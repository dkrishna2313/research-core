"""Tests for RequestsFetcher."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.web

from research_core.adapters.web.fetch import RequestsFetcher  # noqa: E402
from research_core.adapters.web.models import FetchedResource  # noqa: E402
from research_core.exceptions import ProviderExecutionError  # noqa: E402
from tests.adapters.web.conftest import FakeResolver  # noqa: E402


def _mock_session(
    status_code: int = 200,
    content_type: str = "text/html",
    content: bytes = b"<html>content</html>",
    final_url: str = "https://example.com/page",
    exc: Exception | None = None,
) -> MagicMock:
    """Build a mock requests.Session that returns a fake response."""
    mock_session_cls = MagicMock()
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    if exc is not None:
        mock_session.get.side_effect = exc
    else:
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.url = final_url
        mock_resp.headers = {"Content-Type": content_type}
        mock_resp.encoding = "utf-8"

        # iter_content yields content in one chunk
        mock_resp.iter_content = MagicMock(return_value=iter([content]))
        mock_resp.close = MagicMock()
        mock_session.get.return_value = mock_resp

    return mock_session_cls


def _requests_module(session_cls: MagicMock) -> MagicMock:
    mock_requests = MagicMock()
    mock_requests.Session = session_cls
    return mock_requests


class TestRequestsFetcherSchemeValidation:
    def test_file_scheme_rejected(self) -> None:
        fetcher = RequestsFetcher(resolver=FakeResolver())
        with pytest.raises(ProviderExecutionError, match="unsupported URL scheme"):
            fetcher.fetch("file:///etc/passwd", timeout_seconds=5.0)

    def test_data_scheme_rejected(self) -> None:
        fetcher = RequestsFetcher(resolver=FakeResolver())
        with pytest.raises(ProviderExecutionError, match="unsupported URL scheme"):
            fetcher.fetch("data:text/html,hello", timeout_seconds=5.0)

    def test_javascript_scheme_rejected(self) -> None:
        fetcher = RequestsFetcher(resolver=FakeResolver())
        with pytest.raises(ProviderExecutionError, match="unsupported URL scheme"):
            fetcher.fetch("javascript:void(0)", timeout_seconds=5.0)

    def test_ftp_scheme_rejected(self) -> None:
        fetcher = RequestsFetcher(resolver=FakeResolver())
        with pytest.raises(ProviderExecutionError, match="unsupported URL scheme"):
            fetcher.fetch("ftp://example.com/file.txt", timeout_seconds=5.0)

    def test_mailto_scheme_rejected(self) -> None:
        fetcher = RequestsFetcher(resolver=FakeResolver())
        with pytest.raises(ProviderExecutionError, match="unsupported URL scheme"):
            fetcher.fetch("mailto:user@example.com", timeout_seconds=5.0)


class TestRequestsFetcherSuccessPath:
    def test_returns_fetched_resource(self) -> None:
        fetcher = RequestsFetcher(resolver=FakeResolver())
        session_cls = _mock_session(content=b"hello")
        mock_req = _requests_module(session_cls)
        with patch.object(fetcher, "_import_requests", return_value=mock_req):
            result = fetcher.fetch("https://example.com", timeout_seconds=5.0)
        assert isinstance(result, FetchedResource)

    def test_status_code_preserved(self) -> None:
        fetcher = RequestsFetcher(resolver=FakeResolver())
        session_cls = _mock_session(status_code=200, content=b"ok")
        mock_req = _requests_module(session_cls)
        with patch.object(fetcher, "_import_requests", return_value=mock_req):
            result = fetcher.fetch("https://example.com", timeout_seconds=5.0)
        assert result.status_code == 200

    def test_404_returned_as_fetched_resource(self) -> None:
        fetcher = RequestsFetcher(resolver=FakeResolver())
        session_cls = _mock_session(status_code=404, content=b"not found")
        mock_req = _requests_module(session_cls)
        with patch.object(fetcher, "_import_requests", return_value=mock_req):
            result = fetcher.fetch("https://example.com/missing", timeout_seconds=5.0)
        assert result.status_code == 404

    def test_403_returned_as_fetched_resource(self) -> None:
        fetcher = RequestsFetcher(resolver=FakeResolver())
        session_cls = _mock_session(status_code=403, content=b"forbidden")
        mock_req = _requests_module(session_cls)
        with patch.object(fetcher, "_import_requests", return_value=mock_req):
            result = fetcher.fetch("https://example.com/forbidden", timeout_seconds=5.0)
        assert result.status_code == 403

    def test_final_url_preserved_after_redirect(self) -> None:
        fetcher = RequestsFetcher(resolver=FakeResolver())
        session_cls = _mock_session(
            final_url="https://example.com/redirected",
            content=b"content",
        )
        mock_req = _requests_module(session_cls)
        with patch.object(fetcher, "_import_requests", return_value=mock_req):
            result = fetcher.fetch("https://example.com/original", timeout_seconds=5.0)
        assert result.final_url == "https://example.com/redirected"
        assert result.requested_url == "https://example.com/original"

    def test_retrieved_at_is_timezone_aware(self) -> None:
        fetcher = RequestsFetcher(resolver=FakeResolver())
        session_cls = _mock_session(content=b"ok")
        mock_req = _requests_module(session_cls)
        with patch.object(fetcher, "_import_requests", return_value=mock_req):
            result = fetcher.fetch("https://example.com", timeout_seconds=5.0)
        assert result.retrieved_at.tzinfo is not None

    def test_content_type_preserved(self) -> None:
        fetcher = RequestsFetcher(resolver=FakeResolver())
        session_cls = _mock_session(content_type="application/pdf", content=b"%PDF")
        mock_req = _requests_module(session_cls)
        with patch.object(fetcher, "_import_requests", return_value=mock_req):
            result = fetcher.fetch("https://example.com/doc.pdf", timeout_seconds=5.0)
        assert "application/pdf" in result.content_type

    def test_content_preserved(self) -> None:
        body = b"Hello, world!"
        fetcher = RequestsFetcher(resolver=FakeResolver())
        session_cls = _mock_session(content=body)
        mock_req = _requests_module(session_cls)
        with patch.object(fetcher, "_import_requests", return_value=mock_req):
            result = fetcher.fetch("https://example.com", timeout_seconds=5.0)
        assert result.content == body


class TestRequestsFetcherErrors:
    def _make_exc_with_name(self, name: str) -> Exception:
        cls = type(name, (Exception,), {})
        return cls("error message")

    def test_timeout_raises_execution_error(self) -> None:
        fetcher = RequestsFetcher(resolver=FakeResolver())
        exc = self._make_exc_with_name("ReadTimeout")
        session_cls = _mock_session(exc=exc)
        mock_req = _requests_module(session_cls)
        with (
            patch.object(fetcher, "_import_requests", return_value=mock_req),
            pytest.raises(ProviderExecutionError, match="timed out"),
        ):
            fetcher.fetch("https://example.com", timeout_seconds=1.0)

    def test_too_many_redirects_raises_execution_error(self) -> None:
        fetcher = RequestsFetcher(resolver=FakeResolver())
        exc = self._make_exc_with_name("TooManyRedirects")
        session_cls = _mock_session(exc=exc)
        mock_req = _requests_module(session_cls)
        with (
            patch.object(fetcher, "_import_requests", return_value=mock_req),
            pytest.raises(ProviderExecutionError, match="too many redirects"),
        ):
            fetcher.fetch("https://example.com", timeout_seconds=5.0)

    def test_connection_error_raises_execution_error(self) -> None:
        fetcher = RequestsFetcher(resolver=FakeResolver())
        exc = self._make_exc_with_name("ConnectionError")
        session_cls = _mock_session(exc=exc)
        mock_req = _requests_module(session_cls)
        with (
            patch.object(fetcher, "_import_requests", return_value=mock_req),
            pytest.raises(ProviderExecutionError, match="fetch failed"),
        ):
            fetcher.fetch("https://example.com", timeout_seconds=5.0)

    def test_missing_requests_raises_execution_error(self) -> None:
        import sys

        fetcher = RequestsFetcher(resolver=FakeResolver())
        with (
            patch.dict(sys.modules, {"requests": None}),  # type: ignore[dict-item]
            pytest.raises(ProviderExecutionError, match="requests"),
        ):
            fetcher._import_requests()


class TestRequestsFetcherSizeLimit:
    def test_response_truncated_at_max_bytes(self) -> None:
        max_bytes = 100
        content = b"x" * 200  # larger than limit
        fetcher = RequestsFetcher(max_response_bytes=max_bytes, resolver=FakeResolver())

        # Simulate streaming in chunks of 50 bytes
        mock_session_cls = MagicMock()
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://example.com"
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_resp.encoding = "utf-8"

        # Provide content in 50-byte chunks
        chunks = [content[i : i + 50] for i in range(0, len(content), 50)]
        mock_resp.iter_content = MagicMock(return_value=iter(chunks))
        mock_resp.close = MagicMock()
        mock_session.get.return_value = mock_resp

        mock_req = _requests_module(mock_session_cls)
        with patch.object(fetcher, "_import_requests", return_value=mock_req):
            result = fetcher.fetch("https://example.com", timeout_seconds=5.0)

        assert result.truncated is True
        assert len(result.content) <= max_bytes
