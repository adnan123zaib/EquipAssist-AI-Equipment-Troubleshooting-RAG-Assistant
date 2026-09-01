import re
import uuid
from dataclasses import asdict, dataclass

from app.services.ingestion.pdf import PageText


NUMBERED_HEADING = re.compile(r"^\d+(?:\.\d+)*\.?\s+.+$")
ERROR_HEADING = re.compile(r"^(?:E\d{2,4}|F\d{2,4}|AL-\d{2,4}|0x[0-9A-F]+)\s*:\s*.+$", re.I)


@dataclass
class Chunk:
    id: str
    manual_id: str
    manual_filename: str
    equipment_name: str
    manufacturer: str
    model: str
    owner_user_id: str
    page_number: int
    section_title: str
    chunk_number: int
    original_text: str
    source_identifier: str

    def metadata(self):
        data = asdict(self)
        data.pop("original_text")
        return data


def clean_text(text: str) -> str:
    text = text.replace("\u00ad", "").replace("\x00", "")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def is_heading(line: str) -> bool:
    candidate = line.strip().rstrip(":")
    if re.fullmatch(r"page\s+\d+", candidate, re.I):
        return False
    if not candidate or len(candidate) > 90 or len(candidate.split()) > 12:
        return False
    if candidate.endswith((".", "?", "!")):
        return False
    if NUMBERED_HEADING.match(candidate) or ERROR_HEADING.match(line.strip()):
        return True
    words = re.findall(r"[A-Za-z][A-Za-z0-9/-]*", candidate)
    if not words:
        return False
    # Short title-like lines are headings; ordinary sentence fragments are not.
    title_like = all(word[0].isupper() for word in words)
    return title_like and len(words) <= 8


def _split_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    current_title = "General"
    current_lines: list[str] = []

    for line in text.splitlines():
        if is_heading(line):
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = line.strip().rstrip(":")
            current_lines = [line.strip()]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, current_lines))

    return [(title, "\n".join(lines).strip()) for title, lines in sections if "\n".join(lines).strip()]


def chunk_pages(
    pages: list[PageText],
    manual_id: str,
    filename: str,
    equipment_name: str = "",
    manufacturer: str = "",
    model: str = "",
    chunk_size: int = 1000,
    overlap: int = 150,
    owner_user_id: str = "",
) -> list[Chunk]:
    if overlap >= chunk_size:
        raise ValueError("chunk overlap must be smaller than chunk size")

    chunks: list[Chunk] = []
    number = 0

    for page in pages:
        text = clean_text(page.text)
        for section, section_text in _split_sections(text):
            start = 0
            while start < len(section_text):
                end = min(start + chunk_size, len(section_text))
                piece = section_text[start:end]

                if end < len(section_text):
                    boundary = max(piece.rfind("\n"), piece.rfind(". "))
                    if boundary > chunk_size // 2:
                        end = start + boundary + 1
                        piece = section_text[start:end]

                piece = piece.strip()
                if piece:
                    number += 1
                    source_identifier = f"{manual_id}:p{page.page_number}:c{number}"
                    chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, source_identifier))
                    chunks.append(
                        Chunk(
                            chunk_id,
                            manual_id,
                            filename,
                            equipment_name,
                            manufacturer,
                            model,
                            owner_user_id,
                            page.page_number,
                            section,
                            number,
                            piece,
                            source_identifier,
                        )
                    )

                if end >= len(section_text):
                    break
                start = max(start + 1, end - overlap)

    return chunks
