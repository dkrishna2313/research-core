"""Tests for DdgsSearchClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.web

from research_core.adapters.web.search import DdgsSearchClient  # noqa: E402
from research_core.exceptions import ProviderExecutionError, ProviderUnavailableError  # noqa: E402


def _mock_ddgs_class(results: list[dict]) -> MagicMock:
    """Return a mock DDGS class whose context manager yields results."""
    mock_instance = MagicMock()
    mock_instance.text.return_value = iter(results)
    mock_instance.__enter__ = MagicMock(return_value=mock_instance)
    mock_instance.__exit__ = MagicMock(return_value=False)
    mock_cls = MagicMock(return_value=mock_instance)
    return mock_cls


class TestDdgsSearchClientSearch:
    def _search(self, results: list[dict], **kwargs: object) -> object:
        client = DdgsSearchClient()
        mock_cls = _mock_ddgs_class(results)
        with patch.object(client, "_import_ddgs", return_value=mock_cls):
            return client.search(
                query="test query",
                max_results=kwargs.get("max_results", 5),  # type: ignore[arg-type]
                language=kwargs.get("language"),  # type: ignore[arg-type]
                safe_search=kwargs.get("safe_search"),  # type: ignore[arg-type]
                timeout_seconds=kwargs.get("timeout_seconds", 10.0),  # type: ignore[arg-type]
            )

    def test_returns_tuple_of_search_hits(self) -> None:
        from research_core.adapters.web.models import SearchHit

        results = [{"href": "https://example.com", "title": "Example", "body": "Body text"}]
        hits = self._search(results)
        assert isinstance(hits, tuple)
        assert len(hits) == 1
        assert isinstance(hits[0], SearchHit)

    def test_rank_starts_at_one(self) -> None:
        results = [
            {"href": "https://example.com/a", "title": "A", "body": ""},
            {"href": "https://example.com/b", "title": "B", "body": ""},
        ]
        hits = self._search(results)
        assert hits[0].rank == 1
        assert hits[1].rank == 2

    def test_url_preserved(self) -> None:
        results = [{"href": "https://example.com/page", "title": "T", "body": ""}]
        hits = self._search(results)
        assert hits[0].url == "https://example.com/page"

    def test_title_preserved(self) -> None:
        results = [{"href": "https://example.com", "title": "My Title", "body": ""}]
        hits = self._search(results)
        assert hits[0].title == "My Title"

    def test_snippet_preserved(self) -> None:
        results = [{"href": "https://example.com", "title": "T", "body": "Snippet text"}]
        hits = self._search(results)
        assert hits[0].snippet == "Snippet text"

    def test_provider_set_to_duckduckgo(self) -> None:
        results = [{"href": "https://example.com", "title": "T", "body": ""}]
        hits = self._search(results)
        assert hits[0].provider == "duckduckgo"

    def test_items_without_href_are_filtered(self) -> None:
        results = [
            {"href": "", "title": "No URL", "body": ""},
            {"href": "https://example.com", "title": "Valid", "body": ""},
        ]
        hits = self._search(results)
        assert len(hits) == 1
        assert hits[0].url == "https://example.com"

    def test_items_with_none_href_are_filtered(self) -> None:
        results = [
            {"href": None, "title": "No URL", "body": ""},
            {"href": "https://example.com", "title": "Valid", "body": ""},
        ]
        hits = self._search(results)
        assert len(hits) == 1

    def test_empty_results_returns_empty_tuple(self) -> None:
        hits = self._search([])
        assert hits == ()

    def test_language_passed_as_region(self) -> None:
        client = DdgsSearchClient()
        mock_cls = _mock_ddgs_class([])
        mock_instance = mock_cls.return_value
        with patch.object(client, "_import_ddgs", return_value=mock_cls):
            client.search(
                query="test",
                max_results=5,
                language="de-de",
                safe_search=None,
                timeout_seconds=10.0,
            )
        call_kwargs = mock_instance.text.call_args.kwargs
        assert call_kwargs.get("region") == "de-de"

    def test_language_none_uses_worldwide_region(self) -> None:
        client = DdgsSearchClient()
        mock_cls = _mock_ddgs_class([])
        mock_instance = mock_cls.return_value
        with patch.object(client, "_import_ddgs", return_value=mock_cls):
            client.search(
                query="test",
                max_results=5,
                language=None,
                safe_search=None,
                timeout_seconds=10.0,
            )
        call_kwargs = mock_instance.text.call_args.kwargs
        assert call_kwargs.get("region") == "wt-wt"

    def test_provider_exception_raises_execution_error(self) -> None:
        client = DdgsSearchClient()
        mock_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.text.side_effect = RuntimeError("ddgs failure")
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_cls.return_value = mock_instance
        with (
            patch.object(client, "_import_ddgs", return_value=mock_cls),
            pytest.raises(ProviderExecutionError, match="DuckDuckGo search failed"),
        ):
            client.search(
                query="test",
                max_results=5,
                language=None,
                safe_search=None,
                timeout_seconds=10.0,
            )

    def test_missing_ddgs_raises_unavailable_error(self) -> None:
        import sys

        with (
            patch.dict(
                sys.modules,
                {"ddgs": None, "duckduckgo_search": None},  # type: ignore[dict-item]
            ),
            pytest.raises(ProviderUnavailableError, match="ddgs"),
        ):
            client = DdgsSearchClient()
            client._import_ddgs()
