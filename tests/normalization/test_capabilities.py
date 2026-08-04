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
