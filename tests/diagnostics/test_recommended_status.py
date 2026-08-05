"""
Tests for recommended_status logic: COMPLETE vs PARTIAL.
"""

from __future__ import annotations

import pytest

from research_core.analysis.analyzer import DeterministicGapAnalyzer
from research_core.analysis.config import GapAnalysisConfig
from research_core.contracts.result import ResearchStatus
from tests.diagnostics.conftest import make_claim, make_ranked_evidence, make_source

_PERMISSIVE = GapAnalysisConfig(
    minimum_evidence_count=1,
    minimum_source_count=1,
    minimum_claim_coverage_ratio=0.0,
    minimum_relevance_score=0.0,
    minimum_authority_score=0.0,
    minimum_recency_score=0.0,
    minimum_extraction_confidence_score=0.0,
    minimum_provenance_completeness_score=0.0,
    maximum_single_source_share=1.0,
    maximum_single_provider_share=1.0,
    minimum_quality_coverage_ratio=0.0,
)


@pytest.fixture
def analyzer() -> DeterministicGapAnalyzer:
    return DeterministicGapAnalyzer()


@pytest.mark.diagnostics
class TestRecommendedStatusPartial:
    def test_no_evidence_is_partial(self, analyzer: DeterministicGapAnalyzer) -> None:
        result = analyzer.analyze([], [], [], None, GapAnalysisConfig())
        assert result.recommended_status == ResearchStatus.PARTIAL

    def test_any_gap_is_partial(self, analyzer: DeterministicGapAnalyzer) -> None:
        cfg = GapAnalysisConfig(minimum_evidence_count=5)
        ev = make_ranked_evidence()
        result = analyzer.analyze([make_source()], [ev], [], None, cfg)
        assert result.recommended_status == ResearchStatus.PARTIAL

    def test_is_complete_false_when_partial(self, analyzer: DeterministicGapAnalyzer) -> None:
        result = analyzer.analyze([], [], [], None, GapAnalysisConfig())
        assert result.is_complete is False


@pytest.mark.diagnostics
class TestRecommendedStatusComplete:
    def test_sufficient_evidence_no_gaps_is_complete(
        self, analyzer: DeterministicGapAnalyzer
    ) -> None:
        src = make_source()
        ev = make_ranked_evidence()
        cl = make_claim()
        result = analyzer.analyze([src], [ev], [cl], None, _PERMISSIVE)
        assert result.recommended_status == ResearchStatus.COMPLETE
        assert result.is_complete is True

    def test_is_complete_true_iff_status_complete(
        self, analyzer: DeterministicGapAnalyzer
    ) -> None:
        src = make_source()
        ev = make_ranked_evidence()
        cl = make_claim()
        result = analyzer.analyze([src], [ev], [cl], None, _PERMISSIVE)
        assert result.is_complete == (result.recommended_status == ResearchStatus.COMPLETE)
