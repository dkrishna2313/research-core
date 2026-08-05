"""
Regression tests for gap-ID collision prevention (RC6).

Prior to the fix, _make_gap_id() did not include the condition name in the
SHA-256 payload. Two distinct conditions (e.g. no_sources / no_evidence) that
produced a gap with identical structural parameters generated the same gap_id,
causing the deduplication pass in DeterministicGapAnalyzer to collapse them.

These tests confirm that:
  1. Distinct conditions produce distinct gap IDs on empty input.
  2. Diagnostics correctly reflect both emitted gaps.
  3. Condition identity alone is sufficient to differentiate IDs.
  4. Existing determinism (same inputs → same ID, order-invariant) is preserved.
  5. Each meaningful input field is load-bearing in the ID.
"""

from __future__ import annotations

import pytest

from research_core.analysis.analyzer import DeterministicGapAnalyzer
from research_core.analysis.conditions import _make_gap_id
from research_core.analysis.config import GapAnalysisConfig
from research_core.analysis.contracts import DiagnosticStatus
from research_core.contracts.gaps import GapSeverity, GapType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gap_id(
    condition_name: str,
    *,
    gap_type: GapType = GapType.NO_EVIDENCE,
    severity: GapSeverity = GapSeverity.CRITICAL,
    status: DiagnosticStatus = DiagnosticStatus.FAIL,
    observed_value: float | None = 0.0,
    threshold_value: float | None = 0.0,
    affected_source_ids: tuple[str, ...] = (),
    affected_evidence_ids: tuple[str, ...] = (),
    affected_claim_ids: tuple[str, ...] = (),
    analyzer_version: str = "0.6.0",
    config_fingerprint: str = "abc123",
) -> str:
    return _make_gap_id(
        condition_name=condition_name,
        gap_type=gap_type,
        severity=severity,
        status=status,
        observed_value=observed_value,
        threshold_value=threshold_value,
        affected_source_ids=affected_source_ids,
        affected_evidence_ids=affected_evidence_ids,
        affected_claim_ids=affected_claim_ids,
        analyzer_version=analyzer_version,
        config_fingerprint=config_fingerprint,
    )


# ---------------------------------------------------------------------------
# 1. Zero-threshold empty input: no_sources vs no_evidence → distinct IDs
# ---------------------------------------------------------------------------

@pytest.mark.diagnostics
class TestZeroThresholdDistinctGaps:
    def test_no_sources_and_no_evidence_produce_distinct_gap_ids(self) -> None:
        cfg = GapAnalysisConfig(minimum_source_count=0, minimum_evidence_count=0)
        analyzer = DeterministicGapAnalyzer()
        result = analyzer.analyze(
            sources=[],
            ranked_evidence=[],
            claims=[],
            ranking_result=None,
            config=cfg,
        )
        gap_ids = [g.gap_id for g in result.gaps]
        no_src_gap = next((g for g in result.gaps if g.condition == "no_sources"), None)
        no_ev_gap = next((g for g in result.gaps if g.condition == "no_evidence"), None)
        assert no_src_gap is not None, "no_sources gap must be present"
        assert no_ev_gap is not None, "no_evidence gap must be present"
        assert no_src_gap.gap_id != no_ev_gap.gap_id, (
            "no_sources and no_evidence must produce distinct gap IDs"
        )
        assert len(set(gap_ids)) == len(gap_ids), "all gap_ids must be unique"

    def test_both_gaps_present_in_result(self) -> None:
        cfg = GapAnalysisConfig(minimum_source_count=0, minimum_evidence_count=0)
        analyzer = DeterministicGapAnalyzer()
        result = analyzer.analyze(
            sources=[],
            ranked_evidence=[],
            claims=[],
            ranking_result=None,
            config=cfg,
        )
        conditions = {g.condition for g in result.gaps}
        assert "no_sources" in conditions
        assert "no_evidence" in conditions

    def test_neither_gap_is_silently_collapsed(self) -> None:
        cfg = GapAnalysisConfig(minimum_source_count=0, minimum_evidence_count=0)
        analyzer = DeterministicGapAnalyzer()
        result = analyzer.analyze(
            sources=[],
            ranked_evidence=[],
            claims=[],
            ranking_result=None,
            config=cfg,
        )
        no_ev_gaps = [g for g in result.gaps if g.condition == "no_evidence"]
        no_src_gaps = [g for g in result.gaps if g.condition == "no_sources"]
        assert len(no_ev_gaps) == 1
        assert len(no_src_gaps) == 1


# ---------------------------------------------------------------------------
# 2. Diagnostics reconcile for two-failed-condition scenario
# ---------------------------------------------------------------------------

