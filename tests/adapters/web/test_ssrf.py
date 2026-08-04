"""Tests for SSRF validation in the web page fetcher."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.web

from research_core.adapters.web.fetch import (  # noqa: E402
    DefaultHostResolver,
    RequestsFetcher,
    _is_blocked_ip,
    _validate_url_ssrf,
)
from research_core.exceptions import ProviderExecutionError  # noqa: E402
from tests.adapters.web.conftest import FakeResolver  # noqa: E402


class TestIsBlockedIp:
    def test_public_ip_allowed(self) -> None:
        assert _is_blocked_ip("1.2.3.4") is False
        assert _is_blocked_ip("8.8.8.8") is False
        assert _is_blocked_ip("93.184.216.34") is False

    def test_rfc1918_10_blocked(self) -> None:
        assert _is_blocked_ip("10.0.0.1") is True
        assert _is_blocked_ip("10.255.255.255") is True

    def test_rfc1918_172_blocked(self) -> None:
        assert _is_blocked_ip("172.16.0.1") is True
        assert _is_blocked_ip("172.31.255.255") is True

    def test_rfc1918_192_blocked(self) -> None:
        assert _is_blocked_ip("192.168.0.1") is True
        assert _is_blocked_ip("192.168.1.100") is True

    def test_loopback_blocked(self) -> None:
        assert _is_blocked_ip("127.0.0.1") is True
        assert _is_blocked_ip("127.0.0.2") is True

    def test_link_local_blocked(self) -> None:
        assert _is_blocked_ip("169.254.0.1") is True
        assert _is_blocked_ip("169.254.169.254") is True

    def test_ipv6_loopback_blocked(self) -> None:
        assert _is_blocked_ip("::1") is True

    def test_ipv4_mapped_ipv6_link_local_blocked(self) -> None:
        # ::ffff:169.254.169.254 — AWS metadata endpoint in IPv4-mapped form
        assert _is_blocked_ip("::ffff:169.254.169.254") is True

    def test_ipv4_mapped_ipv6_loopback_blocked(self) -> None:
        assert _is_blocked_ip("::ffff:127.0.0.1") is True

    def test_ipv4_mapped_ipv6_rfc1918_blocked(self) -> None:
        assert _is_blocked_ip("::ffff:192.168.1.1") is True

    def test_ipv4_mapped_ipv6_public_allowed(self) -> None:
        assert _is_blocked_ip("::ffff:1.2.3.4") is False

    def test_unparseable_address_blocked(self) -> None:
        assert _is_blocked_ip("not-an-ip") is True

    def test_multicast_blocked(self) -> None:
        assert _is_blocked_ip("224.0.0.1") is True
        assert _is_blocked_ip("239.255.255.255") is True


class TestValidateUrlSsrf:
    def test_public_ip_passes(self) -> None:
        resolver = FakeResolver(["1.2.3.4"])
        _validate_url_ssrf("https://example.com", resolver)  # should not raise

    def test_private_ip_raises(self) -> None:
        resolver = FakeResolver(["10.0.0.1"])
        with pytest.raises(ProviderExecutionError, match="SSRF protection"):
            _validate_url_ssrf("https://internal.corp", resolver)

    def test_loopback_raises(self) -> None:
        resolver = FakeResolver(["127.0.0.1"])
        with pytest.raises(ProviderExecutionError, match="SSRF protection"):
            _validate_url_ssrf("https://localhost", resolver)

    def test_unresolvable_host_raises(self) -> None:
        resolver = FakeResolver([])
        with pytest.raises(ProviderExecutionError, match="could not resolve"):
            _validate_url_ssrf("https://unresolvable.invalid", resolver)

    def test_multiple_addresses_one_blocked_raises(self) -> None:
        resolver = FakeResolver(["1.2.3.4", "10.0.0.1"])
        with pytest.raises(ProviderExecutionError, match="SSRF protection"):
            _validate_url_ssrf("https://dual-stack.example.com", resolver)

    def test_all_public_multiple_addresses_passes(self) -> None:
        resolver = FakeResolver(["1.2.3.4", "5.6.7.8"])
        _validate_url_ssrf("https://cdn.example.com", resolver)  # should not raise

    def test_missing_hostname_raises(self) -> None:
        resolver = FakeResolver(["1.2.3.4"])
        with pytest.raises(ProviderExecutionError, match="could not parse hostname"):
            _validate_url_ssrf("https://", resolver)


class TestFetcherSsrfIntegration:
    def test_private_ip_rejected_before_network(self) -> None:
        resolver = FakeResolver(["192.168.1.1"])
        fetcher = RequestsFetcher(resolver=resolver)
        with pytest.raises(ProviderExecutionError, match="SSRF protection"):
            fetcher.fetch("https://internal.corp", timeout_seconds=5.0)

    def test_public_ip_allowed(self) -> None:
        from unittest.mock import MagicMock, patch

        resolver = FakeResolver(["1.2.3.4"])
        fetcher = RequestsFetcher(resolver=resolver)

        mock_session_cls = MagicMock()
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://example.com"
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_resp.encoding = "utf-8"
        mock_resp.iter_content = MagicMock(return_value=iter([b"content"]))
        mock_resp.close = MagicMock()
        mock_session.get.return_value = mock_resp

        mock_req = MagicMock()
        mock_req.Session = mock_session_cls

        with patch.object(fetcher, "_import_requests", return_value=mock_req):
            result = fetcher.fetch("https://example.com", timeout_seconds=5.0)
        assert result.status_code == 200

    def test_redirect_to_private_ip_rejected(self) -> None:
        from unittest.mock import MagicMock, patch

        call_count = 0

        class SequentialResolver:
            def resolve(self, hostname: str, port: int) -> list[str]:
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return ["1.2.3.4"]  # initial URL resolves to public IP
                return ["10.0.0.1"]  # redirect target resolves to private IP

        fetcher = RequestsFetcher(resolver=SequentialResolver())

        mock_session_cls = MagicMock()
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        # First call returns a 302 redirect
        redirect_resp = MagicMock()
        redirect_resp.status_code = 302
        redirect_resp.headers = {"Location": "https://internal.corp/page"}
        redirect_resp.url = "https://example.com"

        mock_session.get.return_value = redirect_resp

        mock_req = MagicMock()
        mock_req.Session = mock_session_cls

        with (
            patch.object(fetcher, "_import_requests", return_value=mock_req),
            pytest.raises(ProviderExecutionError, match="SSRF protection"),
        ):
            fetcher.fetch("https://example.com", timeout_seconds=5.0)


class TestDefaultHostResolver:
    def test_returns_list(self) -> None:
        resolver = DefaultHostResolver()
        result = resolver.resolve("localhost", 80)
        assert isinstance(result, list)

    def test_unresolvable_returns_empty(self) -> None:
        resolver = DefaultHostResolver()
        result = resolver.resolve("this.host.does.not.exist.invalid", 80)
        assert result == []
