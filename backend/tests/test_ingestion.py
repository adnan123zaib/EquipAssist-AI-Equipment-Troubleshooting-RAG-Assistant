import hashlib
import fitz
from app.services.ingestion.pdf import extract_pdf,PageText
from app.services.ingestion.chunker import chunk_pages

def test_pdf_text_extraction(sample_pdf):
    pages = extract_pdf(str(sample_pdf))

    assert len(pages) >= 1
    assert any("E05" in page.text for page in pages)
    assert all(page.page_number > 0 for page in pages)
    
def test_chunking_preserves_metadata():
    chunks=chunk_pages([PageText(7,"E05: Motor Overtemperature\nStop the motor. Apply lockout/tagout before inspection. "*20)],"m1","manual.pdf","Pump","Northstar","PX-200",300,50)
    assert len(chunks)>1; assert all(c.page_number==7 and c.manual_id=="m1" and c.model=="PX-200" for c in chunks); assert all(c.source_identifier for c in chunks)
    assert len({c.id for c in chunks}) == len(chunks)

def test_invalid_pdf_upload(client):
    r=client.post('/api/v1/manuals/upload',files={'files':('bad.pdf',b'not pdf','application/pdf')}); assert r.status_code==415

def test_duplicate_detection(client,sample_pdf):
    data=sample_pdf.read_bytes(); payload={'files':('PX-200.pdf',data,'application/pdf')}; meta={'equipment_name':'PX-200','model_number':'PX-200'}
    first=client.post('/api/v1/manuals/upload',files=payload,data=meta); assert first.status_code in (201,409)
    second=client.post('/api/v1/manuals/upload',files=payload,data=meta); assert second.status_code==409



def test_chunk_sections_track_document_headings(sample_pdf):
    pages = extract_pdf(str(sample_pdf))
    chunks = chunk_pages(pages, "m1", "PX-200_manual.pdf", "PX-200", "Northstar", "PX-200", 500, 80, "user-1")
    assert any(c.section_title == "E05: Motor Overtemperature" for c in chunks)
    assert any(c.section_title == "E12: Low Hydraulic Pressure" for c in chunks)
    assert any("Emergency Shutdown Procedure" in c.section_title for c in chunks)
    assert all(c.owner_user_id == "user-1" for c in chunks)
