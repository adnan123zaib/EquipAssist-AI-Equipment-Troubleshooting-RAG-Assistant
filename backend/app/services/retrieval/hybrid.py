import re
from dataclasses import dataclass
from rank_bm25 import BM25Okapi
from app.services.retrieval.embeddings import EmbeddingProvider
from app.services.retrieval.vector_store import VectorStore

ERROR_CODE=re.compile(r"(?<![A-Z0-9])(?:E\d{2,4}|F\d{2,4}|AL-\d{2,4}|0x[0-9A-F]+)(?![A-Z0-9])",re.I)


def detect_error_codes(text:str)->list[str]: return [x.upper() for x in ERROR_CODE.findall(text)]


@dataclass
class RetrievedChunk:
    chunk_id:str; text:str; metadata:dict; retrieval_score:float; reranker_score:float; exact_match:bool


class HybridRetriever:
    def __init__(self,store:VectorStore,embedder:EmbeddingProvider,threshold:float=.35): self.store=store; self.embedder=embedder; self.threshold=threshold
    async def search(self,query:str,top_k:int=6,manual_ids:list[str]|None=None,owner_user_id:str|None=None)->list[RetrievedChunk]:
        vector=(await self.embedder.embed([query]))[0]
        dense=self.store.query(vector,max(top_k*3,10),manual_ids,owner_user_id)
        corpus=self.store.all(manual_ids,owner_user_id)
        docs=corpus.get("documents",[]); ids=corpus.get("ids",[]); metas=corpus.get("metadatas",[])
        stopwords={"the","a","an","and","or","to","of","in","on","for","with","what","how","does","do","is","are","it","my","please","manual","troubleshooting","causes","verification"}
        def tokens(s):
            return [token for token in re.findall(r"[a-z0-9-]+",s.lower()) if token not in stopwords and len(token)>1]
        query_tokens=tokens(query)
        # BM25 is used only as a lexical signal. Normalize against the maximum
        # positive score so one document cannot manufacture a score of 1 from
        # a zero/negative BM25 baseline.
        bm=BM25Okapi([tokens(x) for x in docs]) if docs and query_tokens else None
        keyword=bm.get_scores(query_tokens) if bm else []
        positive=[float(x) for x in keyword if float(x)>0]
        max_bm=max(positive) if positive else 1.0
        exact=set(detect_error_codes(query)); merged={}
        for cid,doc,meta,dist in zip(dense["ids"][0],dense["documents"][0],dense["metadatas"][0],dense["distances"][0]):
            sim=max(0.0,1.0-float(dist)); is_exact=bool(exact & set(detect_error_codes(doc)))
            merged[cid]=[doc,meta,sim,0.0,is_exact]
        for i,(cid,doc,meta) in enumerate(zip(ids,docs,metas)):
            kw=max(0.0,float(keyword[i])/max_bm) if len(keyword) else 0.0
            is_exact=bool(exact & set(detect_error_codes(doc)))
            if kw>0 or is_exact:
                row=merged.setdefault(cid,[doc,meta,0.0,0.0,is_exact]); row[3]=kw; row[4]=row[4] or is_exact
        results=[]
        for cid,(doc,meta,sim,kw,is_exact) in merged.items():
            # Exact fault identifiers are a deterministic lexical anchor. For
            # all other queries require both semantic/lexical evidence instead
            # of allowing a single noisy signal to pass the threshold.
            score=min(1.0,.55*sim+.35*kw+.25*(1.0 if is_exact else 0.0))
            rerank=min(1.0,.65*score+.35*kw)
            if score>=self.threshold or is_exact:
                results.append(RetrievedChunk(cid,doc,meta,score,rerank,is_exact))
        return sorted(results,key=lambda x:(x.exact_match,x.reranker_score),reverse=True)[:top_k]
