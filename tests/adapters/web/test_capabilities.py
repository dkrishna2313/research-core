"""Tests for WebSearchAdapter capability reporting."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.web

from research_core.normalization.capabilities import capability_report_for_web  # noqa: E402
from research_core.normalization.contracts import CapabilityReport, CapabilityStatus  # noqa: E402


class TestWebCapabilityReport:
    def test_returns_capability_report(self) -> None:
        report = capability_report_for_web(object())
        assert isinstance(report, CapabilityReport)

    def test_adapter_name_is_web_search_adapter(self) -> None:
        report = capability_report_for_web(object())
        assert report.adapter_name == "WebSearchAdapter"

    def test_has_search_provider_capability(self) -> None:
        report = capability_report_for_web(object())
        names = {c.name for c in report.capabilities}
        assert "search_provider" in names

    def test_has_page_fetcher_capability(self) -> None:
        report = capability_report_for_web(object())
        names = {c.name for c in report.capabilities}
        assert "page_fetcher" in names

    def test_has_html_extractor_capability(self) -> None:
        report = capability_report_for_web(object())
        names = {c.name for c in report.capabilities}
        assert "html_extractor" in names

    def test_overall_is_string(self) -> None:
        report = capability_report_for_web(object())
        assert isinstance(report.metadata.get("overall"), str)

    def test_capability_statuses_are_valid(self) -> None:
        report = capability_report_for_web(object())
        valid = set(CapabilityStatus)
        for cap in report.capabilities:
            assert cap.status in valid

    def test_no_network_calls_made(self) -> None:
        # Calling with a bare object should not raise network errors
        report = capability_report_for_web(object())
        assert report is not None

    def test_has_plain_text_extraction_capability(self) -> None:
        report = capability_report_for_web()
        names = {c.name for c in report.capabilities}
        assert "plain_text_extraction" in names

    def test_plain_text_extraction_always_available(self) -> None:
        report = capability_report_for_web()
        cap = next(c for c in report.capabilities if c.name == "plain_text_extraction")
        assert cap.status == CapabilityStatus.AVAILABLE

    def test_has_cache_capability(self) -> None:
        report = capability_report_for_web()
        names = {c.name for c in report.capabilities}
        assert "cache" in names

    def test_cache_unknown_when_not_specified(self) -> None:
        report = capability_report_for_web()
        cap = next(c for c in report.capabilities if c.name == "cache")
        assert cap.status == CapabilityStatus.UNKNOWN

    def test_cache_available_when_enabled(self) -> None:
        report = capability_report_for_web(cache_enabled=True)
        cap = next(c for c in report.capabilities if c.name == "cache")
        assert cap.status == CapabilityStatus.AVAILABLE

    def test_cache_degraded_when_disabled(self) -> None:
        report = capability_report_for_web(cache_enabled=False)
        cap = next(c for c in report.capabilities if c.name == "cache")
        assert cap.status == CapabilityStatus.DEGRADED
