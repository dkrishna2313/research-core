"""Tests for error handling and exception translation in the web adapter."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.web

from research_core.adapters.web.adapter import WebSearchAdapter  # noqa: E402
from research_core.exceptions import ProviderExecutionError, ProviderUnavailableError  # noqa: E402
from research_core.protocols.web import WebSearchRequest  # noqa: E402
from tests.conftest import make_research_request  # noqa: E402


def _make_request() -> WebSearchRequest:
    return WebSearchRequest(query="test query", parent_request=make_research_request())


class TestProviderUnavailablePassthrough:
    def test_provider_unavailable_not_wrapped(self) -> None:
        client = MagicMock()
        client.search.side_effect = ProviderUnavailableError("no ddgs")
        adapter = WebSearchAdapter(search_client=client)
        with pytest.raises(ProviderUnavailableError, match="no ddgs"):
            adapter.search(_make_request())


class TestProviderExecutionPassthrough:
    def test_execution_error_not_wrapped(self) -> None:
        client = MagicMock()
        client.search.side_effect = ProviderExecutionError("search failed")
        adapter = WebSearchAdapter(search_client=client)
        with pytest.raises(ProviderExecutionError, match="search failed"):
            adapter.search(_make_request())


class TestUnexpectedExceptionWrapping:
    def test_unexpected_exception_wrapped(self) -> None:
        client = MagicMock()
        client.search.side_effect = RuntimeError("unexpected boom")
        adapter = WebSearchAdapter(search_client=client)
        with pytest.raises(ProviderExecutionError, match="web search failed"):
            adapter.search(_make_request())


class TestMissingDependencyErrors:
    def test_missing_ddgs_raises_unavailable(self) -> None:
        with patch.dict(
            sys.modules,
            {"ddgs": None, "duckduckgo_search": None},  # type: ignore[dict-item]
        ):
            from research_core.adapters.web.search import DdgsSearchClient

            client = DdgsSearchClient()
            with pytest.raises(ProviderUnavailableError, match="ddgs"):
                client._import_ddgs()

    def test_missing_requests_raises_on_fetch(self) -> None:
        from research_core.adapters.web.fetch import RequestsFetcher

        fetcher = RequestsFetcher()
        with (
            patch.dict(sys.modules, {"requests": None}),  # type: ignore[dict-item]
            pytest.raises(ProviderExecutionError, match="requests"),
        ):
            fetcher._import_requests()

    def test_missing_trafilatura_raises_on_extract(self) -> None:
        from datetime import UTC, datetime

        from research_core.adapters.web.extract import TrafilaturaExtractor
        from research_core.adapters.web.models import FetchedResource

        ext = TrafilaturaExtractor()
        resource = FetchedResource(
            requested_url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="text/html",
            content=b"<html>test</html>",
            retrieved_at=datetime.now(UTC),
        )
        with (
            patch.dict(sys.modules, {"trafilatura": None}),  # type: ignore[dict-item]
            pytest.raises(ProviderExecutionError, match="trafilatura"),
        ):
            ext.extract(resource)
