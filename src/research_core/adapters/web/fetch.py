"""
Page fetcher boundary for the web search adapter.

RequestsFetcher wraps the requests package behind the PageFetcher protocol.
The requests package is imported lazily at fetch() time.

Response size is bounded at _MAX_RESPONSE_BYTES (10 MB) using streaming.
Redirect following is bounded at _MAX_REDIRECTS (10).

Supported URL schemes: http and https only. Other schemes raise
ProviderExecutionError before any network access.

HTTP error responses (4xx, 5xx) are returned as FetchedResource with the
corresponding status_code — the caller decides whether to skip or fail.
Connection errors, timeouts, and redirect exhaustion raise ProviderExecutionError.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlparse

from research_core.adapters.web.models import FetchedResource
from research_core.exceptions import ProviderExecutionError

_MAX_RESPONSE_BYTES: int = 10 * 1024 * 1024  # 10 MB
_MAX_REDIRECTS: int = 10
_USER_AGENT = "Mozilla/5.0 (compatible; research-core/0.3)"
_ALLOWED_SCHEMES = {"http", "https"}


@runtime_checkable
class PageFetcher(Protocol):
    """Internal protocol for a web page fetcher."""

    def fetch(self, url: str, *, timeout_seconds: float) -> FetchedResource:
        """Fetch url and return a FetchedResource. Raises ProviderExecutionError on failure."""
        ...


class RequestsFetcher:
    """PageFetcher backed by the requests package.

    Imports requests lazily on the first fetch() call.
    """

    def __init__(
        self,
        *,
        max_response_bytes: int = _MAX_RESPONSE_BYTES,
        max_redirects: int = _MAX_REDIRECTS,
    ) -> None:
        self._max_response_bytes = max_response_bytes
        self._max_redirects = max_redirects

    def fetch(self, url: str, *, timeout_seconds: float) -> FetchedResource:
        """Fetch url and return a FetchedResource.

        Raises ProviderExecutionError for:
        - unsupported URL schemes (non-http/https)
        - connection errors
        - timeouts
        - too many redirects
        - other request-level failures

        HTTP error responses (4xx, 5xx) are returned with the status_code;
        the caller decides how to handle them.
        """
        parsed = urlparse(url)
        if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
            raise ProviderExecutionError(
                f"unsupported URL scheme {parsed.scheme!r} in {url!r}; "
                f"only http and https are supported"
            )

        requests = self._import_requests()

        try:
            session = requests.Session()
            session.max_redirects = self._max_redirects
            resp = session.get(
                url,
                timeout=timeout_seconds,
                headers={"User-Agent": _USER_AGENT},
                stream=True,
            )
        except Exception as exc:
            exc_type = type(exc).__name__
            if "Timeout" in exc_type:
                raise ProviderExecutionError(
                    f"fetch timed out after {timeout_seconds}s for {url!r}: {exc}"
                ) from exc
            if "TooManyRedirects" in exc_type:
                raise ProviderExecutionError(
                    f"too many redirects fetching {url!r}: {exc}"
                ) from exc
            raise ProviderExecutionError(
                f"fetch failed for {url!r}: {exc_type}: {exc}"
            ) from exc

        retrieved_at = datetime.now(UTC)
        final_url = resp.url or url
        content_type = resp.headers.get("Content-Type", "")
        encoding = resp.encoding or None

        # Read body bounded by max_response_bytes
        chunks: list[bytes] = []
        total = 0
        truncated = False
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                total += len(chunk)
                if total > self._max_response_bytes:
                    chunks.append(chunk[: self._max_response_bytes - (total - len(chunk))])
                    truncated = True
                    break
                chunks.append(chunk)
        resp.close()

        content = b"".join(chunks)

        return FetchedResource(
            requested_url=url,
            final_url=final_url,
            status_code=resp.status_code,
            content_type=content_type,
            content=content,
            retrieved_at=retrieved_at,
            encoding=encoding,
            truncated=truncated,
        )

    @staticmethod
    def _import_requests() -> Any:
        try:
            import requests

            return requests
        except ImportError as exc:
            raise ProviderExecutionError(
                "requests package is not installed. Install with: pip install requests"
            ) from exc
