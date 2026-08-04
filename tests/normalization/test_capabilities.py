"""Tests for adapter capability reporting."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.normalization

from research_core.normalization.capabilities import (  # noqa: E402
    capability_report_for_knowledge,
    capability_report_for_web,
)
from research_core.normalization.contracts import CapabilityReport, CapabilityStatus  # noqa: E402


class TestKnowledgeCapabilityReport:
    def test_returns_capability_report(self) -> None:
        report = capability_report_for_knowledge(object())
        assert isinstance(report, CapabilityReport)

    def test_checked_at_in_metadata(self) -> None:
        from datetime import datetime

        report = capability_report_for_knowledge(object())
        assert "checked_at" in report.metadata
        ts = report.metadata["checked_at"]
        parsed = datetime.fromisoformat(str(ts))
        assert parsed.tzinfo is not None

    def test_adapter_name_is_knowledge_adapter(self) -> None:
        report = capability_report_for_knowledge(object())
        assert report.adapter_name == "KnowledgeAdapter"

    def test_has_knowledge_store_capability(self) -> None:
        report = capability_report_for_knowledge(object())
        names = {c.name for c in report.capabilities}
        assert "knowledge_store" in names

    def test_overall_in_metadata(self) -> None:
        report = capability_report_for_knowledge(object())
        assert "overall" in report.metadata

    def test_overall_is_valid_value(self) -> None:
        report = capability_report_for_knowledge(object())
        assert report.metadata["overall"] in ("available", "unavailable", "degraded", "unknown")

    def test_capability_status_values_are_valid(self) -> None:
        report = capability_report_for_knowledge(object())
        valid = set(CapabilityStatus)
        for cap in report.capabilities:
            assert cap.status in valid


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

    def test_has_pdf_extractor_capability(self) -> None:
        report = capability_report_for_web(object())
        names = {c.name for c in report.capabilities}
        assert "pdf_extractor" in names

    def test_has_docx_extractor_capability(self) -> None:
        report = capability_report_for_web(object())
        names = {c.name for c in report.capabilities}
        assert "docx_extractor" in names

    def test_overall_in_metadata(self) -> None:
        report = capability_report_for_web(object())
        assert "overall" in report.metadata

    def test_capability_status_values_are_valid(self) -> None:
        report = capability_report_for_web(object())
        valid = set(CapabilityStatus)
        for cap in report.capabilities:
            assert cap.status in valid

    def test_checked_at_in_metadata(self) -> None:
        from datetime import datetime

        report = capability_report_for_web(object())
        assert "checked_at" in report.metadata
        ts = report.metadata["checked_at"]
        parsed = datetime.fromisoformat(str(ts))
        assert parsed.tzinfo is not None

    def test_search_available_with_ddgs(self) -> None:
        # With ddgs installed, search capability should be available
        import importlib.util
        has_ddgs = importlib.util.find_spec("ddgs") is not None
        has_ddgspy = importlib.util.find_spec("duckduckgo_search") is not None
        report = capability_report_for_web(object())
        search_cap = next(c for c in report.capabilities if c.name == "search_provider")
        if has_ddgs or has_ddgspy:
            assert search_cap.status == CapabilityStatus.AVAILABLE
        else:
            assert search_cap.status == CapabilityStatus.UNAVAILABLE
