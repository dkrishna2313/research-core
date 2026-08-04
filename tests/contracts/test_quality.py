"""Tests for QualityDimension and QualityDiagnostics contracts."""

from __future__ import annotations

import types

import pytest

from research_core.contracts.quality import QualityDiagnostics, QualityDimension
from research_core.exceptions import ContractValidationError


class TestQualityDimension:
    def test_none_score_is_unavailable(self) -> None:
        dim = QualityDimension()
        assert dim.score is None
        assert dim.is_available is False

    def test_zero_score_is_available(self) -> None:
        dim = QualityDimension(score=0.0)
        assert dim.is_available is True

    def test_score_at_boundaries_accepted(self) -> None:
        assert QualityDimension(score=0.0).score == 0.0
        assert QualityDimension(score=1.0).score == 1.0

    def test_score_above_one_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            QualityDimension(score=1.01)

    def test_score_below_zero_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            QualityDimension(score=-0.1)

    def test_none_is_not_zero(self) -> None:
        none_dim = QualityDimension(score=None)
        zero_dim = QualityDimension(score=0.0)
        assert none_dim.score != zero_dim.score
        assert none_dim.is_available is False
        assert zero_dim.is_available is True

    def test_flags_default_to_empty_tuple(self) -> None:
        dim = QualityDimension()
        assert dim.flags == ()

    def test_is_frozen(self) -> None:
        dim = QualityDimension(score=0.5)
        with pytest.raises((AttributeError, TypeError)):
            dim.score = 0.6  # type: ignore[misc]


class TestQualityDiagnostics:
    def test_default_all_unavailable(self) -> None:
        diag = QualityDiagnostics()
        for name, dim in diag.dimensions().items():
            assert dim.score is None, f"Expected {name} to be unavailable"

    def test_twelve_dimensions_present(self) -> None:
        diag = QualityDiagnostics()
        dims = diag.dimensions()
        assert len(dims) == 12

    def test_all_dimension_names_present(self) -> None:
        diag = QualityDiagnostics()
        expected = {
            "relevance", "authority", "recency", "corroboration",
            "independence", "coverage", "extraction_confidence",
            "contradiction_severity", "uncertainty", "completeness",
            "provenance_completeness", "reproducibility",
        }
        assert set(diag.dimensions().keys()) == expected

    def test_available_dimensions_excludes_none(self) -> None:
        diag = QualityDiagnostics(
            relevance=QualityDimension(score=0.8),
        )
        available = diag.available_dimensions()
        assert "relevance" in available
        assert len(available) == 1

    def test_composite_none_by_default(self) -> None:
        diag = QualityDiagnostics()
        assert diag.composite is None

    def test_composite_in_range_accepted(self) -> None:
        diag = QualityDiagnostics(composite=0.75)
        assert diag.composite == 0.75

    def test_composite_above_one_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            QualityDiagnostics(composite=1.1)

    def test_composite_below_zero_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            QualityDiagnostics(composite=-0.5)

    def test_metadata_wrapped(self) -> None:
        diag = QualityDiagnostics(metadata={"key": "val"})
        assert isinstance(diag.metadata, types.MappingProxyType)

    def test_is_frozen(self) -> None:
        diag = QualityDiagnostics()
        with pytest.raises((AttributeError, TypeError)):
            diag.composite = 0.5  # type: ignore[misc]
