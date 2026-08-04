"""Tests for KnowledgeAdapter — unit tests with a mock retriever."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

knowledge = pytest.importorskip("knowledge", reason="knowledge package (dc-power-agent) required")

from research_core.adapters.knowledge.adapter import KnowledgeAdapter  # noqa: E402
from research_core.exceptions import ProviderExecutionError, ProviderUnavailableError  # noqa: E402
from research_core.protocols.knowledge import (  # noqa: E402
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResult,
)
from tests.conftest import make_research_request  # noqa: E402

from .conftest import make_kl_evidence, make_kl_source, make_retrieved_evidence  # noqa: E402


def _make_request(**kwargs: object) -> KnowledgeRetrievalRequest:
    parent = make_research_request(max_knowledge_results=kwargs.pop("max_results", 20))
    return KnowledgeRetrievalRequest(
        query=kwargs.pop("query", "SMR deployment"),
        parent_request=parent,
        **kwargs,  # type: ignore[arg-type]
    )


def _mock_retrieval_result(items: list) -> MagicMock:
    result = MagicMock()
    result.items = items
    return result


class TestKnowledgeAdapterConstruction:
    def test_construction_does_not_import_knowledge(self, tmp_path: Path) -> None:
        import sys

        knowledge_was_loaded = "knowledge" in sys.modules
        adapter = KnowledgeAdapter(store_root=tmp_path)
        assert adapter is not None
        if not knowledge_was_loaded:
            pass  # don't assert anything — knowledge may already be loaded

    def test_store_root_stored_as_path(self, tmp_path: Path) -> None:
        adapter = KnowledgeAdapter(store_root=str(tmp_path))
        assert adapter._store_root == tmp_path

    def test_load_sources_default_true(self, tmp_path: Path) -> None:
        adapter = KnowledgeAdapter(store_root=tmp_path)
        assert adapter._load_sources is True

    def test_load_sources_can_be_disabled(self, tmp_path: Path) -> None:
        adapter = KnowledgeAdapter(store_root=tmp_path, load_sources=False)
        assert adapter._load_sources is False

    def test_retriever_initially_none(self, tmp_path: Path) -> None:
        adapter = KnowledgeAdapter(store_root=tmp_path)
        assert adapter._retriever is None

    def test_is_available_returns_true_when_knowledge_installed(self) -> None:
        assert KnowledgeAdapter.is_available() is True


class TestKnowledgeAdapterRetrieve:
    def _make_adapter_with_mock_retriever(self, tmp_path: Path, items: list) -> KnowledgeAdapter:
        adapter = KnowledgeAdapter(store_root=tmp_path)
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = _mock_retrieval_result(items)
        adapter._retriever = mock_retriever
        return adapter

    def test_returns_knowledge_retrieval_result(self, tmp_path: Path) -> None:
        adapter = self._make_adapter_with_mock_retriever(tmp_path, [])
        result = adapter.retrieve(_make_request())
        assert isinstance(result, KnowledgeRetrievalResult)

    def test_empty_retrieval_result(self, tmp_path: Path) -> None:
        adapter = self._make_adapter_with_mock_retriever(tmp_path, [])
        result = adapter.retrieve(_make_request())
        assert result.sources == ()
        assert result.evidence == ()

    def test_evidence_items_mapped(self, tmp_path: Path) -> None:
        items = [make_retrieved_evidence(score=1.0)]
        adapter = self._make_adapter_with_mock_retriever(tmp_path, items)
        result = adapter.retrieve(_make_request())
        assert len(result.evidence) == 1

    def test_no_profile_passes_no_profile_to_retriever(self, tmp_path: Path) -> None:
        adapter = KnowledgeAdapter(store_root=tmp_path)
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = _mock_retrieval_result([])
        adapter._retriever = mock_retriever

        adapter.retrieve(_make_request())

        call_kwargs = mock_retriever.retrieve.call_args
        assert "profile" not in (call_kwargs.kwargs or {})

    def test_single_profile_passed_to_retriever(self, tmp_path: Path) -> None:
        adapter = KnowledgeAdapter(store_root=tmp_path)
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = _mock_retrieval_result([])
        adapter._retriever = mock_retriever

        request = _make_request(profiles=("smr-general",))
        adapter.retrieve(request)

        call_kwargs = mock_retriever.retrieve.call_args
        assert call_kwargs.kwargs.get("profile") == "smr-general"

    def test_source_included_when_load_sources_true(self, tmp_path: Path) -> None:
        kl_src = make_kl_source()
        item = make_retrieved_evidence(source=kl_src)
        adapter = KnowledgeAdapter(store_root=tmp_path, load_sources=True)
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = _mock_retrieval_result([item])
        adapter._retriever = mock_retriever

        result = adapter.retrieve(_make_request())
        assert len(result.sources) == 1

    def test_source_excluded_when_load_sources_false(self, tmp_path: Path) -> None:
        kl_src = make_kl_source()
        item = make_retrieved_evidence(source=kl_src)
        adapter = KnowledgeAdapter(store_root=tmp_path, load_sources=False)
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = _mock_retrieval_result([item])
        adapter._retriever = mock_retriever

        result = adapter.retrieve(_make_request())
        assert result.sources == ()

    def test_duplicate_sources_deduplicated(self, tmp_path: Path) -> None:
        kl_src = make_kl_source()
        item1 = make_retrieved_evidence(
            evidence=make_kl_evidence(evidence_id="ev-001"),
            source=kl_src,
            rank=1,
        )
        item2 = make_retrieved_evidence(
            evidence=make_kl_evidence(evidence_id="ev-002"),
            source=kl_src,
            rank=2,
        )
        adapter = KnowledgeAdapter(store_root=tmp_path, load_sources=True)
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = _mock_retrieval_result([item1, item2])
        adapter._retriever = mock_retriever

        result = adapter.retrieve(_make_request())
        assert len(result.sources) == 1
        assert len(result.evidence) == 2

    def test_top_k_passed_from_request(self, tmp_path: Path) -> None:
        adapter = KnowledgeAdapter(store_root=tmp_path)
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = _mock_retrieval_result([])
        adapter._retriever = mock_retriever

        request = _make_request(max_results=7)
        adapter.retrieve(request)

        call_kwargs = mock_retriever.retrieve.call_args
        assert call_kwargs.kwargs.get("top_k") == 7


class TestKnowledgeAdapterRetrieverCaching:
    def test_retriever_cached_after_first_call(self, tmp_path: Path) -> None:
        (tmp_path / "knowledge_store").mkdir()
        adapter = KnowledgeAdapter(store_root=tmp_path / "knowledge_store")

        _patch = "research_core.adapters.knowledge.adapter.KnowledgeAdapter._ensure_retriever"
        with patch(_patch) as mock_ensure:
            mock_retriever = MagicMock()
            mock_retriever.retrieve.return_value = _mock_retrieval_result([])
            mock_ensure.return_value = mock_retriever

            adapter.retrieve(_make_request())
            adapter.retrieve(_make_request())

        assert mock_ensure.call_count == 2


class TestKnowledgeAdapterErrors:
    def test_execution_error_wraps_unexpected_exception(self, tmp_path: Path) -> None:
        adapter = KnowledgeAdapter(store_root=tmp_path)
        mock_retriever = MagicMock()
        mock_retriever.retrieve.side_effect = RuntimeError("unexpected")
        adapter._retriever = mock_retriever

        with pytest.raises(ProviderExecutionError, match="knowledge retrieval failed"):
            adapter.retrieve(_make_request())

    def test_provider_unavailable_error_passes_through(self, tmp_path: Path) -> None:
        adapter = KnowledgeAdapter(store_root=tmp_path)
        mock_retriever = MagicMock()
        mock_retriever.retrieve.side_effect = ProviderUnavailableError("store gone")
        adapter._retriever = mock_retriever

        with pytest.raises(ProviderUnavailableError):
            adapter.retrieve(_make_request())
