import re
from dataclasses import dataclass
import fitz


@dataclass
class PageText:
    page_number:int; text:str


class OCRService:
    """Extension point for scanned-document OCR."""
    def extract(self, pdf_path:str)->list[PageText]:
        raise RuntimeError("OCR is not configured. Upload a text-based PDF or configure an OCRService implementation.")


def extract_pdf(path:str, ocr:OCRService|None=None)->list[PageText]:
    pages=[]
    with fitz.open(path) as doc:
        for number,page in enumerate(doc,1):
            text=re.sub(r"[ \t]+"," ",page.get_text("text")).strip()
            pages.append(PageText(number,text))
    if sum(len(p.text) for p in pages)<100:
        if ocr: return ocr.extract(path)
        raise ValueError("PDF contains insufficient extractable text; OCR is not configured.")
    return pages

