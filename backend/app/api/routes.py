import asyncio
import hashlib
import json
import re
import time
from pathlib import Path
from fastapi import APIRouter,BackgroundTasks,Depends,File,Form,HTTPException,UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.api.deps import graph_for_user, services
from app.api.auth_deps import get_current_user
from app.db.session import get_db
from app.models import Citation,Conversation,IngestionLog,Manual,Message,Query,User
from app.schemas.api import ManualOut,QueryRequest,QueryResponse
from app.services.ingestion.service import IngestionService

router=APIRouter()

@router.get("/health")
async def health(): return {"status":"ok","service":"EquipAssist AI"}

async def _process(manual_id:str):
    from app.db.session import SessionLocal
    db=SessionLocal(); s,embed,store,_=services()
    try:
        m=db.get(Manual,manual_id)
        if m: await IngestionService(s,store,embed).process(db,m)
    finally: db.close()

@router.post("/manuals/upload",response_model=list[ManualOut],status_code=201)
async def upload_manuals(background:BackgroundTasks,files:list[UploadFile]=File(...),equipment_name:str=Form(""),manufacturer:str=Form(""),model_number:str=Form(""),version:str=Form(""),db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    s,_,_,_=services(); results=[]
    for file in files:
        data=await file.read()
        if file.content_type!="application/pdf" or not data.startswith(b"%PDF"): raise HTTPException(415,"Only valid PDF files are accepted")
        if len(data)>s.max_upload_size_mb*1024*1024: raise HTTPException(413,"PDF exceeds configured size limit")
        digest=hashlib.sha256(data).hexdigest()
        if db.scalar(select(Manual).where(Manual.file_hash==digest,Manual.uploaded_by_user_id==user.id)): raise HTTPException(409,"This PDF has already been uploaded")
        safe=re.sub(r"[^A-Za-z0-9._-]","_",Path(file.filename or "manual.pdf").name); path=Path(s.manual_storage_directory)/f"{user.id[:8]}_{digest[:12]}_{safe}"; path.write_bytes(data)
        m=Manual(filename=safe,uploaded_by_user_id=user.id,equipment_name=equipment_name,manufacturer=manufacturer,model_number=model_number,version=version,file_path=str(path),file_hash=digest); db.add(m); db.commit(); db.refresh(m); results.append(m); background.add_task(_process,m.id)
    return results

@router.get("/manuals",response_model=list[ManualOut])
async def manuals(db:Session=Depends(get_db),user:User=Depends(get_current_user)): return list(db.scalars(select(Manual).where(Manual.uploaded_by_user_id==user.id).order_by(Manual.created_at.desc())))

@router.get("/manuals/{manual_id}",response_model=ManualOut)
async def manual(manual_id:str,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    if not (m:=db.scalar(select(Manual).where(Manual.id==manual_id,Manual.uploaded_by_user_id==user.id))): raise HTTPException(404,"Manual not found")
    return m

@router.post("/manuals/{manual_id}/reprocess",response_model=ManualOut)
async def reprocess(manual_id:str,background:BackgroundTasks,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    if not (m:=db.scalar(select(Manual).where(Manual.id==manual_id,Manual.uploaded_by_user_id==user.id))): raise HTTPException(404,"Manual not found")
    m.status="uploaded"; db.commit(); background.add_task(_process,m.id); return m

@router.delete("/manuals/{manual_id}",status_code=204)
async def delete_manual(manual_id:str,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    if not (m:=db.scalar(select(Manual).where(Manual.id==manual_id,Manual.uploaded_by_user_id==user.id))): raise HTTPException(404,"Manual not found")
    _,_,store,_=services(); store.delete_manual(m.id); path=Path(m.file_path); db.delete(m); db.commit(); path.unlink(missing_ok=True)

async def _query(req:QueryRequest,db:Session,user:User):
    started=time.perf_counter(); graph=graph_for_user(user,db)
    selected_manuals = []
    if req.manual_ids:
        selected_manuals = list(
            db.scalars(
                select(Manual).where(
                    Manual.id.in_(req.manual_ids),
                    Manual.uploaded_by_user_id == user.id,
                )
            )
        )
        owned = {m.id for m in selected_manuals}
        if owned != set(req.manual_ids):
            raise HTTPException(404, "One or more manuals are unavailable")
    equipment_model = req.equipment_model
    if not equipment_model and len(selected_manuals) == 1:
        equipment_model = selected_manuals[0].model_number or None

    conversation=db.scalar(select(Conversation).where(Conversation.id==req.conversation_id,Conversation.user_id==user.id)) if req.conversation_id else None
    if not conversation: conversation=Conversation(user_id=user.id,title=req.question[:80],selected_manual_id=req.manual_ids[0] if len(req.manual_ids)==1 else None); db.add(conversation); db.commit(); db.refresh(conversation)
    db.add(Message(conversation_id=conversation.id,role="user",content=req.question)); conversation.updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc); db.commit()
    final=await graph.run(question=req.question,manual_ids=req.manual_ids,equipment_model=equipment_model,owner_user_id=user.id,top_k=req.top_k or services()[0].retrieval_top_k)
    elapsed=round((time.perf_counter()-started)*1000); assistant=Message(conversation_id=conversation.id,role="assistant",content=final["answer"],confidence_score=final["confidence"]["score"]); db.add(assistant); db.commit(); db.refresh(assistant)
    for c in final["citations"]: db.add(Citation(message_id=assistant.id,manual_id=c["manual_id"],chunk_id=c["chunk_id"],page_number=c["page_number"],section_title=c["section_title"],excerpt=c["excerpt"],retrieval_score=c["retrieval_score"],reranker_score=c["reranker_score"]))
    codes=re.findall(r"\b(?:E\d+|F\d+|AL-\d+|0x[0-9A-F]+)\b",req.question,re.I)
    db.add(Query(conversation_id=conversation.id,original_query=req.question,rewritten_query=req.question,detected_error_code=codes[0].upper() if codes else None,detected_equipment=equipment_model,retrieval_attempts=final["retrieval_attempts"],response_time_ms=elapsed)); db.commit()
    final.update({"response_time_ms":elapsed,"conversation_id":conversation.id}); return final

@router.post("/chat/query", response_model=QueryResponse)
async def chat_query(req: QueryRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return await _query(req, db, user)


@router.post("/chat/stream")
async def chat_stream(req:QueryRequest,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    result=await _query(req,db,user)
    async def events():
        yield "event: status\ndata: {\"stage\":\"retrieval_complete\"}\n\n"
        for key in ("answer","troubleshooting_steps","safety_warnings","citations","confidence","retrieval_attempts","response_time_ms","conversation_id"):
            yield f"event: {key}\ndata: {json.dumps(result[key])}\n\n"; await asyncio.sleep(.01)
        yield "event: done\ndata: {}\n\n"
    return StreamingResponse(events(),media_type="text/event-stream")

@router.get("/conversations")
async def conversations(db:Session=Depends(get_db),user:User=Depends(get_current_user)): return [{"id":x.id,"title":x.title,"created_at":x.created_at} for x in db.scalars(select(Conversation).where(Conversation.user_id==user.id).order_by(Conversation.updated_at.desc()))]

@router.get("/conversations/{conversation_id}")
async def conversation(conversation_id:str,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    if not (c:=db.scalar(select(Conversation).where(Conversation.id==conversation_id,Conversation.user_id==user.id))): raise HTTPException(404,"Conversation not found")
    return {"id":c.id,"title":c.title,"messages":[{"id":m.id,"role":m.role,"content":m.content,"confidence_score":m.confidence_score,"created_at":m.created_at} for m in c.messages]}

@router.delete("/conversations/{conversation_id}",status_code=204)
async def delete_conversation(conversation_id:str,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    if not (c:=db.scalar(select(Conversation).where(Conversation.id==conversation_id,Conversation.user_id==user.id))): raise HTTPException(404,"Conversation not found")
    db.delete(c); db.commit()

@router.get("/providers")
async def providers(user:User=Depends(get_current_user)):
    s,_,_,_=services(); return {"llm":{"selected":s.llm_provider,"available":["local","groq","openai","anthropic"]},"embeddings":{"selected":s.embedding_provider,"available":["local"]},"vector_database":"chromadb"}

@router.get("/settings")
async def settings_endpoint(user:User=Depends(get_current_user)):
    s,_,_,_=services(); return {"top_k":s.retrieval_top_k,"similarity_threshold":s.similarity_threshold,"chunk_size":s.chunk_size,"chunk_overlap":s.chunk_overlap,"reranking":s.enable_reranking,"max_retrieval_attempts":s.max_retrieval_attempts}

@router.get("/metrics")
async def metrics(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    total=db.scalar(select(func.count()).select_from(Manual).where(Manual.uploaded_by_user_id==user.id)) or 0; indexed=db.scalar(select(func.count()).select_from(Manual).where(Manual.status=="indexed",Manual.uploaded_by_user_id==user.id)) or 0; failed=db.scalar(select(func.count()).select_from(Manual).where(Manual.status=="failed",Manual.uploaded_by_user_id==user.id)) or 0; conv=db.scalar(select(func.count()).select_from(Conversation).where(Conversation.user_id==user.id)) or 0; questions=db.scalar(select(func.count()).select_from(Query).join(Conversation).where(Conversation.user_id==user.id)) or 0
    return {"total_manuals":total,"indexed_manuals":indexed,"failed_ingestions":failed,"active_conversations":conv,"questions_answered":questions}
