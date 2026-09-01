from app.services.retrieval.hybrid import RetrievedChunk

def calculate_confidence(chunks:list[RetrievedChunk],citation_coverage:float,evidence_agreement:float,identifier_specific:bool,model_missing:bool=False,conflict:bool=False,indirect:bool=False)->dict:
    retrieval=sum(x.retrieval_score for x in chunks[:3])/min(3,len(chunks)) if chunks else 0
    rerank=sum(x.reranker_score for x in chunks[:3])/min(3,len(chunks)) if chunks else 0
    exact=1.0 if any(x.exact_match for x in chunks) else 0.0
    raw=100*(.30*retrieval+.25*rerank+.20*citation_coverage+.15*evidence_agreement+.10*exact)
    penalties=[]
    if len(chunks)==1: raw-=15; penalties.append("only one useful chunk")
    if model_missing: raw-=20; penalties.append("equipment model missing")
    if conflict: raw-=25; penalties.append("sources conflict")
    if indirect: raw=min(raw,55); penalties.append("evidence is indirect")
    if identifier_specific and not exact: raw=min(raw,40); penalties.append("no exact identifier match")
    score=max(0,min(100,round(raw))); level="high" if score>=85 else "medium" if score>=65 else "low"
    explanation=("Exact identifier match and consistent cited evidence." if exact and len(chunks)>1 else "Score is based on retrieved evidence and citation coverage.")
    if penalties: explanation+=" Penalties: "+", ".join(penalties)+"."
    return {"score":score,"level":level,"explanation":explanation,"components":{"retrieval_similarity":round(retrieval,3),"reranker_relevance":round(rerank,3),"citation_coverage":citation_coverage,"evidence_agreement":evidence_agreement,"exact_identifier_match":exact}}

