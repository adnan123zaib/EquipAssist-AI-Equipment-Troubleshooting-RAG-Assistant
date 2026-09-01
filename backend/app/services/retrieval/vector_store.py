from typing import Any

import chromadb

from app.core.config import Settings


class VectorStore:
    """ChromaDB vector storage for indexed manual chunks."""

    def __init__(self, settings: Settings):
        self.client = chromadb.PersistentClient(path=settings.chroma_persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="equipment_manuals",
            metadata={"hnsw:space": "cosine"},
        )

    @staticmethod
    def _where(
        manual_ids: list[str] | None = None,
        owner_user_id: str | None = None,
    ):
        conditions = []
        if owner_user_id:
            conditions.append({"owner_user_id": owner_user_id})
        if manual_ids:
            conditions.append(
                {"manual_id": manual_ids[0]}
                if len(manual_ids) == 1
                else {"manual_id": {"$in": manual_ids}}
            )
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def query(
        self,
        embedding: list[float],
        top_k: int,
        manual_ids: list[str] | None = None,
        owner_user_id: str | None = None,
    ) -> dict[str, Any]:
        collection_count = self.collection.count()
        if collection_count == 0:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        where = self._where(manual_ids, owner_user_id)
        try:
            return self.collection.query(
                query_embeddings=[embedding],
                n_results=min(top_k, collection_count),
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            if "dimension" in str(exc).lower():
                raise RuntimeError(
                    "The ChromaDB index uses an incompatible embedding dimension. "
                    "Delete storage/chroma, restart the backend, and reprocess the uploaded manuals."
                ) from exc
            raise

    def add(self, ids, documents, embeddings, metadatas) -> None:
        if not ids:
            return
        if not (len(ids) == len(documents) == len(embeddings) == len(metadatas)):
            raise ValueError("Vector-store inputs must have equal lengths")
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def all(
        self,
        manual_ids: list[str] | None = None,
        owner_user_id: str | None = None,
    ) -> dict[str, Any]:
        return self.collection.get(
            where=self._where(manual_ids, owner_user_id),
            include=["documents", "metadatas"],
        )

    def delete_manual(self, manual_id: str) -> None:
        self.collection.delete(where={"manual_id": manual_id})

    def count_manual(self, manual_id: str) -> int:
        result = self.collection.get(where={"manual_id": manual_id}, include=[])
        return len(result.get("ids", []))
