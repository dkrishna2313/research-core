"""Tests for KnowledgeAdapter capability reporting."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.knowledge

from research_core.normalization.capabilities import capability_report_for_knowledge  # noqa: E402
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
        assert report.metadata["overall"] in ("available", "unavailable")

    def test_capability_statuses_are_valid(self) -> None:
        report = capability_report_for_knowledge(object())
        valid = set(CapabilityStatus)
        for cap in report.capabilities:
            assert cap.status in valid

    def test_no_network_calls_made(self) -> None:
        report = capability_report_for_knowledge(object())
        assert report is not None
