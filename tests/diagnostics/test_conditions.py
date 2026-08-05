"""
Tests for individual gap condition evaluators in conditions.py.
"""

from __future__ import annotations

import pytest

from research_core.analysis.aggregate import (
    compute_coverage,
    compute_distribution,
    compute_evidence_conditions,
)
from research_core.analysis.conditions import (
    ConditionStatus,
    cond_duplicate_concentration,
    cond_insufficient_evidence,
    cond_insufficient_sources,
    cond_low_authority,
    cond_low_extraction_confidence,
    cond_low_relevance,
    cond_no_claims,
    cond_no_evidence,
    cond_no_sources,
    cond_provider_concentration,
    cond_source_concentration,
    cond_stale_evidence,
    cond_truncation,
)
from research_core.analysis.config import GapAnalysisConfig
from research_core.analysis.quality import score_all_dimensions
from research_core.contracts.gaps import GapSeverity, GapType
from tests.diagnostics.conftest import make_claim, make_ranked_evidence, make_source


def _coverage(sources, ranked_evidence, claims):
    return compute_coverage(sources, ranked_evidence, claims)


def _distribution(ranked_evidence):
    return compute_distribution(ranked_evidence)


def _ev_cond(ranked_evidence, ranking_result=None):
    return compute_evidence_conditions(ranked_evidence, ranking_result)


def _dims(ranked_evidence, cfg):
    cov = compute_coverage([], ranked_evidence, [])
    return score_all_dimensions(ranked_evidence, cov, cfg)


@pytest.mark.diagnostics
class TestCondNoSources:
    def test_no_sources_is_critical_fail(self) -> None:
        cfg = GapAnalysisConfig()
        result = cond_no_sources([], cfg)
        assert result.status == ConditionStatus.FAIL
        assert result.gap is not None
        assert result.gap.severity == GapSeverity.CRITICAL
        assert result.gap.gap_type == GapType.NO_EVIDENCE

    def test_with_source_passes(self) -> None:
        cfg = GapAnalysisConfig()
        result = cond_no_sources([make_source()], cfg)
        assert result.status == ConditionStatus.PASS
        assert result.gap is None


@pytest.mark.diagnostics
class TestCondNoEvidence:
    def test_no_evidence_is_critical_fail(self) -> None:
        cfg = GapAnalysisConfig()
        result = cond_no_evidence([], cfg)
        assert result.status == ConditionStatus.FAIL
        assert result.gap.severity == GapSeverity.CRITICAL

    def test_with_evidence_passes(self) -> None:
        cfg = GapAnalysisConfig()
        result = cond_no_evidence([make_ranked_evidence()], cfg)
        assert result.status == ConditionStatus.PASS


@pytest.mark.diagnostics
class TestCondInsufficientEvidence:
    def test_below_minimum_is_high_fail(self) -> None:
        cfg = GapAnalysisConfig(minimum_evidence_count=3)
        ev = [make_ranked_evidence(evidence_id=f"ev-{i}", rank=i + 1) for i in range(2)]
        result = cond_insufficient_evidence(ev, cfg)
        assert result.status == ConditionStatus.FAIL
        assert result.gap.severity == GapSeverity.HIGH

    def test_at_minimum_passes(self) -> None:
        cfg = GapAnalysisConfig(minimum_evidence_count=2)
        ev = [make_ranked_evidence(evidence_id=f"ev-{i}", rank=i + 1) for i in range(2)]
        result = cond_insufficient_evidence(ev, cfg)
        assert result.status == ConditionStatus.PASS


