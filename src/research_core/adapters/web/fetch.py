"""
Page fetcher boundary for the web search adapter.

RequestsFetcher wraps the requests package behind the PageFetcher protocol.
The requests package is imported lazily at fetch() time.

Response size is bounded at _MAX_RESPONSE_BYTES (10 MB) using streaming.
Redirect following is bounded at _MAX_REDIRECTS (10) with per-hop SSRF validation.

Supported URL schemes: http and https only. Other schemes raise
ProviderExecutionError before any network access.

SSRF protection: every URL (including redirect destinations) is validated by
resolving the hostname and blocking RFC 1918, loopback, link-local, multicast,
and cloud-metadata IP ranges. Manual redirect following ensures each hop is
validated before the request is made.

HTTP error responses (4xx, 5xx) are returned as FetchedResource with the
corresponding status_code — the caller decides whether to skip or fail.
Connection errors, timeouts, and redirect exhaustion raise ProviderExecutionError.
"""

from __future__ import annotations

import ipaddress
import socket
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urljoin, urlparse

from research_core.adapters.web.models import FetchedResource
from research_core.exceptions import ProviderExecutionError

_MAX_RESPONSE_BYTES: int = 10 * 1024 * 1024  # 10 MB
_MAX_REDIRECTS: int = 10
_USER_AGENT = "Mozilla/5.0 (compatible; research-core/0.4)"
_ALLOWED_SCHEMES = {"http", "https"}

_BLOCKED_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network("0.0.0.0/8"),  # unspecified / "this network" (RFC 1122)
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / metadata
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("224.0.0.0/4"),  # multicast
    ipaddress.ip_network("::/128"),  # IPv6 unspecified
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
    ipaddress.ip_network("ff00::/8"),  # IPv6 multicast
]


@runtime_checkable
class HostResolver(Protocol):
    """Internal protocol for resolving hostnames to IP addresses."""

    def resolve(self, hostname: str, port: int) -> list[str]:
        """Return resolved IP address strings for (hostname, port). Empty list = unresolvable."""
        ...


class DefaultHostResolver:
    """Production host resolver using socket.getaddrinfo."""

    def resolve(self, hostname: str, port: int) -> list[str]:
        try:
            results = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
            return [str(r[4][0]) for r in results]
        except OSError:
            return []


@runtime_checkable
class PageFetcher(Protocol):
    """Internal protocol for a web page fetcher."""

    def fetch(self, url: str, *, timeout_seconds: float) -> FetchedResource:
        """Fetch url and return a FetchedResource. Raises ProviderExecutionError on failure."""
        ...


def _is_blocked_ip(addr_str: str) -> bool:
    """Return True if addr_str is a private/internal/blocked address."""
    try:
        addr: ipaddress.IPv4Address | ipaddress.IPv6Address = ipaddress.ip_address(addr_str)
        # Unwrap IPv4-mapped IPv6 (e.g. ::ffff:169.254.169.254)
        if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
            addr = addr.ipv4_mapped
        return any(addr in net for net in _BLOCKED_NETWORKS)
    except ValueError:
        return True  # unparseable address → blocked


def _validate_url_ssrf(url: str, resolver: HostResolver) -> None:
    """Raise ProviderExecutionError if url resolves to a blocked address or contains credentials."""
    parsed = urlparse(url)
    hostname = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    if parsed.username or parsed.password:
        raise ProviderExecutionError(
            f"SSRF protection: embedded credentials are not permitted in {url!r}"
        )

    if not hostname:
        raise ProviderExecutionError(f"could not parse hostname from URL {url!r}")

    addresses = resolver.resolve(hostname, port)
    if not addresses:
        raise ProviderExecutionError(
            f"could not resolve hostname {hostname!r} in {url!r}"
        )

    for addr in addresses:
        if _is_blocked_ip(addr):
            raise ProviderExecutionError(
                f"SSRF protection: {hostname!r} resolves to blocked address {addr!r} in {url!r}"
            )


class RequestsFetcher:
    """PageFetcher backed by the requests package.

    Imports requests lazily on the first fetch() call.
    Uses manual redirect following with per-hop SSRF validation.
    """

    def __init__(
        self,
        *,
        max_response_bytes: int = _MAX_RESPONSE_BYTES,
        max_redirects: int = _MAX_REDIRECTS,
        resolver: HostResolver | None = None,
    ) -> None:
        self._max_response_bytes = max_response_bytes
        self._max_redirects = max_redirects
        self._resolver: HostResolver = resolver if resolver is not None else DefaultHostResolver()

    def fetch(self, url: str, *, timeout_seconds: float) -> FetchedResource:
        """Fetch url and return a FetchedResource.

        Raises ProviderExecutionError for:
        - unsupported URL schemes (non-http/https)
        - SSRF-blocked destinations (private/internal IPs)
        - unresolvable hostnames
        - connection errors
        - timeouts
        - too many redirects
        - other request-level failures

        HTTP error responses (4xx, 5xx) are returned with the status_code.
        """
        parsed = urlparse(url)
        if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
            raise ProviderExecutionError(
                f"unsupported URL scheme {parsed.scheme!r} in {url!r}; "
                f"only http and https are supported"
            )

        # Validate the initial URL before making any network call
        _validate_url_ssrf(url, self._resolver)

        requests = self._import_requests()

        try:
            session = requests.Session()
            # Disable automatic redirects so we can validate each hop
            current_url = url
            resp = None

            for _ in range(self._max_redirects + 1):
                resp = session.get(
                    current_url,
                    timeout=timeout_seconds,
                    headers={"User-Agent": _USER_AGENT},
                    stream=True,
                    allow_redirects=False,
                )
                status = resp.status_code
                if status not in (301, 302, 303, 307, 308):
                    break

                location = resp.headers.get("Location", "")
                if not location:
                    raise ProviderExecutionError(
                        f"redirect from {current_url!r} had no Location header"
                    )

                next_url = urljoin(current_url, location)
                next_parsed = urlparse(next_url)
                if next_parsed.scheme.lower() not in _ALLOWED_SCHEMES:
                    raise ProviderExecutionError(
                        f"redirect to unsupported scheme {next_parsed.scheme!r} in {next_url!r}"
                    )

                _validate_url_ssrf(next_url, self._resolver)
                current_url = next_url
            else:
                raise ProviderExecutionError(
                    f"too many redirects fetching {url!r}"
                )

        except ProviderExecutionError:
            raise
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

        if resp is None:
            raise ProviderExecutionError(f"no response received for {url!r}")

        retrieved_at = datetime.now(UTC)
        final_url = resp.url or current_url
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
