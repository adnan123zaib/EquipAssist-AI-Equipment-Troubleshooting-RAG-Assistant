import pytest
from app.services.retrieval.hybrid import detect_error_codes,RetrievedChunk
from app.services.confidence.calculator import calculate_confidence

def test_error_code_detection(): assert detect_error_codes('E05 F12 AL-102 and 0x31')==['E05','F12','AL-102','0X31']

def chunk(exact=True,score=.9): return RetrievedChunk('c','E05 motor temperature',{'manual_id':'m','manual_filename':'x.pdf','page_number':2,'section_title':'E05'},score,.88,exact)

def test_confidence_formula_and_penalty():
    high=calculate_confidence([chunk(),chunk()],1,.9,True); low=calculate_confidence([chunk(False,.4)],.3,.5,True,indirect=True)
    assert high['score']>=80; assert low['score']<=40; assert high['components']['exact_identifier_match']==1

def test_weak_evidence_rejection_cap(): assert calculate_confidence([],0,0,True)['score']==0

