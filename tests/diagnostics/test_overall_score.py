"""
Tests for compute_overall_score() — equal-weighted mean of dimension means.
"""

from __future__ import annotations

import pytest

from research_core.analysis.contracts import DiagnosticStatus, QualityDimensionSummary
from research_core.analysis.quality import compute_overall_score


def _dim(name: str, mean: float | None) -> QualityDimensionSummary:
    return QualityDimensionSummary(
        dimension=name,
        status=DiagnosticStatus.PASS if mean is not None else DiagnosticStatus.UNAVAILABLE,
        measured_count=1 if mean is not None else 0,
        missing_count=0 if mean is not None else 1,
        minimum=mean,
        maximum=mean,
        mean=mean,
        median=mean,
        threshold=0.3,
        below_threshold_count=0,
        affected_evidence_ids=(),
    )


@pytest.mark.diagnostics
class TestComputeOverallScore:
    def test_empty_dimensions_is_none(self) -> None:
        assert compute_overall_score(()) is None

    def test_all_unavailable_is_none(self) -> None:
        dims = (_dim("relevance", None), _dim("authority", None))
        assert compute_overall_score(dims) is None

    def test_single_dimension_is_its_mean(self) -> None:
        dims = (_dim("relevance", 0.7),)
        score = compute_overall_score(dims)
        assert score == pytest.approx(0.7)  # type: ignore[operator]

    def test_two_dimensions_equal_weight(self) -> None:
        dims = (_dim("relevance", 0.4), _dim("authority", 0.6))
        score = compute_overall_score(dims)
        assert score == pytest.approx(0.5)  # type: ignore[operator]

    def test_three_dimensions_mean(self) -> None:
        dims = (_dim("relevance", 0.3), _dim("authority", 0.6), _dim("recency", 0.9))
        score = compute_overall_score(dims)
        assert score == pytest.approx(0.6)  # type: ignore[operator]

    def test_partial_unavailable_skips_none(self) -> None:
        dims = (
            _dim("relevance", 0.8),
            _dim("authority", None),  # unavailable
        )
        score = compute_overall_score(dims)
        # Only relevance contributes
        assert score == pytest.approx(0.8)  # type: ignore[operator]

    def test_zero_mean_included(self) -> None:
        dims = (_dim("relevance", 0.0), _dim("authority", 0.8))
        score = compute_overall_score(dims)
        assert score == pytest.approx(0.4)  # type: ignore[operator]
