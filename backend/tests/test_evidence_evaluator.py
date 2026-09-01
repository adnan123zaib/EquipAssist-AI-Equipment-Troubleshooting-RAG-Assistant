import pytest

from app.agents.workflow import TroubleshootingGraph
from app.services.retrieval.hybrid import RetrievedChunk


class _UnusedService:
    """Minimal collaborator used because evaluator tests do not call providers."""


def _chunk(*, retrieval: float, reranker: float, exact: bool) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="chunk-1",
        text="E05 indicates motor overtemperature.",
        metadata={
            "manual_id": "manual-1",
            "manual_filename": "PX-200_manual.pdf",
            "page_number": 7,
            "section_title": "Error Codes",
        },
        retrieval_score=retrieval,
        reranker_score=reranker,
        exact_match=exact,
    )


@pytest.mark.asyncio
async def test_one_strong_exact_identifier_chunk_is_sufficient():
    workflow = TroubleshootingGraph(_UnusedService(), _UnusedService())
    result = await workflow.evaluate(
        {"error_codes": ["E05"], "chunks": [_chunk(retrieval=.72, reranker=.68, exact=True)]}
    )
    assert result["sufficient"] is True


@pytest.mark.asyncio
async def test_unknown_identifier_is_rejected_even_with_unrelated_chunks():
    workflow = TroubleshootingGraph(_UnusedService(), _UnusedService())
    result = await workflow.evaluate(
        {"error_codes": ["AL-9999"], "chunks": [_chunk(retrieval=.85, reranker=.82, exact=False)]}
    )
    assert result["sufficient"] is False
    assert "AL-9999" in result["evidence_reason"]


@pytest.mark.asyncio
async def test_two_moderate_symptom_passages_are_sufficient():
    workflow = TroubleshootingGraph(_UnusedService(), _UnusedService())
    chunks = [
        _chunk(retrieval=.40, reranker=.42, exact=False),
        _chunk(retrieval=.36, reranker=.38, exact=False),
    ]
    result = await workflow.evaluate({"error_codes": [], "chunks": chunks})
    assert result["sufficient"] is True
