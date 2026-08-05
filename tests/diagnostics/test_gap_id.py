"""
Tests for gap ID determinism and format.
"""

from __future__ import annotations

import pytest

from research_core.analysis.analyzer import DeterministicGapAnalyzer
from research_core.analysis.conditions import _make_gap_id
from research_core.analysis.config import GapAnalysisConfig
from research_core.analysis.contracts import DiagnosticStatus
from research_core.contracts.gaps import GapSeverity, GapType


@pytest.mark.diagnostics
class TestMakeGapId:
    def test_id_starts_with_gap_prefix(self) -> None:
        gap_id = _make_gap_id(
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.CRITICAL,
            status=DiagnosticStatus.FAIL,
            observed_value=0.0,
            threshold_value=2.0,
            affected_source_ids=(),
            affected_evidence_ids=(),
            affected_claim_ids=(),
            analyzer_version="1",
            config_fingerprint="abc",
        )
        assert gap_id.startswith("gap-")

    def test_id_length(self) -> None:
        gap_id = _make_gap_id(
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.CRITICAL,
            status=DiagnosticStatus.FAIL,
            observed_value=0.0,
            threshold_value=2.0,
            affected_source_ids=(),
            affected_evidence_ids=(),
            affected_claim_ids=(),
            analyzer_version="1",
            config_fingerprint="abc",
        )
        # "gap-" + 20 hex chars
        assert len(gap_id) == 24

    def test_same_inputs_same_id(self) -> None:
        kwargs = dict(
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.CRITICAL,
            status=DiagnosticStatus.FAIL,
            observed_value=0.0,
            threshold_value=2.0,
            affected_source_ids=("src-1",),
            affected_evidence_ids=("ev-1",),
            affected_claim_ids=(),
            analyzer_version="1",
            config_fingerprint="test-fp",
        )
        id1 = _make_gap_id(**kwargs)
        id2 = _make_gap_id(**kwargs)
        assert id1 == id2

    def test_different_types_different_ids(self) -> None:
        common = dict(
            severity=GapSeverity.HIGH,
            status=DiagnosticStatus.FAIL,
            observed_value=0.5,
            threshold_value=1.0,
            affected_source_ids=(),
            affected_evidence_ids=(),
            affected_claim_ids=(),
            analyzer_version="1",
            config_fingerprint="fp",
        )
        id1 = _make_gap_id(gap_type=GapType.NO_EVIDENCE, **common)
        id2 = _make_gap_id(gap_type=GapType.INSUFFICIENT_COVERAGE, **common)
        assert id1 != id2

    def test_different_evidence_ids_different_gap_ids(self) -> None:
        common = dict(
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.CRITICAL,
            status=DiagnosticStatus.FAIL,
            observed_value=0.0,
            threshold_value=2.0,
            affected_source_ids=(),
            affected_claim_ids=(),
            analyzer_version="1",
            config_fingerprint="fp",
        )
        id1 = _make_gap_id(affected_evidence_ids=("ev-1",), **common)
        id2 = _make_gap_id(affected_evidence_ids=("ev-2",), **common)
        assert id1 != id2

    def test_affected_ids_sorted_consistently(self) -> None:
        common = dict(
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.CRITICAL,
            status=DiagnosticStatus.FAIL,
            observed_value=0.0,
            threshold_value=2.0,
            affected_source_ids=(),
            affected_claim_ids=(),
            analyzer_version="1",
            config_fingerprint="fp",
        )
        id1 = _make_gap_id(affected_evidence_ids=("ev-a", "ev-b"), **common)
        id2 = _make_gap_id(affected_evidence_ids=("ev-b", "ev-a"), **common)
        # Sorted before hashing → same ID regardless of input order
        assert id1 == id2


@pytest.mark.diagnostics
class TestGapIdStabilityAcrossAnalyzer:
    def test_repeated_analysis_stable_ids(self) -> None:
        analyzer = DeterministicGapAnalyzer()
        cfg = GapAnalysisConfig()
        r1 = analyzer.analyze([], [], [], None, cfg)
        r2 = analyzer.analyze([], [], [], None, cfg)
        assert [g.gap_id for g in r1.gaps] == [g.gap_id for g in r2.gaps]

    def test_config_change_changes_gap_ids(self) -> None:
        analyzer = DeterministicGapAnalyzer()
        cfg1 = GapAnalysisConfig(analyzer_version="1")
        cfg2 = GapAnalysisConfig(analyzer_version="2")
        r1 = analyzer.analyze([], [], [], None, cfg1)
        r2 = analyzer.analyze([], [], [], None, cfg2)
        # Different config fingerprints → different gap IDs
        ids1 = {g.gap_id for g in r1.gaps}
        ids2 = {g.gap_id for g in r2.gaps}
        assert ids1 != ids2
