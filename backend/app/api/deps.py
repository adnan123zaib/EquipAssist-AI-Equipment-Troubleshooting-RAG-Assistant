from functools import lru_cache

from sqlalchemy.orm import Session

from app.agents.workflow import TroubleshootingGraph
from app.core.config import get_settings
from app.models import User
from app.services.generation.providers import (
    generation_provider,
)
from app.services.retrieval.embeddings import embedding_provider
from app.services.retrieval.hybrid import HybridRetriever
from app.services.retrieval.vector_store import VectorStore


@lru_cache
def services():
    settings = get_settings()
    embedder = embedding_provider(settings)
    store = VectorStore(settings)
    retriever = HybridRetriever(
        store,
        embedder,
        settings.similarity_threshold,
    )
    graph = TroubleshootingGraph(
        retriever,
        generation_provider(settings),
        settings.max_retrieval_attempts,
    )
    return settings, embedder, store, graph


def graph_for_user(user: User, db: Session) -> TroubleshootingGraph:
    settings, embedder, store, _ = services()
    retriever = HybridRetriever(store, embedder, settings.similarity_threshold)
    return TroubleshootingGraph(
        retriever,
        generation_provider(settings),
        settings.max_retrieval_attempts,
    )
