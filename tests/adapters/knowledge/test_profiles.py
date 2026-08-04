"""Tests for multi-profile retrieval merging and deduplication."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

knowledge = pytest.importorskip("knowledge", reason="knowledge package (dc-power-agent) required")

from research_core.adapters.knowledge.adapter import KnowledgeAdapter  # noqa: E402
from research_core.protocols.knowledge import KnowledgeRetrievalRequest  # noqa: E402
from tests.conftest import make_research_request  # noqa: E402

from .conftest import make_kl_evidence, make_retrieved_evidence  # noqa: E402


def _make_request(
    profiles: tuple[str, ...] = (), max_results: int = 20
) -> KnowledgeRetrievalRequest:
    parent = make_research_request(max_knowledge_results=max_results)
    return KnowledgeRetrievalRequest(
        query="SMR deployment",
        parent_request=parent,
        profiles=profiles,
    )


def _mock_result(items: list) -> MagicMock:
    r = MagicMock()
    r.items = items
    return r


class TestMultiProfileRetrieval:
    def _adapter_with_retriever(self, tmp_path: Path) -> tuple[KnowledgeAdapter, MagicMock]:
        adapter = KnowledgeAdapter(store_root=tmp_path, load_sources=False)
        mock_retriever = MagicMock()
        adapter._retriever = mock_retriever
        return adapter, mock_retriever

    def test_no_profiles_calls_retriever_once(self, tmp_path: Path) -> None:
        adapter, mock_retriever = self._adapter_with_retriever(tmp_path)
        mock_retriever.retrieve.return_value = _mock_result([])

        adapter.retrieve(_make_request(profiles=()))
        assert mock_retriever.retrieve.call_count == 1

    def test_single_profile_calls_retriever_once(self, tmp_path: Path) -> None:
        adapter, mock_retriever = self._adapter_with_retriever(tmp_path)
        mock_retriever.retrieve.return_value = _mock_result([])

        adapter.retrieve(_make_request(profiles=("smr-general",)))
        assert mock_retriever.retrieve.call_count == 1

    def test_two_profiles_calls_retriever_twice(self, tmp_path: Path) -> None:
        adapter, mock_retriever = self._adapter_with_retriever(tmp_path)
        mock_retriever.retrieve.return_value = _mock_result([])

        adapter.retrieve(_make_request(profiles=("smr-general", "smr-advanced")))
        assert mock_retriever.retrieve.call_count == 2

    def test_each_profile_used_in_retrieve_call(self, tmp_path: Path) -> None:
        adapter, mock_retriever = self._adapter_with_retriever(tmp_path)
        mock_retriever.retrieve.return_value = _mock_result([])

        adapter.retrieve(_make_request(profiles=("profile-a", "profile-b", "profile-c")))

        call_profiles = [
            call.kwargs.get("profile")
            for call in mock_retriever.retrieve.call_args_list
        ]
        assert sorted(call_profiles) == ["profile-a", "profile-b", "profile-c"]

    def test_dedup_by_evidence_id(self, tmp_path: Path) -> None:
        ev = make_kl_evidence(evidence_id="ev-shared")
        item_a = make_retrieved_evidence(evidence=ev, score=1.0, rank=1)
        item_b = make_retrieved_evidence(evidence=ev, score=0.8, rank=1)

        adapter, mock_retriever = self._adapter_with_retriever(tmp_path)
        mock_retriever.retrieve.side_effect = [_mock_result([item_a]), _mock_result([item_b])]

        result = adapter.retrieve(_make_request(profiles=("prof-a", "prof-b")))
        assert len(result.evidence) == 1

    def test_highest_score_wins_on_dedup(self, tmp_path: Path) -> None:
        ev = make_kl_evidence(
            evidence_id="ev-shared",
            statement="High score version of this statement.",
        )
        item_low = make_retrieved_evidence(evidence=ev, score=0.5, rank=2)
        ev_high = make_kl_evidence(
            evidence_id="ev-shared",
            statement="High score version of this statement.",
        )
        item_high = make_retrieved_evidence(evidence=ev_high, score=1.5, rank=1)

        adapter, mock_retriever = self._adapter_with_retriever(tmp_path)
        mock_retriever.retrieve.side_effect = [
            _mock_result([item_low]),
            _mock_result([item_high]),
        ]

        result = adapter.retrieve(_make_request(profiles=("a", "b")))
        assert len(result.evidence) == 1
        assert result.evidence[0].provenance.retrieval_score is not None
        assert result.evidence[0].provenance.retrieval_score > normalize_score(0.5)

    def test_unique_evidence_from_different_profiles_merged(self, tmp_path: Path) -> None:
        ev1 = make_kl_evidence(evidence_id="ev-001", statement="Statement from profile A.")
        ev2 = make_kl_evidence(evidence_id="ev-002", statement="Statement from profile B.")
        item1 = make_retrieved_evidence(evidence=ev1, score=1.2, rank=1)
        item2 = make_retrieved_evidence(evidence=ev2, score=1.0, rank=1)

        adapter, mock_retriever = self._adapter_with_retriever(tmp_path)
        mock_retriever.retrieve.side_effect = [_mock_result([item1]), _mock_result([item2])]

        result = adapter.retrieve(_make_request(profiles=("a", "b")))
        assert len(result.evidence) == 2

    def test_top_k_respected_after_merge(self, tmp_path: Path) -> None:
        items_a = [
            make_retrieved_evidence(
                evidence=make_kl_evidence(evidence_id=f"ev-a-{i}", statement=f"Statement A{i}."),
                score=float(10 - i),
                rank=i + 1,
            )
            for i in range(5)
        ]
        items_b = [
            make_retrieved_evidence(
                evidence=make_kl_evidence(evidence_id=f"ev-b-{i}", statement=f"Statement B{i}."),
                score=float(5 - i),
                rank=i + 1,
            )
            for i in range(5)
        ]

        adapter, mock_retriever = self._adapter_with_retriever(tmp_path)
        mock_retriever.retrieve.side_effect = [_mock_result(items_a), _mock_result(items_b)]

        result = adapter.retrieve(_make_request(profiles=("a", "b"), max_results=3))
        assert len(result.evidence) <= 3

    def test_merged_evidence_ordered_by_score_descending(self, tmp_path: Path) -> None:
        ev1 = make_kl_evidence(evidence_id="ev-low", statement="Low score item.")
        ev2 = make_kl_evidence(evidence_id="ev-high", statement="High score item.")
        item_low = make_retrieved_evidence(evidence=ev1, score=0.5, rank=2)
        item_high = make_retrieved_evidence(evidence=ev2, score=1.8, rank=1)

        adapter, mock_retriever = self._adapter_with_retriever(tmp_path)
        mock_retriever.retrieve.side_effect = [_mock_result([item_low]), _mock_result([item_high])]

        result = adapter.retrieve(_make_request(profiles=("a", "b")))
        assert len(result.evidence) == 2
        score_0 = result.evidence[0].provenance.retrieval_score or 0
        score_1 = result.evidence[1].provenance.retrieval_score or 0
        assert score_0 >= score_1


def normalize_score(score: float) -> float:
    from research_core.adapters.knowledge.mapping import normalize_score as _ns

    return _ns(score)
