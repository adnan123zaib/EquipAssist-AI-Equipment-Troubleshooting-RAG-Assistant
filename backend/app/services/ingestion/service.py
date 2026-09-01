import hashlib
import logging

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.entities import IngestionLog, Manual, ManualStatus
from app.services.ingestion.chunker import chunk_pages
from app.services.ingestion.pdf import extract_pdf
from app.services.retrieval.embeddings import EmbeddingProvider
from app.services.retrieval.vector_store import VectorStore

log = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, s: Settings, store: VectorStore, embedder: EmbeddingProvider):
        self.s = s
        self.store = store
        self.embedder = embedder

    @staticmethod
    def digest(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _stage(self, db: Session, m: Manual, stage: str, status: str, message: str):
        m.status = status
        db.add(
            IngestionLog(
                manual_id=m.id,
                stage=stage,
                status=status,
                message=message,
            )
        )
        db.commit()

    async def process(self, db: Session, m: Manual) -> Manual:
        try:
            self._stage(db, m, "extraction", ManualStatus.extracting.value, "Extracting text by page")
            pages = extract_pdf(m.file_path)
            m.page_count = len(pages)

            self._stage(db, m, "chunking", ManualStatus.chunking.value, "Creating page-preserving semantic chunks")
            chunks = chunk_pages(
                pages,
                m.id,
                m.filename,
                m.equipment_name,
                m.manufacturer,
                m.model_number,
                self.s.chunk_size,
                self.s.chunk_overlap,
                owner_user_id=m.uploaded_by_user_id or "",
            )
            if not chunks:
                raise ValueError("No non-empty text chunks were produced from the manual.")

            self._stage(db, m, "embedding", ManualStatus.embedding.value, "Generating embeddings")
            vectors = await self.embedder.embed([c.original_text for c in chunks])
            if len(vectors) != len(chunks):
                raise RuntimeError("Embedding count does not match chunk count.")

            self.store.delete_manual(m.id)
            self.store.add(
                ids=[c.id for c in chunks],
                documents=[c.original_text for c in chunks],
                embeddings=vectors,
                metadatas=[c.metadata() for c in chunks],
            )

            if self.store.count_manual(m.id) != len(chunks):
                raise RuntimeError("Index validation count mismatch")

            m.chunk_count = len(chunks)
            m.status = ManualStatus.indexed.value
            m.error_message = None
            db.commit()
            db.refresh(m)
            return m
        except Exception as exc:
            log.exception("ingestion_failed", extra={"manual_id": m.id})
            m.status = ManualStatus.failed.value
            m.error_message = str(exc)[:4000]
            db.commit()
            raise