@pytest.mark.diagnostics
class TestDiagnosticsReconcile:
    def test_conditions_failed_includes_both(self) -> None:
        cfg = GapAnalysisConfig(minimum_source_count=0, minimum_evidence_count=0)
        analyzer = DeterministicGapAnalyzer()
        result = analyzer.analyze(
            sources=[],
            ranked_evidence=[],
            claims=[],
            ranking_result=None,
            config=cfg,
        )
        diag = result.gap_analysis_diagnostics
        assert diag.conditions_failed >= 2

    def test_gaps_emitted_matches_unique_gaps(self) -> None:
        cfg = GapAnalysisConfig(minimum_source_count=0, minimum_evidence_count=0)
        analyzer = DeterministicGapAnalyzer()
        result = analyzer.analyze(
            sources=[],
            ranked_evidence=[],
            claims=[],
            ranking_result=None,
            config=cfg,
        )
        diag = result.gap_analysis_diagnostics
        assert diag.gaps_emitted == len(result.gaps)

    def test_gaps_by_category_includes_no_evidence(self) -> None:
        cfg = GapAnalysisConfig(minimum_source_count=0, minimum_evidence_count=0)
        analyzer = DeterministicGapAnalyzer()
        result = analyzer.analyze(
            sources=[],
            ranked_evidence=[],
            claims=[],
            ranking_result=None,
            config=cfg,
        )
        diag = result.gap_analysis_diagnostics
        assert str(GapType.NO_EVIDENCE) in diag.gaps_by_category

    def test_gaps_by_severity_includes_critical(self) -> None:
        cfg = GapAnalysisConfig(minimum_source_count=0, minimum_evidence_count=0)
        analyzer = DeterministicGapAnalyzer()
        result = analyzer.analyze(
            sources=[],
            ranked_evidence=[],
            claims=[],
            ranking_result=None,
            config=cfg,
        )
        diag = result.gap_analysis_diagnostics
        assert str(GapSeverity.CRITICAL) in diag.gaps_by_severity
        assert diag.gaps_by_severity[str(GapSeverity.CRITICAL)] >= 2


# ---------------------------------------------------------------------------
# 3. Condition identity alone distinguishes IDs
# ---------------------------------------------------------------------------

@pytest.mark.diagnostics
class TestConditionIdentityDistinguishesIds:
    def test_same_params_different_condition_gives_different_id(self) -> None:
        id_a = _gap_id("no_sources")
        id_b = _gap_id("no_evidence")
        assert id_a != id_b

    def test_three_distinct_conditions_all_distinct(self) -> None:
        id_a = _gap_id("cond_a")
        id_b = _gap_id("cond_b")
        id_c = _gap_id("cond_c")
        assert len({id_a, id_b, id_c}) == 3

    def test_gap_object_condition_field_populated(self) -> None:
        cfg = GapAnalysisConfig(minimum_source_count=0, minimum_evidence_count=0)
        analyzer = DeterministicGapAnalyzer()
        result = analyzer.analyze(
            sources=[],
            ranked_evidence=[],
            claims=[],
            ranking_result=None,
            config=cfg,
        )
        for gap in result.gaps:
            assert gap.condition != "", f"gap {gap.gap_id} must have non-empty condition"


# ---------------------------------------------------------------------------
# 4. Existing determinism preserved
# ---------------------------------------------------------------------------

@pytest.mark.diagnostics
class TestDeterminism:
    def test_identical_inputs_produce_identical_id(self) -> None:
        id_a = _gap_id("no_sources", gap_type=GapType.NO_EVIDENCE, observed_value=0.0)
        id_b = _gap_id("no_sources", gap_type=GapType.NO_EVIDENCE, observed_value=0.0)
        assert id_a == id_b

    def test_affected_ids_order_does_not_change_id(self) -> None:
        id_a = _gap_id("cond_x", affected_evidence_ids=("ev-1", "ev-2", "ev-3"))
        id_b = _gap_id("cond_x", affected_evidence_ids=("ev-3", "ev-1", "ev-2"))
        assert id_a == id_b, "affected_evidence_ids are sorted before hashing"

    def test_affected_source_ids_order_does_not_change_id(self) -> None:
        id_a = _gap_id("cond_x", affected_source_ids=("src-a", "src-b"))
        id_b = _gap_id("cond_x", affected_source_ids=("src-b", "src-a"))
        assert id_a == id_b

    def test_id_starts_with_gap_prefix(self) -> None:
        gid = _gap_id("no_sources")
        assert gid.startswith("gap-")
        assert len(gid) == 4 + 20

    def test_id_is_hex_string(self) -> None:
        gid = _gap_id("no_sources")
        hex_part = gid[4:]
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_analyzer_run_is_deterministic(self) -> None:
        cfg = GapAnalysisConfig(minimum_source_count=0, minimum_evidence_count=0)
        analyzer = DeterministicGapAnalyzer()
        result_a = analyzer.analyze(
            sources=[], ranked_evidence=[], claims=[], ranking_result=None, config=cfg
        )
        result_b = analyzer.analyze(
            sources=[], ranked_evidence=[], claims=[], ranking_result=None, config=cfg
        )
        ids_a = {g.gap_id for g in result_a.gaps}
        ids_b = {g.gap_id for g in result_b.gaps}
        assert ids_a == ids_b


