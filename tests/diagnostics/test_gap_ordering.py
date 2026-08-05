"""
Tests for gap ordering: severity DESC, then type/status/ids/id ASC.
"""

from __future__ import annotations

import pytest

from research_core.analysis.analyzer import _gap_sort_key
from research_core.contracts.common import EMPTY_METADATA
from research_core.contracts.gaps import GapSeverity, GapStatus, GapType, ResearchGap


def _make_gap(
    gap_type: GapType = GapType.NO_EVIDENCE,
    severity: GapSeverity = GapSeverity.MEDIUM,
    gap_id: str = "gap-test",
) -> ResearchGap:
    return ResearchGap(
        gap_id=gap_id,
        gap_type=gap_type,
        description="test gap",
        severity=severity,
        status=GapStatus.OPEN,
        metadata=EMPTY_METADATA,
    )


@pytest.mark.diagnostics
class TestGapSortKey:
    def test_critical_sorts_before_high(self) -> None:
        critical = _make_gap(severity=GapSeverity.CRITICAL, gap_id="gap-c")
        high = _make_gap(severity=GapSeverity.HIGH, gap_id="gap-h")
        assert _gap_sort_key(critical) < _gap_sort_key(high)

    def test_high_sorts_before_medium(self) -> None:
        high = _make_gap(severity=GapSeverity.HIGH, gap_id="gap-h")
        medium = _make_gap(severity=GapSeverity.MEDIUM, gap_id="gap-m")
        assert _gap_sort_key(high) < _gap_sort_key(medium)

    def test_medium_sorts_before_low(self) -> None:
        medium = _make_gap(severity=GapSeverity.MEDIUM, gap_id="gap-m")
        low = _make_gap(severity=GapSeverity.LOW, gap_id="gap-l")
        assert _gap_sort_key(medium) < _gap_sort_key(low)

    def test_same_severity_sorted_by_gap_type(self) -> None:
        a = _make_gap(
            severity=GapSeverity.MEDIUM,
            gap_type=GapType.INSUFFICIENT_COVERAGE,
            gap_id="gap-a",
        )
        b = _make_gap(
            severity=GapSeverity.MEDIUM,
            gap_type=GapType.STALE_EVIDENCE,
            gap_id="gap-b",
        )
        # Alphabetical: "insufficient_coverage" < "stale_evidence"
        assert _gap_sort_key(a) < _gap_sort_key(b)

    def test_same_severity_and_type_sorted_by_id(self) -> None:
        a = _make_gap(severity=GapSeverity.LOW, gap_type=GapType.NO_EVIDENCE, gap_id="gap-aaa")
        b = _make_gap(severity=GapSeverity.LOW, gap_type=GapType.NO_EVIDENCE, gap_id="gap-bbb")
        assert _gap_sort_key(a) < _gap_sort_key(b)


@pytest.mark.diagnostics
class TestGapOrderingInResult:
    def test_sorted_result_is_stable(self) -> None:
        from research_core.analysis.analyzer import DeterministicGapAnalyzer
        from research_core.analysis.config import GapAnalysisConfig

        analyzer = DeterministicGapAnalyzer()
        cfg = GapAnalysisConfig()
        result = analyzer.analyze([], [], [], None, cfg)
        gaps = result.gaps
        if len(gaps) > 1:
            for i in range(len(gaps) - 1):
                assert _gap_sort_key(gaps[i]) <= _gap_sort_key(gaps[i + 1])

    def test_all_critical_before_non_critical(self) -> None:
        from research_core.analysis.analyzer import DeterministicGapAnalyzer
        from research_core.analysis.config import GapAnalysisConfig

        analyzer = DeterministicGapAnalyzer()
        cfg = GapAnalysisConfig()
        # Empty input triggers both CRITICAL gaps
        result = analyzer.analyze([], [], [], None, cfg)
        gaps = result.gaps
        seen_non_critical = False
        for g in gaps:
            if g.severity != GapSeverity.CRITICAL:
                seen_non_critical = True
            if seen_non_critical:
                assert g.severity != GapSeverity.CRITICAL