@pytest.mark.diagnostics
class TestCondInsufficientSources:
    def test_no_evidence_unavailable(self) -> None:
        cfg = GapAnalysisConfig()
        result = cond_insufficient_sources([make_source()], [], cfg)
        assert result.status == ConditionStatus.UNAVAILABLE

    def test_below_minimum_sources_is_fail(self) -> None:
        cfg = GapAnalysisConfig(minimum_source_count=2)
        ev = make_ranked_evidence(source_id="src-1")
        result = cond_insufficient_sources([make_source()], [ev], cfg)
        assert result.status == ConditionStatus.FAIL
        assert result.gap.severity == GapSeverity.HIGH

    def test_sufficient_sources_passes(self) -> None:
        cfg = GapAnalysisConfig(minimum_source_count=1)
        ev = make_ranked_evidence()
        result = cond_insufficient_sources([make_source()], [ev], cfg)
        assert result.status == ConditionStatus.PASS


@pytest.mark.diagnostics
class TestCondNoClaims:
    def test_no_evidence_unavailable(self) -> None:
        cfg = GapAnalysisConfig()
        result = cond_no_claims([], [], cfg)
        assert result.status == ConditionStatus.UNAVAILABLE

    def test_evidence_no_claims_is_medium_fail(self) -> None:
        cfg = GapAnalysisConfig()
        ev = make_ranked_evidence()
        result = cond_no_claims([ev], [], cfg)
        assert result.status == ConditionStatus.FAIL
        assert result.gap.severity == GapSeverity.MEDIUM

    def test_with_claims_passes(self) -> None:
        cfg = GapAnalysisConfig()
        ev = make_ranked_evidence()
        cl = make_claim()
        result = cond_no_claims([ev], [cl], cfg)
        assert result.status == ConditionStatus.PASS


@pytest.mark.diagnostics
class TestCondSourceConcentration:
    def test_all_from_one_source_triggers(self) -> None:
        cfg = GapAnalysisConfig(maximum_single_source_share=0.8)
        ev1 = make_ranked_evidence(evidence_id="ev-1", source_id="src-1")
        ev2 = make_ranked_evidence(evidence_id="ev-2", source_id="src-1", rank=2)
        dist = _distribution([ev1, ev2])
        result = cond_source_concentration(dist, cfg)
        assert result.status == ConditionStatus.FAIL
        assert result.gap.severity == GapSeverity.HIGH

    def test_two_sources_balanced_passes(self) -> None:
        cfg = GapAnalysisConfig(maximum_single_source_share=0.8)
        ev1 = make_ranked_evidence(evidence_id="ev-1", source_id="src-1")
        ev2 = make_ranked_evidence(evidence_id="ev-2", source_id="src-2", rank=2)
        dist = _distribution([ev1, ev2])
        result = cond_source_concentration(dist, cfg)
        assert result.status == ConditionStatus.PASS


@pytest.mark.diagnostics
class TestCondProviderConcentration:
    def test_single_provider_triggers(self) -> None:
        cfg = GapAnalysisConfig(maximum_single_provider_share=0.8)
        ev1 = make_ranked_evidence(evidence_id="ev-1", provider="prov-a")
        ev2 = make_ranked_evidence(evidence_id="ev-2", provider="prov-a", rank=2)
        dist = _distribution([ev1, ev2])
        result = cond_provider_concentration(dist, cfg)
        assert result.status == ConditionStatus.FAIL
        assert result.gap.severity == GapSeverity.MEDIUM

    def test_empty_evidence_unavailable(self) -> None:
        cfg = GapAnalysisConfig()
        dist = _distribution([])
        result = cond_provider_concentration(dist, cfg)
        assert result.status == ConditionStatus.UNAVAILABLE


@pytest.mark.diagnostics
class TestCondLowAuthority:
    def test_low_authority_triggers(self) -> None:
        cfg = GapAnalysisConfig(minimum_authority_score=0.5)
        ev = make_ranked_evidence(quality_kwargs={"authority": 0.1})
        dims = _dims([ev], cfg)
        result = cond_low_authority(dims, cfg)
        assert result.status == ConditionStatus.FAIL
        assert result.gap.gap_type == GapType.WEAK_AUTHORITY
        assert result.gap.severity == GapSeverity.HIGH

    def test_sufficient_authority_passes(self) -> None:
        cfg = GapAnalysisConfig(minimum_authority_score=0.3)
        ev = make_ranked_evidence(quality_kwargs={"authority": 0.9})
        dims = _dims([ev], cfg)
        result = cond_low_authority(dims, cfg)
        assert result.status == ConditionStatus.PASS

    def test_no_authority_data_unavailable(self) -> None:
        cfg = GapAnalysisConfig()
        ev = make_ranked_evidence(quality_kwargs={"authority": None})
        dims = _dims([ev], cfg)
        result = cond_low_authority(dims, cfg)
        assert result.status == ConditionStatus.UNAVAILABLE


