"""Integration tests for KnowledgeAdapter against a real KnowledgeStore.

These tests require:
1. The knowledge package (dc-power-agent) to be installed.
2. A populated knowledge_store directory at KNOWLEDGE_STORE_PATH.

All tests are skipped automatically when either condition is not met.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

knowledge = pytest.importorskip("knowledge", reason="knowledge package (dc-power-agent) required")

KNOWLEDGE_STORE_PATH = Path(
    os.environ.get(
        "KNOWLEDGE_STORE_PATH",
        "/Users/dkrishna/Documents/Clients/Climate/ARI/AI-Apps/knowledge-layer/knowledge_store",
    )
)

pytestmark = [
    pytest.mark.knowledge,
    pytest.mark.integration,
    pytest.mark.skipif(
        not KNOWLEDGE_STORE_PATH.exists(),
        reason=f"knowledge_store not found at {KNOWLEDGE_STORE_PATH}",
    ),
]

from research_core.adapters.knowledge import KnowledgeAdapter  # noqa: E402
from research_core.protocols.knowledge import (  # noqa: E402
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResult,
)
from tests.conftest import make_research_request  # noqa: E402


def _request(query: str = "SMR deployment", max_results: int = 5) -> KnowledgeRetrievalRequest:
    return KnowledgeRetrievalRequest(
        query=query,
        parent_request=make_research_request(max_knowledge_results=max_results),
    )


@pytest.fixture(scope="module")
def adapter() -> KnowledgeAdapter:
    return KnowledgeAdapter(store_root=KNOWLEDGE_STORE_PATH, load_sources=True)


class TestIntegrationBasicRetrieval:
    def test_retrieve_returns_result_type(self, adapter: KnowledgeAdapter) -> None:
        result = adapter.retrieve(_request())
        assert isinstance(result, KnowledgeRetrievalResult)

    def test_retrieve_returns_evidence_tuple(self, adapter: KnowledgeAdapter) -> None:
        result = adapter.retrieve(_request())
        assert isinstance(result.evidence, tuple)

    def test_retrieve_returns_sources_tuple(self, adapter: KnowledgeAdapter) -> None:
        result = adapter.retrieve(_request())
        assert isinstance(result.sources, tuple)

    def test_evidence_content_non_empty(self, adapter: KnowledgeAdapter) -> None:
        result = adapter.retrieve(_request(query="nuclear reactor"))
        for ev in result.evidence:
            assert ev.content.strip(), f"evidence_id {ev.evidence_id} has empty content"

    def test_evidence_count_respects_max_results(self, adapter: KnowledgeAdapter) -> None:
        result = adapter.retrieve(_request(max_results=3))
        assert len(result.evidence) <= 3

    def test_retrieval_score_normalized(self, adapter: KnowledgeAdapter) -> None:
        result = adapter.retrieve(_request(query="licensing approval"))
        for ev in result.evidence:
            score = ev.provenance.retrieval_score
            if score is not None:
                assert 0.0 <= score <= 1.0, (
                    f"score {score} out of [0,1] for evidence_id {ev.evidence_id}"
                )

    def test_provenance_retrieved_at_timezone_aware(self, adapter: KnowledgeAdapter) -> None:
        result = adapter.retrieve(_request())
        for ev in result.evidence:
            assert ev.provenance.retrieved_at.tzinfo is not None, (
                f"retrieved_at not tz-aware for {ev.evidence_id}"
            )

    def test_sources_deduplicated(self, adapter: KnowledgeAdapter) -> None:
        result = adapter.retrieve(_request(max_results=10))
        source_ids = [s.source_id for s in result.sources]
        assert len(source_ids) == len(set(source_ids)), "sources contain duplicates"

    def test_retriever_cached(self, adapter: KnowledgeAdapter) -> None:
        adapter.retrieve(_request())
        retriever_first = adapter._retriever
        adapter.retrieve(_request())
        assert adapter._retriever is retriever_first

    def test_sources_have_url(self, adapter: KnowledgeAdapter) -> None:
        result = adapter.retrieve(_request(query="SMR cost"))
        for src in result.sources:
            assert src.url, f"source {src.source_id} has no URL"
