"""
Tests for RC6 contract type validation and invariants.
"""

from __future__ import annotations

import pytest

from research_core.analysis.contracts import (
    CoverageDiagnostics,
    DiagnosticStatus,
    DistributionDiagnostics,
    EvidenceConditionDiagnostics,
    GapAnalysisDiagnostics,
    GapAnalysisResult,
    QualityDiagnosticsResult,
    QualityDimensionSummary,
)
from research_core.contracts.common import EMPTY_METADATA
from research_core.contracts.result import ResearchStatus
from research_core.exceptions import ContractValidationError

from tests.diagnostics.conftest import make_source


def _make_coverage(**kwargs: object) -> CoverageDiagnostics:
    defaults = dict(
        source_count=1,
        evidence_count=2,
        ranked_evidence_count=2,
        claim_count=1,
        claims_with_evidence=1,
        claims_without_evidence=0,
        evidence_with_claims=1,
        evidence_without_claims=1,
        unique_parent_evidence_count=0,
        segmented_evidence_count=0,
        sources_with_claims=1,
        sources_without_claims=0,
        claim_coverage_ratio=1.0,
        evidence_utilization_ratio=0.5,
    )
    defaults.update(kwargs)
    return CoverageDiagnostics(**defaults)  # type: ignore[arg-type]


def _make_ev_conditions(**kwargs: object) -> EvidenceConditionDiagnostics:
    defaults = dict(
        truncated_evidence_count=0,
        duplicate_evidence_count=0,
        near_duplicate_evidence_count=0,
        missing_retrieval_score_count=0,
        missing_retrieval_rank_count=0,
        invalid_lineage_count=0,
    )
    defaults.update(kwargs)
    return EvidenceConditionDiagnostics(**defaults)  # type: ignore[arg-type]


def _make_distribution(**kwargs: object) -> DistributionDiagnostics:
    defaults = dict(
        unique_source_count=1,
        unique_provider_count=1,
        largest_source_share=1.0,
        largest_provider_share=1.0,
        source_diversity_score=0.0,
        provider_diversity_score=0.0,
        evidence_per_source=EMPTY_METADATA,
        evidence_per_provider=EMPTY_METADATA,
    )
    defaults.update(kwargs)
    return DistributionDiagnostics(**defaults)  # type: ignore[arg-type]


def _make_dim_summary(**kwargs: object) -> QualityDimensionSummary:
    defaults = dict(
        dimension="relevance",
        status=DiagnosticStatus.PASS,
        measured_count=2,
        missing_count=0,
        minimum=0.5,
        maximum=0.9,
        mean=0.7,
        median=0.7,
        threshold=0.3,
        below_threshold_count=0,
        affected_evidence_ids=(),
        metadata=EMPTY_METADATA,
    )
    defaults.update(kwargs)
    return QualityDimensionSummary(**defaults)  # type: ignore[arg-type]


def _make_quality_result(**kwargs: object) -> QualityDiagnosticsResult:
    defaults = dict(
        overall_status=DiagnosticStatus.PASS,
        overall_score=0.7,
        dimensions=(),
        coverage=_make_coverage(),
        distribution=_make_distribution(),
        evidence_conditions=_make_ev_conditions(),
        gap_count=0,
        critical_gap_count=0,
        high_gap_count=0,
        configuration_fingerprint="abc123",
        analyzer="DeterministicGapAnalyzer",
        analyzer_version="1",
        metadata=EMPTY_METADATA,
    )
    defaults.update(kwargs)
    return QualityDiagnosticsResult(**defaults)  # type: ignore[arg-type]


def _make_run_diagnostics(**kwargs: object) -> GapAnalysisDiagnostics:
    defaults = dict(
        input_source_count=1,
        input_evidence_count=2,
        input_ranked_evidence_count=2,
        input_claim_count=1,
        conditions_evaluated=5,
        conditions_passed=4,
        conditions_failed=1,
        conditions_indeterminate=0,
        conditions_unavailable=0,
        gaps_emitted=1,
        gaps_by_category=EMPTY_METADATA,
        gaps_by_severity=EMPTY_METADATA,
        configuration_fingerprint="abc123",
        analyzer="DeterministicGapAnalyzer",
        analyzer_version="1",
        metadata=EMPTY_METADATA,
    )
    defaults.update(kwargs)
    return GapAnalysisDiagnostics(**defaults)  # type: ignore[arg-type]


@pytest.mark.diagnostics
class TestDiagnosticStatus:
    def test_all_members(self) -> None:
        members = {s.value for s in DiagnosticStatus}
        assert "pass" in members
        assert "fail" in members
        assert "indeterminate" in members
        assert "unavailable" in members
        assert "not_applicable" in members