# ---------------------------------------------------------------------------
# 5. Each field is load-bearing in the ID
# ---------------------------------------------------------------------------

@pytest.mark.diagnostics
class TestIdSensitivity:
    def _base(self) -> str:
        return _gap_id(
            "no_sources",
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.CRITICAL,
            status=DiagnosticStatus.FAIL,
            observed_value=0.0,
            threshold_value=0.0,
            affected_source_ids=(),
            affected_evidence_ids=(),
            affected_claim_ids=(),
            analyzer_version="0.6.0",
            config_fingerprint="fp-abc",
        )

    def test_condition_name_change_alters_id(self) -> None:
        base = self._base()
        changed = _gap_id(
            "no_evidence",
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.CRITICAL,
            status=DiagnosticStatus.FAIL,
            observed_value=0.0,
            threshold_value=0.0,
            analyzer_version="0.6.0",
            config_fingerprint="fp-abc",
        )
        assert base != changed

    def test_gap_type_change_alters_id(self) -> None:
        base = self._base()
        changed = _gap_id(
            "no_sources",
            gap_type=GapType.INSUFFICIENT_COVERAGE,
            severity=GapSeverity.CRITICAL,
            status=DiagnosticStatus.FAIL,
            observed_value=0.0,
            threshold_value=0.0,
            analyzer_version="0.6.0",
            config_fingerprint="fp-abc",
        )
        assert base != changed

    def test_severity_change_alters_id(self) -> None:
        base = self._base()
        changed = _gap_id(
            "no_sources",
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.HIGH,
            status=DiagnosticStatus.FAIL,
            observed_value=0.0,
            threshold_value=0.0,
            analyzer_version="0.6.0",
            config_fingerprint="fp-abc",
        )
        assert base != changed

    def test_status_change_alters_id(self) -> None:
        base = self._base()
        changed = _gap_id(
            "no_sources",
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.CRITICAL,
            status=DiagnosticStatus.INDETERMINATE,
            observed_value=0.0,
            threshold_value=0.0,
            analyzer_version="0.6.0",
            config_fingerprint="fp-abc",
        )
        assert base != changed

    def test_observed_value_change_alters_id(self) -> None:
        base = self._base()
        changed = _gap_id(
            "no_sources",
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.CRITICAL,
            status=DiagnosticStatus.FAIL,
            observed_value=1.0,
            threshold_value=0.0,
            analyzer_version="0.6.0",
            config_fingerprint="fp-abc",
        )
        assert base != changed

    def test_threshold_change_alters_id(self) -> None:
        base = self._base()
        changed = _gap_id(
            "no_sources",
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.CRITICAL,
            status=DiagnosticStatus.FAIL,
            observed_value=0.0,
            threshold_value=5.0,
            analyzer_version="0.6.0",
            config_fingerprint="fp-abc",
        )
        assert base != changed

    def test_affected_evidence_ids_change_alters_id(self) -> None:
        base = self._base()
        changed = _gap_id(
            "no_sources",
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.CRITICAL,
            status=DiagnosticStatus.FAIL,
            observed_value=0.0,
            threshold_value=0.0,
            affected_evidence_ids=("ev-1",),
            analyzer_version="0.6.0",
            config_fingerprint="fp-abc",
        )
        assert base != changed

    def test_affected_source_ids_change_alters_id(self) -> None:
        base = self._base()
        changed = _gap_id(
            "no_sources",
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.CRITICAL,
            status=DiagnosticStatus.FAIL,
            observed_value=0.0,
            threshold_value=0.0,
            affected_source_ids=("src-1",),
            analyzer_version="0.6.0",
            config_fingerprint="fp-abc",
        )
        assert base != changed

    def test_affected_claim_ids_change_alters_id(self) -> None:
        base = self._base()
        changed = _gap_id(
            "no_sources",
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.CRITICAL,
            status=DiagnosticStatus.FAIL,
            observed_value=0.0,
            threshold_value=0.0,
            affected_claim_ids=("clm-1",),
            analyzer_version="0.6.0",
            config_fingerprint="fp-abc",
        )
        assert base != changed

    def test_analyzer_version_change_alters_id(self) -> None:
        base = self._base()
        changed = _gap_id(
            "no_sources",
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.CRITICAL,
            status=DiagnosticStatus.FAIL,
            observed_value=0.0,
            threshold_value=0.0,
            analyzer_version="0.7.0",
            config_fingerprint="fp-abc",
        )
        assert base != changed

    def test_config_fingerprint_change_alters_id(self) -> None:
        base = self._base()
        changed = _gap_id(
            "no_sources",
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.CRITICAL,
            status=DiagnosticStatus.FAIL,
            observed_value=0.0,
            threshold_value=0.0,
            analyzer_version="0.6.0",
            config_fingerprint="fp-xyz",
        )
        assert base != changed
