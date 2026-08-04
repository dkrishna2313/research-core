"""Tests for KnowledgeAdapter error handling."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from research_core.adapters.knowledge.adapter import KnowledgeAdapter
from research_core.exceptions import ProviderExecutionError, ProviderUnavailableError
from research_core.protocols.knowledge import KnowledgeRetrievalRequest
from tests.conftest import make_research_request

pytestmark = pytest.mark.knowledge


def _make_request() -> KnowledgeRetrievalRequest:
    return KnowledgeRetrievalRequest(
        query="test query",
        parent_request=make_research_request(),
    )


class TestKnowledgePackageMissing:
    def test_is_available_returns_false_when_package_missing(self, tmp_path: Path) -> None:
        with patch.dict(sys.modules, {"knowledge": None}):  # type: ignore[dict-item]
            result = KnowledgeAdapter.is_available()
        assert result is False

    def test_ensure_retriever_raises_provider_unavailable_when_missing(
        self, tmp_path: Path
    ) -> None:
        adapter = KnowledgeAdapter(store_root=tmp_path)
        modules: dict[str, None] = {
            "knowledge": None,
            "knowledge.retriever": None,
            "knowledge.store": None,
        }
        with (
            patch.dict(sys.modules, modules),  # type: ignore[arg-type]
            pytest.raises(ProviderUnavailableError, match="knowledge package"),
        ):
            adapter._ensure_retriever()


class TestStoreInitializationFailure:
    def test_store_error_raises_provider_unavailable(self, tmp_path: Path) -> None:
        adapter = KnowledgeAdapter(store_root=tmp_path / "nonexistent_store")

        with (
            patch(
                "knowledge.store.KnowledgeStore.__init__",
                side_effect=RuntimeError("disk full"),
            ),
            pytest.raises(ProviderUnavailableError, match="failed to initialize"),
        ):
            adapter._ensure_retriever()


class TestRetrievalFailure:
    def test_unexpected_exception_wrapped_as_execution_error(self, tmp_path: Path) -> None:
        adapter = KnowledgeAdapter(store_root=tmp_path)
        mock_retriever = MagicMock()
        mock_retriever.retrieve.side_effect = ValueError("malformed query")
        adapter._retriever = mock_retriever

        with pytest.raises(ProviderExecutionError, match="knowledge retrieval failed"):
            adapter.retrieve(_make_request())

    def test_execution_error_message_includes_query(self, tmp_path: Path) -> None:
        adapter = KnowledgeAdapter(store_root=tmp_path)
        mock_retriever = MagicMock()
        mock_retriever.retrieve.side_effect = RuntimeError("timeout")
        adapter._retriever = mock_retriever

        request = _make_request()
        with pytest.raises(ProviderExecutionError) as exc_info:
            adapter.retrieve(request)
        assert request.query in str(exc_info.value)

    def test_provider_unavailable_error_not_re_wrapped(self, tmp_path: Path) -> None:
        adapter = KnowledgeAdapter(store_root=tmp_path)
        mock_retriever = MagicMock()
        mock_retriever.retrieve.side_effect = ProviderUnavailableError("store gone")
        adapter._retriever = mock_retriever

        with pytest.raises(ProviderUnavailableError, match="store gone"):
            adapter.retrieve(_make_request())

    def test_execution_error_not_re_wrapped(self, tmp_path: Path) -> None:
        adapter = KnowledgeAdapter(store_root=tmp_path)
        mock_retriever = MagicMock()
        mock_retriever.retrieve.side_effect = ProviderExecutionError("bad response")
        adapter._retriever = mock_retriever

        with pytest.raises(ProviderExecutionError, match="bad response"):
            adapter.retrieve(_make_request())