@pytest.mark.diagnostics
class TestCondLowRelevance:
    def test_low_relevance_triggers_insufficient_coverage(self) -> None:
        cfg = GapAnalysisConfig(minimum_relevance_score=0.5)
        ev = make_ranked_evidence(quality_kwargs={"relevance": 0.1})
        dims = _dims([ev], cfg)
        result = cond_low_relevance(dims, cfg)
        assert result.status == ConditionStatus.FAIL
        assert result.gap.gap_type == GapType.INSUFFICIENT_COVERAGE


@pytest.mark.diagnostics
class TestCondStaleEvidence:
    def test_low_recency_triggers(self) -> None:
        cfg = GapAnalysisConfig(minimum_recency_score=0.5)
        ev = make_ranked_evidence(quality_kwargs={"recency": 0.1})
        dims = _dims([ev], cfg)
        result = cond_stale_evidence(dims, [ev], cfg)
        assert result.status == ConditionStatus.FAIL
        assert result.gap.gap_type == GapType.STALE_EVIDENCE

    def test_sufficient_recency_passes(self) -> None:
        cfg = GapAnalysisConfig(minimum_recency_score=0.2)
        ev = make_ranked_evidence(quality_kwargs={"recency": 0.9})
        dims = _dims([ev], cfg)
        result = cond_stale_evidence(dims, [ev], cfg)
        assert result.status == ConditionStatus.PASS


@pytest.mark.diagnostics
class TestCondLowExtractionConfidence:
    def test_low_extraction_confidence_triggers(self) -> None:
        cfg = GapAnalysisConfig(minimum_extraction_confidence_score=0.5)
        ev = make_ranked_evidence(quality_kwargs={"extraction_confidence": 0.1})
        dims = _dims([ev], cfg)
        result = cond_low_extraction_confidence(dims, cfg)
        assert result.status == ConditionStatus.FAIL
        assert result.gap.gap_type == GapType.LOW_EXTRACTION_CONFIDENCE


@pytest.mark.diagnostics
class TestCondDuplicateConcentration:
    def test_high_duplicate_share_triggers(self) -> None:
        from unittest.mock import MagicMock

        cfg = GapAnalysisConfig(maximum_duplicate_share=0.3)
        ev1 = make_ranked_evidence(evidence_id="ev-1")
        ev2 = make_ranked_evidence(evidence_id="ev-2", rank=2)
        ranking_result = MagicMock()
        ranking_result.duplicates = [MagicMock()]  # 1/2 = 50% > 30%
        ev_cond = _ev_cond([ev1, ev2], ranking_result)
        result = cond_duplicate_concentration(ev_cond, [ev1, ev2], cfg)
        assert result.status == ConditionStatus.FAIL

    def test_low_duplicate_share_passes(self) -> None:
        from unittest.mock import MagicMock

        cfg = GapAnalysisConfig(maximum_duplicate_share=0.8)
        ev = make_ranked_evidence()
        ranking_result = MagicMock()
        ranking_result.duplicates = []
        ev_cond = _ev_cond([ev], ranking_result)
        result = cond_duplicate_concentration(ev_cond, [ev], cfg)
        assert result.status == ConditionStatus.PASS


@pytest.mark.diagnostics
class TestCondTruncation:
    def test_no_evidence_unavailable(self) -> None:
        cfg = GapAnalysisConfig()
        ev_cond = _ev_cond([], None)
        result = cond_truncation(ev_cond, [], cfg)
        assert result.status == ConditionStatus.UNAVAILABLE