@pytest.mark.diagnostics
class TestQualityDimensionSummary:
    def test_valid_construction(self) -> None:
        dim = _make_dim_summary()
        assert dim.total_count == 2

    def test_negative_measured_count_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            _make_dim_summary(measured_count=-1)

    def test_negative_missing_count_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            _make_dim_summary(missing_count=-1)

    def test_mean_above_one_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            _make_dim_summary(mean=1.5)

    def test_none_statistics_allowed(self) -> None:
        dim = _make_dim_summary(
            measured_count=0,
            minimum=None,
            maximum=None,
            mean=None,
            median=None,
            below_threshold_count=0,
        )
        assert dim.mean is None

    def test_metadata_coerced_to_proxy(self) -> None:
        import types

        dim = _make_dim_summary(metadata={"key": "value"})
        assert isinstance(dim.metadata, types.MappingProxyType)


@pytest.mark.diagnostics
class TestCoverageDiagnostics:
    def test_valid_construction(self) -> None:
        cov = _make_coverage()
        assert cov.source_count == 1

    def test_negative_count_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            _make_coverage(evidence_count=-1)

    def test_ratio_above_one_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            _make_coverage(claim_coverage_ratio=1.5)

    def test_none_ratio_allowed(self) -> None:
        cov = _make_coverage(claim_coverage_ratio=None, evidence_utilization_ratio=None)
        assert cov.claim_coverage_ratio is None


@pytest.mark.diagnostics
class TestDistributionDiagnostics:
    def test_valid_construction(self) -> None:
        dist = _make_distribution()
        assert dist.unique_source_count == 1

    def test_share_above_one_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            _make_distribution(largest_source_share=1.5)

    def test_none_shares_allowed(self) -> None:
        dist = _make_distribution(
            largest_source_share=None, largest_provider_share=None,
            source_diversity_score=None, provider_diversity_score=None,
        )
        assert dist.largest_source_share is None

    def test_evidence_per_source_coerced_to_proxy(self) -> None:
        import types

        dist = _make_distribution(evidence_per_source={"src-1": 2})
        assert isinstance(dist.evidence_per_source, types.MappingProxyType)


@pytest.mark.diagnostics
class TestEvidenceConditionDiagnostics:
    def test_valid_construction(self) -> None:
        ev = _make_ev_conditions()
        assert ev.duplicate_evidence_count == 0

    def test_negative_count_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            _make_ev_conditions(truncated_evidence_count=-1)


@pytest.mark.diagnostics
class TestQualityDiagnosticsResult:
    def test_valid_construction(self) -> None:
        qr = _make_quality_result()
        assert qr.overall_status == DiagnosticStatus.PASS

    def test_score_above_one_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            _make_quality_result(overall_score=1.1)

    def test_none_score_allowed(self) -> None:
        qr = _make_quality_result(overall_score=None)
        assert qr.overall_score is None

    def test_negative_gap_count_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            _make_quality_result(gap_count=-1)


@pytest.mark.diagnostics
class TestGapAnalysisDiagnostics:
    def test_valid_construction(self) -> None:
        rd = _make_run_diagnostics()
        assert rd.conditions_evaluated == 5

    def test_conditions_sum_mismatch_rejected(self) -> None:
        with pytest.raises(ContractValidationError, match="conditions_evaluated"):
            _make_run_diagnostics(
                conditions_evaluated=6,  # doesn't match 4+1+0+0=5
            )

    def test_negative_count_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            _make_run_diagnostics(gaps_emitted=-1)


@pytest.mark.diagnostics
class TestGapAnalysisResult:
    def test_is_complete_matches_recommended_status_complete(self) -> None:
        result = GapAnalysisResult(
            gaps=(),
            quality_diagnostics=_make_quality_result(),
            gap_analysis_diagnostics=_make_run_diagnostics(
                conditions_evaluated=5,
                conditions_passed=5,
                conditions_failed=0,
                gaps_emitted=0,
            ),
            recommended_status=ResearchStatus.COMPLETE,
            is_complete=True,
        )
        assert result.is_complete is True

    def test_is_complete_must_be_false_when_partial(self) -> None:
        with pytest.raises(ContractValidationError, match="is_complete"):
            GapAnalysisResult(
                gaps=(),
                quality_diagnostics=_make_quality_result(),
                gap_analysis_diagnostics=_make_run_diagnostics(
                    conditions_evaluated=5,
                    conditions_passed=5,
                    conditions_failed=0,
                    gaps_emitted=0,
                ),
                recommended_status=ResearchStatus.PARTIAL,
                is_complete=True,  # wrong!
            )

    def test_duplicate_gap_ids_rejected(self) -> None:
        from research_core.contracts.gaps import GapSeverity, GapStatus, GapType, ResearchGap

        g = ResearchGap(
            gap_id="gap-dup",
            gap_type=GapType.NO_EVIDENCE,
            description="dup",
            severity=GapSeverity.CRITICAL,
            status=GapStatus.OPEN,
        )
        with pytest.raises(ContractValidationError, match="duplicate gap_id"):
            GapAnalysisResult(
                gaps=(g, g),
                quality_diagnostics=_make_quality_result(),
                gap_analysis_diagnostics=_make_run_diagnostics(
                    conditions_evaluated=1,
                    conditions_passed=0,
                    conditions_failed=1,
                    gaps_emitted=2,
                ),
                recommended_status=ResearchStatus.PARTIAL,
                is_complete=False,
            )
