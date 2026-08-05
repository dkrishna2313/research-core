"""
Tests for quality dimension scoring (score_all_dimensions, _score_dimension).
"""

from __future__ import annotations

import pytest

from research_core.analysis.aggregate import compute_coverage
from research_core.analysis.config import GapAnalysisConfig
from research_core.analysis.contracts import DiagnosticStatus
from research_core.analysis.quality import (
    SCORED_DIMENSIONS,
    compute_overall_score,
    score_all_dimensions,
)
from tests.diagnostics.conftest import make_ranked_evidence, make_source


@pytest.mark.diagnostics
class TestScoredDimensions:
    def test_five_dimensions_defined(self) -> None:
        assert len(SCORED_DIMENSIONS) == 5

    def test_required_dimensions_present(self) -> None:
        required = {
            "relevance", "authority", "recency",
            "extraction_confidence", "provenance_completeness",
        }
        assert required == set(SCORED_DIMENSIONS)


@pytest.mark.diagnostics
class TestScoreAllDimensionsEmpty:
    def test_no_evidence_all_unavailable(self) -> None:
        cfg = GapAnalysisConfig()
        coverage = compute_coverage([], [], [])
        dims = score_all_dimensions([], coverage, cfg)
        assert len(dims) == 5
        for d in dims:
            assert d.status == DiagnosticStatus.UNAVAILABLE
            assert d.mean is None
            assert d.measured_count == 0


@pytest.mark.diagnostics
class TestScoreRelevance:
    def test_evidence_with_relevance_above_threshold(self) -> None:
        cfg = GapAnalysisConfig(minimum_relevance_score=0.3)
        ev = make_ranked_evidence(quality_kwargs={"relevance": 0.8})
        src = make_source()
        coverage = compute_coverage([src], [ev], [])
        dims = score_all_dimensions([ev], coverage, cfg)
        relevance = next(d for d in dims if d.dimension == "relevance")
        assert relevance.status == DiagnosticStatus.PASS
        assert relevance.mean == pytest.approx(0.8)  # type: ignore[operator]

    def test_evidence_with_relevance_below_threshold(self) -> None:
        cfg = GapAnalysisConfig(minimum_relevance_score=0.5)
        ev = make_ranked_evidence(quality_kwargs={"relevance": 0.2})
        src = make_source()
        coverage = compute_coverage([src], [ev], [])
        dims = score_all_dimensions([ev], coverage, cfg)
        relevance = next(d for d in dims if d.dimension == "relevance")
        assert relevance.status == DiagnosticStatus.FAIL
        assert relevance.below_threshold_count == 1

    def test_missing_relevance_is_unavailable(self) -> None:
        cfg = GapAnalysisConfig()
        ev = make_ranked_evidence(quality_kwargs={"relevance": None})
        src = make_source()
        coverage = compute_coverage([src], [ev], [])
        dims = score_all_dimensions([ev], coverage, cfg)
        relevance = next(d for d in dims if d.dimension == "relevance")
        assert relevance.status == DiagnosticStatus.UNAVAILABLE
        assert relevance.missing_count == 1


@pytest.mark.diagnostics
class TestScoreProvenanceCompleteness:
    def test_provenance_completeness_from_components(self) -> None:
        cfg = GapAnalysisConfig(minimum_provenance_completeness_score=0.5)
        ev = make_ranked_evidence(provenance_completeness=0.9)
        src = make_source()
        coverage = compute_coverage([src], [ev], [])
        dims = score_all_dimensions([ev], coverage, cfg)
        prov = next(d for d in dims if d.dimension == "provenance_completeness")
        assert prov.status == DiagnosticStatus.PASS
        assert prov.mean == pytest.approx(0.9)  # type: ignore[operator]

    def test_missing_provenance_completeness(self) -> None:
        cfg = GapAnalysisConfig()
        ev = make_ranked_evidence(provenance_completeness=None)
        src = make_source()
        coverage = compute_coverage([src], [ev], [])
        dims = score_all_dimensions([ev], coverage, cfg)
        prov = next(d for d in dims if d.dimension == "provenance_completeness")
        assert prov.status == DiagnosticStatus.UNAVAILABLE


@pytest.mark.diagnostics
class TestScoreAggregation:
    def test_mean_of_multiple_values(self) -> None:
        cfg = GapAnalysisConfig(minimum_authority_score=0.2)
        ev1 = make_ranked_evidence(evidence_id="ev-1", quality_kwargs={"authority": 0.4})
        ev2 = make_ranked_evidence(evidence_id="ev-2", rank=2, quality_kwargs={"authority": 0.6})
        src = make_source()
        coverage = compute_coverage([src], [ev1, ev2], [])
        dims = score_all_dimensions([ev1, ev2], coverage, cfg)
        auth = next(d for d in dims if d.dimension == "authority")
        assert auth.mean == pytest.approx(0.5)  # type: ignore[operator]
        assert auth.minimum == pytest.approx(0.4)  # type: ignore[operator]
        assert auth.maximum == pytest.approx(0.6)  # type: ignore[operator]

    def test_dimensions_in_fixed_order(self) -> None:
        cfg = GapAnalysisConfig()
        ev = make_ranked_evidence()
        coverage = compute_coverage([], [ev], [])
        dims = score_all_dimensions([ev], coverage, cfg)
        assert [d.dimension for d in dims] == list(SCORED_DIMENSIONS)


@pytest.mark.diagnostics
class TestComputeOverallScore:
    def test_no_dimensions_is_none(self) -> None:
        assert compute_overall_score(()) is None

    def test_all_none_means_is_none(self) -> None:
        from research_core.analysis.contracts import QualityDimensionSummary

        dim = QualityDimensionSummary(
            dimension="relevance",
            status=DiagnosticStatus.UNAVAILABLE,
            measured_count=0,
            missing_count=1,
            minimum=None,
            maximum=None,
            mean=None,
            median=None,
            threshold=0.3,
            below_threshold_count=0,
            affected_evidence_ids=(),
        )
        assert compute_overall_score((dim,)) is None

    def test_equal_weight_fmean(self) -> None:
        from research_core.analysis.contracts import QualityDimensionSummary

        def _dim(name: str, mean: float) -> QualityDimensionSummary:
            return QualityDimensionSummary(
                dimension=name,
                status=DiagnosticStatus.PASS,
                measured_count=1,
                missing_count=0,
                minimum=mean,
                maximum=mean,
                mean=mean,
                median=mean,
                threshold=0.3,
                below_threshold_count=0,
                affected_evidence_ids=(),
            )

        dims = (_dim("relevance", 0.4), _dim("authority", 0.6))
        score = compute_overall_score(dims)
        assert score == pytest.approx(0.5)  # type: ignore[operator]
