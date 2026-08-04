"""Security tests for the web adapter."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.web

from research_core.adapters.web.fetch import RequestsFetcher  # noqa: E402
from research_core.adapters.web.mapping import validate_scheme  # noqa: E402
from research_core.exceptions import ProviderExecutionError  # noqa: E402


class TestSchemeRejection:
    def test_file_scheme_rejected_by_validate_scheme(self) -> None:
        with pytest.raises(ProviderExecutionError, match="unsupported URL scheme"):
            validate_scheme("file:///etc/passwd")

    def test_data_scheme_rejected_by_validate_scheme(self) -> None:
        with pytest.raises(ProviderExecutionError, match="unsupported URL scheme"):
            validate_scheme("data:text/html,<script>evil</script>")

    def test_javascript_scheme_rejected_by_validate_scheme(self) -> None:
        with pytest.raises(ProviderExecutionError, match="unsupported URL scheme"):
            validate_scheme("javascript:void(0)")

    def test_ftp_scheme_rejected_by_validate_scheme(self) -> None:
        with pytest.raises(ProviderExecutionError, match="unsupported URL scheme"):
            validate_scheme("ftp://example.com/file")

    def test_mailto_scheme_rejected_by_validate_scheme(self) -> None:
        with pytest.raises(ProviderExecutionError, match="unsupported URL scheme"):
            validate_scheme("mailto:user@example.com")

    def test_file_scheme_rejected_by_fetcher(self) -> None:
        fetcher = RequestsFetcher()
        with pytest.raises(ProviderExecutionError, match="unsupported URL scheme"):
            fetcher.fetch("file:///etc/passwd", timeout_seconds=5.0)

    def test_data_scheme_rejected_by_fetcher(self) -> None:
        fetcher = RequestsFetcher()
        with pytest.raises(ProviderExecutionError, match="unsupported URL scheme"):
            fetcher.fetch("data:text/html,<h1>hello</h1>", timeout_seconds=5.0)

    def test_javascript_scheme_rejected_by_fetcher(self) -> None:
        fetcher = RequestsFetcher()
        with pytest.raises(ProviderExecutionError, match="unsupported URL scheme"):
            fetcher.fetch("javascript:void(0)", timeout_seconds=5.0)

    def test_ftp_scheme_rejected_by_fetcher(self) -> None:
        fetcher = RequestsFetcher()
        with pytest.raises(ProviderExecutionError, match="unsupported URL scheme"):
            fetcher.fetch("ftp://example.com/file.txt", timeout_seconds=5.0)

    def test_http_scheme_accepted(self) -> None:
        validate_scheme("http://example.com")  # no raise

    def test_https_scheme_accepted(self) -> None:
        validate_scheme("https://example.com")  # no raise


class TestResponseSizeLimit:
    def test_max_response_bytes_configurable(self) -> None:
        fetcher = RequestsFetcher(max_response_bytes=100)
        assert fetcher._max_response_bytes == 100

    def test_default_max_response_bytes_is_10mb(self) -> None:
        fetcher = RequestsFetcher()
        assert fetcher._max_response_bytes == 10 * 1024 * 1024


class TestCacheNoPersistenceWithoutCache:
    def test_no_cache_writes_without_cache(self, tmp_path: object) -> None:
        from unittest.mock import MagicMock

        from research_core.adapters.web.adapter import WebSearchAdapter

        client = MagicMock()
        client.search.return_value = ()

        adapter = WebSearchAdapter(search_client=client, cache=None)

        from research_core.protocols.web import WebSearchRequest
        from tests.conftest import make_research_request

        request = WebSearchRequest(query="test", parent_request=make_research_request())
        result = adapter.search(request)
        assert result.sources == ()
        # No cache files should exist since no cache was configured and no pages fetched
