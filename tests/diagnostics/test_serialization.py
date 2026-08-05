"""
Tests for JSON round-trip serialization of RC6 contract types.

Uses research_core.contracts.serialization.serialize(), which handles
MappingProxyType metadata fields that dataclasses.asdict() cannot deepcopy.
"""

from __future__ import annotations

import json

import pytest

from research_core.analysis.analyzer import DeterministicGapAnalyzer
from research_core.analysis.config import GapAnalysisConfig
from research_core.analysis.contracts import (
    DiagnosticStatus,
    QualityDimensionSummary,
)
from research_core.contracts.common import EMPTY_METADATA
from research_core.contracts.serialization import serialize


def _make_dim(mean: float | None = 0.7) -> QualityDimensionSummary:
    return QualityDimensionSummary(
        dimension="relevance",
        status=DiagnosticStatus.PASS if mean is not None else DiagnosticStatus.UNAVAILABLE,
        measured_count=1 if mean is not None else 0,
        missing_count=0 if mean is not None else 1,
        minimum=mean,
        maximum=mean,
        mean=mean,
        median=mean,
        threshold=0.3,
        below_threshold_count=0,
        affected_evidence_ids=("ev-1",),
        metadata=EMPTY_METADATA,
    )


@pytest.mark.diagnostics
class TestQualityDimensionSummarySerializes:
    def test_dimension_json_serializable(self) -> None:
        dim = _make_dim()
        s = serialize(dim)
        j = json.dumps(s)
        loaded = json.loads(j)
        assert loaded["dimension"] == "relevance"
        assert loaded["mean"] == pytest.approx(0.7)  # type: ignore[operator]

    def test_none_values_preserved(self) -> None:
        dim = _make_dim(mean=None)
        s = serialize(dim)
        j = json.dumps(s)
        loaded = json.loads(j)
        assert loaded["mean"] is None
        assert loaded["minimum"] is None

    def test_affected_evidence_ids_as_list(self) -> None:
        dim = _make_dim()
        s = serialize(dim)
        j = json.dumps(s)
        loaded = json.loads(j)
        assert isinstance(loaded["affected_evidence_ids"], list)
        assert "ev-1" in loaded["affected_evidence_ids"]


@pytest.mark.diagnostics
class TestGapAnalysisResultSerializes:
    def test_result_json_serializable(self) -> None:
        from tests.diagnostics.conftest import make_ranked_evidence, make_source

        analyzer = DeterministicGapAnalyzer()
        cfg = GapAnalysisConfig()
        result = analyzer.analyze([], [], [], None, cfg)
        s = serialize(result)
        j = json.dumps(s)
        assert isinstance(j, str)

    def test_result_structure_keys(self) -> None:
        from tests.diagnostics.conftest import make_ranked_evidence, make_source

        analyzer = DeterministicGapAnalyzer()
        cfg = GapAnalysisConfig()
        result = analyzer.analyze([make_source()], [make_ranked_evidence()], [], None, cfg)
        s = serialize(result)
        assert "gaps" in s
        assert "quality_diagnostics" in s
        assert "gap_analysis_diagnostics" in s
        assert "recommended_status" in s

    def test_recommended_status_is_string(self) -> None:
        analyzer = DeterministicGapAnalyzer()
        cfg = GapAnalysisConfig()
        result = analyzer.analyze([], [], [], None, cfg)
        s = serialize(result)
        assert isinstance(s["recommended_status"], str)

    def test_gaps_is_list(self) -> None:
        analyzer = DeterministicGapAnalyzer()
        cfg = GapAnalysisConfig()
        result = analyzer.analyze([], [], [], None, cfg)
        s = serialize(result)
        assert isinstance(s["gaps"], list)

    def test_round_trip_gap_ids_preserved(self) -> None:
        analyzer = DeterministicGapAnalyzer()
        cfg = GapAnalysisConfig()
        result = analyzer.analyze([], [], [], None, cfg)
        s = serialize(result)
        j = json.dumps(s)
        loaded = json.loads(j)
        gap_ids_original = [g.gap_id for g in result.gaps]
        gap_ids_loaded = [g["gap_id"] for g in loaded["gaps"]]
        assert gap_ids_original == gap_ids_loaded
