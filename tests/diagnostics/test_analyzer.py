"""
End-to-end tests for DeterministicGapAnalyzer.
"""

from __future__ import annotations

import pytest

from research_core.analysis.analyzer import DeterministicGapAnalyzer
from research_core.analysis.config import GapAnalysisConfig
from research_core.contracts.result import ResearchStatus

from tests.diagnostics.conftest import make_claim, make_ranked_evidence, make_source


@pytest.fixture
def analyzer() -> DeterministicGapAnalyzer:
    return DeterministicGapAnalyzer()


@pytest.mark.diagnostics
class TestAnalyzerEmptyInput:
    def test_no_sources_no_evidence_is_partial(self, analyzer: DeterministicGapAnalyzer) -> None:
        cfg = GapAnalysisConfig()
        result = analyzer.analyze([], [], [], None, cfg)
        assert result.recommended_status == ResearchStatus.PARTIAL
        assert not result.is_complete

    def test_no_evidence_has_critical_gaps(self, analyzer: DeterministicGapAnalyzer) -> None:
        cfg = GapAnalysisConfig()
        result = analyzer.analyze([make_source()], [], [], None, cfg)
        critical = [g for g in result.gaps if g.severity.value == "critical"]
        assert len(critical) >= 1

    def test_no_evidence_quality_score_is_none(
        self, analyzer: DeterministicGapAnalyzer
    ) -> None:
        cfg = GapAnalysisConfig()
        result = analyzer.analyze([], [], [], None, cfg)
        assert result.quality_diagnostics.overall_score is None


@pytest.mark.diagnostics
class TestAnalyzerMinimalHappyPath:
    def test_sufficient_evidence_and_claims_no_quality_gaps(
        self, analyzer: DeterministicGapAnalyzer
    ) -> None:
        cfg = GapAnalysisConfig(
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
        src = make_source()
        ev = make_ranked_evidence(evidence_id="ev-1", source_id="src-1")
        cl = make_claim(evidence_id="ev-1", source_id="src-1")
        result = analyzer.analyze([src], [ev], [cl], None, cfg)
        assert result.recommended_status == ResearchStatus.COMPLETE
        assert result.is_complete
        assert len(result.gaps) == 0


@pytest.mark.diagnostics
class TestAnalyzerResultStructure:
    def test_result_is_immutable(self, analyzer: DeterministicGapAnalyzer) -> None:
        cfg = GapAnalysisConfig()
        result = analyzer.analyze([], [], [], None, cfg)
        with pytest.raises((AttributeError, TypeError)):
            result.recommended_status = ResearchStatus.COMPLETE  # type: ignore[misc]

    def test_all_gap_ids_unique(self, analyzer: DeterministicGapAnalyzer) -> None:
        cfg = GapAnalysisConfig()
        result = analyzer.analyze([], [], [], None, cfg)
        gap_ids = [g.gap_id for g in result.gaps]
        assert len(gap_ids) == len(set(gap_ids))

    def test_diagnostics_condition_counts_sum(
        self, analyzer: DeterministicGapAnalyzer
    ) -> None:
        cfg = GapAnalysisConfig()
        result = analyzer.analyze([make_source()], [make_ranked_evidence()], [], None, cfg)
        diag = result.gap_analysis_diagnostics
        total = (
            diag.conditions_passed
            + diag.conditions_failed
            + diag.conditions_indeterminate
            + diag.conditions_unavailable
        )
        assert total == diag.conditions_evaluated

    def test_gaps_emitted_matches_gaps_length(
        self, analyzer: DeterministicGapAnalyzer
    ) -> None:
        cfg = GapAnalysisConfig()
        result = analyzer.analyze([], [], [], None, cfg)
        assert result.gap_analysis_diagnostics.gaps_emitted == len(result.gaps)

    def test_gap_count_in_quality_diagnostics_matches(
        self, analyzer: DeterministicGapAnalyzer
    ) -> None:
        cfg = GapAnalysisConfig()
        result = analyzer.analyze([], [], [], None, cfg)
        assert result.quality_diagnostics.gap_count == len(result.gaps)


@pytest.mark.diagnostics
class TestAnalyzerDeterminism:
    def test_identical_inputs_produce_identical_outputs(
        self, analyzer: DeterministicGapAnalyzer
    ) -> None:
        cfg = GapAnalysisConfig()
        src = make_source()
        ev = make_ranked_evidence()
        cl = make_claim()
        r1 = analyzer.analyze([src], [ev], [cl], None, cfg)
        r2 = analyzer.analyze([src], [ev], [cl], None, cfg)
        assert r1.gaps == r2.gaps
        assert r1.recommended_status == r2.recommended_status
        assert [g.gap_id for g in r1.gaps] == [g.gap_id for g in r2.gaps]


@pytest.mark.diagnostics
class TestAnalyzerGapSorting:
    def test_critical_gaps_before_high(self, analyzer: DeterministicGapAnalyzer) -> None:
        cfg = GapAnalysisConfig()
        # Empty input: expect both no_sources (CRITICAL) and no_evidence (CRITICAL)
        result = analyzer.analyze([], [], [], None, cfg)
        severities = [g.severity.value for g in result.gaps]
        # Verify most severe comes first
        if len(severities) > 1:
            assert severities[0] in ("critical", "high")


@pytest.mark.diagnostics
class TestAnalyzerInputCounts:
    def test_input_counts_in_diagnostics(self, analyzer: DeterministicGapAnalyzer) -> None:
        cfg = GapAnalysisConfig()
        src1 = make_source(source_id="src-1")
        src2 = make_source(source_id="src-2")
        ev1 = make_ranked_evidence(evidence_id="ev-1", source_id="src-1")
        ev2 = make_ranked_evidence(evidence_id="ev-2", source_id="src-2", rank=2)
        cl = make_claim()
        result = analyzer.analyze([src1, src2], [ev1, ev2], [cl], None, cfg)
        diag = result.gap_analysis_diagnostics
        assert diag.input_source_count == 2
        assert diag.input_evidence_count == 2
        assert diag.input_claim_count == 1
