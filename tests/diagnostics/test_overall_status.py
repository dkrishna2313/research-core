"""
Tests for compute_overall_status() — quality diagnostic status rules.
"""

from __future__ import annotations

import pytest

from research_core.analysis.contracts import DiagnosticStatus
from research_core.analysis.quality import compute_overall_status
from research_core.contracts.common import EMPTY_METADATA
from research_core.contracts.gaps import GapSeverity, GapStatus, GapType, ResearchGap


def _make_gap(severity: GapSeverity = GapSeverity.MEDIUM) -> ResearchGap:
    return ResearchGap(
        gap_id="gap-test",
        gap_type=GapType.NO_EVIDENCE,
        description="test",
        severity=severity,
        status=GapStatus.OPEN,
        metadata=EMPTY_METADATA,
    )


@pytest.mark.diagnostics
class TestComputeOverallStatus:
    def test_no_evidence_is_fail(self) -> None:
        assert compute_overall_status(0.8, [], 0) == DiagnosticStatus.FAIL

    def test_critical_gap_is_fail(self) -> None:
        result = compute_overall_status(0.8, [_make_gap(GapSeverity.CRITICAL)], 1)
        assert result == DiagnosticStatus.FAIL

    def test_no_score_no_gaps_is_indeterminate(self) -> None:
        assert compute_overall_status(None, [], 1) == DiagnosticStatus.INDETERMINATE

    def test_non_critical_gaps_present_is_indeterminate(self) -> None:
        result = compute_overall_status(0.8, [_make_gap(GapSeverity.HIGH)], 1)
        assert result == DiagnosticStatus.INDETERMINATE

    def test_medium_gap_is_indeterminate(self) -> None:
        result = compute_overall_status(0.9, [_make_gap(GapSeverity.MEDIUM)], 1)
        assert result == DiagnosticStatus.INDETERMINATE

    def test_no_gaps_with_score_is_pass(self) -> None:
        assert compute_overall_status(0.8, [], 3) == DiagnosticStatus.PASS

    def test_critical_gap_beats_evidence_present(self) -> None:
        result = compute_overall_status(0.9, [_make_gap(GapSeverity.CRITICAL)], 5)
        assert result == DiagnosticStatus.FAIL

    def test_low_severity_gap_is_indeterminate_not_fail(self) -> None:
        result = compute_overall_status(0.9, [_make_gap(GapSeverity.LOW)], 3)
        assert result == DiagnosticStatus.INDETERMINATE
