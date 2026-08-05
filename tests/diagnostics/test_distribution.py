"""
Tests for compute_distribution() source and provider distribution diagnostics.
"""

from __future__ import annotations

import pytest

from research_core.analysis.aggregate import compute_distribution

from tests.diagnostics.conftest import make_ranked_evidence


@pytest.mark.diagnostics
class TestComputeDistributionEmpty:
    def test_no_evidence_all_none(self) -> None:
        dist = compute_distribution([])
        assert dist.unique_source_count == 0
        assert dist.unique_provider_count == 0
        assert dist.largest_source_share is None
        assert dist.largest_provider_share is None
        assert dist.source_diversity_score is None
        assert dist.provider_diversity_score is None


@pytest.mark.diagnostics
class TestComputeDistributionSingleSource:
    def test_single_source_full_concentration(self) -> None:
        ev = make_ranked_evidence(source_id="src-1", provider="prov-a")
        dist = compute_distribution([ev])
        assert dist.unique_source_count == 1
        assert dist.largest_source_share == 1.0
        assert dist.source_diversity_score == 0.0

    def test_single_provider_full_concentration(self) -> None:
        ev = make_ranked_evidence(provider="prov-a")
        dist = compute_distribution([ev])
        assert dist.largest_provider_share == 1.0
        assert dist.provider_diversity_score == 0.0


@pytest.mark.diagnostics
class TestComputeDistributionMultipleSources:
    def test_two_equal_sources(self) -> None:
        ev1 = make_ranked_evidence(evidence_id="ev-1", source_id="src-1")
        ev2 = make_ranked_evidence(evidence_id="ev-2", source_id="src-2", rank=2)
        dist = compute_distribution([ev1, ev2])
        assert dist.unique_source_count == 2
        assert dist.largest_source_share == 0.5
        assert dist.source_diversity_score == 0.5

    def test_dominant_source(self) -> None:
        ev1 = make_ranked_evidence(evidence_id="ev-1", source_id="src-1", rank=1)
        ev2 = make_ranked_evidence(evidence_id="ev-2", source_id="src-1", rank=2)
        ev3 = make_ranked_evidence(evidence_id="ev-3", source_id="src-2", rank=3)
        dist = compute_distribution([ev1, ev2, ev3])
        assert pytest.approx(dist.largest_source_share) == 2 / 3  # type: ignore[operator]

    def test_evidence_per_source_counts(self) -> None:
        ev1 = make_ranked_evidence(evidence_id="ev-1", source_id="src-1")
        ev2 = make_ranked_evidence(evidence_id="ev-2", source_id="src-1", rank=2)
        ev3 = make_ranked_evidence(evidence_id="ev-3", source_id="src-2", rank=3)
        dist = compute_distribution([ev1, ev2, ev3])
        assert dist.evidence_per_source["src-1"] == 2
        assert dist.evidence_per_source["src-2"] == 1


@pytest.mark.diagnostics
class TestComputeDistributionMultipleProviders:
    def test_two_equal_providers(self) -> None:
        ev1 = make_ranked_evidence(evidence_id="ev-1", provider="prov-a")
        ev2 = make_ranked_evidence(evidence_id="ev-2", provider="prov-b", rank=2)
        dist = compute_distribution([ev1, ev2])
        assert dist.unique_provider_count == 2
        assert dist.largest_provider_share == 0.5

    def test_evidence_per_provider_counts(self) -> None:
        ev1 = make_ranked_evidence(evidence_id="ev-1", provider="prov-a")
        ev2 = make_ranked_evidence(evidence_id="ev-2", provider="prov-a", rank=2)
        dist = compute_distribution([ev1, ev2])
        assert dist.evidence_per_provider["prov-a"] == 2

    def test_diversity_complementary_to_concentration(self) -> None:
        ev1 = make_ranked_evidence(evidence_id="ev-1", source_id="src-1")
        ev2 = make_ranked_evidence(evidence_id="ev-2", source_id="src-2", rank=2)
        dist = compute_distribution([ev1, ev2])
        assert pytest.approx(dist.source_diversity_score + dist.largest_source_share) == 1.0  # type: ignore[operator]
