from datetime import datetime
from pydantic import BaseModel, Field


class ManualOut(BaseModel):
    id:str; filename:str; equipment_name:str; manufacturer:str; model_number:str; version:str; page_count:int; chunk_count:int; status:str; error_message:str|None; created_at:datetime; updated_at:datetime
    model_config={"from_attributes":True}


class QueryRequest(BaseModel):
    question:str=Field(min_length=3,max_length=2000); manual_ids:list[str]=[]; conversation_id:str|None=None; equipment_model:str|None=None; top_k:int|None=Field(default=None,ge=1,le=20)


class CitationOut(BaseModel):
    manual_id:str; manual_name:str; page_number:int; section_title:str; excerpt:str; chunk_id:str; retrieval_score:float; reranker_score:float=0


class ConfidenceOut(BaseModel):
    score:int; level:str; explanation:str; components:dict[str,float]


class QueryResponse(BaseModel):
    answer:str; troubleshooting_steps:list[str]; safety_warnings:list[str]; citations:list[CitationOut]; confidence:ConfidenceOut; retrieval_attempts:int; response_time_ms:int; conversation_id:str

