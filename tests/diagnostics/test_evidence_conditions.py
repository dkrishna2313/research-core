"""
Tests for compute_evidence_conditions() low-level evidence state diagnostics.
"""

from __future__ import annotations

from typing import Any

import pytest

from research_core.analysis.aggregate import compute_evidence_conditions
from research_core.contracts.common import _to_proxy

from tests.diagnostics.conftest import make_evidence, make_ranked_evidence, make_source


def _truncated_ranked_evidence(evidence_id: str = "ev-trunc", rank: int = 1) -> Any:
    from research_core.contracts.common import SourceType
    from research_core.normalization.contracts import (
        ComponentStatus,
        NormalizedEvidence,
        RankedEvidence,
        RankingComponent,
    )

    source = make_source()
    evidence = make_evidence(
        evidence_id=evidence_id,
        metadata=_to_proxy({"truncated": True}),
    )
    norm_ev = NormalizedEvidence(
        evidence=evidence,
        source=source,
        provider="test",
        provider_rank=1,
        provider_score=None,
        normalized_retrieval_signal=None,
        content_length=100,
        parent_evidence_id=None,
        segment_index=None,
    )
    return RankedEvidence(
        normalized_evidence=norm_ev,
        rank=rank,
        score=0.5,
        components=(
            RankingComponent(
                name="retrieval",
                status=ComponentStatus.MISSING,
                raw_value=None,
                normalized_value=None,
                weight_used=0.0,
            ),
        ),
    )


@pytest.mark.diagnostics
class TestComputeEvidenceConditionsEmpty:
    def test_no_evidence(self) -> None:
        cond = compute_evidence_conditions([], None)
        assert cond.truncated_evidence_count == 0
        assert cond.duplicate_evidence_count == 0
        assert cond.invalid_lineage_count == 0


@pytest.mark.diagnostics
class TestTruncation:
    def test_truncated_evidence_detected(self) -> None:
        ev = _truncated_ranked_evidence()
        cond = compute_evidence_conditions([ev], None)
        assert cond.truncated_evidence_count == 1

    def test_non_truncated_not_counted(self) -> None:
        ev = make_ranked_evidence()
        cond = compute_evidence_conditions([ev], None)
        assert cond.truncated_evidence_count == 0

    def test_mixed_truncation(self) -> None:
        normal = make_ranked_evidence(evidence_id="ev-1")
        trunc = _truncated_ranked_evidence(evidence_id="ev-2", rank=2)
        cond = compute_evidence_conditions([normal, trunc], None)
        assert cond.truncated_evidence_count == 1


@pytest.mark.diagnostics
class TestDuplicateCounts:
    def test_no_ranking_result_zero_duplicates(self) -> None:
        ev = make_ranked_evidence()
        cond = compute_evidence_conditions([ev], None)
        assert cond.duplicate_evidence_count == 0

    def test_duplicate_count_from_ranking_result(self) -> None:
        from unittest.mock import MagicMock

        ranking_result = MagicMock()
        ranking_result.duplicates = [MagicMock(), MagicMock()]
        ev = make_ranked_evidence()
        cond = compute_evidence_conditions([ev], ranking_result)
        assert cond.duplicate_evidence_count == 2


@pytest.mark.diagnostics
class TestInvalidLineage:
    def test_segment_index_without_parent_is_invalid(self) -> None:
        ev = make_ranked_evidence(segment_index=0, parent_evidence_id=None)
        cond = compute_evidence_conditions([ev], None)
        assert cond.invalid_lineage_count == 1

    def test_parent_without_segment_index_is_invalid(self) -> None:
        ev = make_ranked_evidence(parent_evidence_id="ev-parent", segment_index=None)
        cond = compute_evidence_conditions([ev], None)
        assert cond.invalid_lineage_count == 1

    def test_both_set_is_valid(self) -> None:
        ev = make_ranked_evidence(
            parent_evidence_id="ev-parent", segment_index=0, evidence_id="ev-seg"
        )
        cond = compute_evidence_conditions([ev], None)
        assert cond.invalid_lineage_count == 0

    def test_neither_set_is_valid(self) -> None:
        ev = make_ranked_evidence()
        cond = compute_evidence_conditions([ev], None)
        assert cond.invalid_lineage_count == 0


@pytest.mark.diagnostics
class TestMissingScoreAndRank:
    def test_missing_provider_score_counted(self) -> None:
        ev = make_ranked_evidence(provider_score=None)
        cond = compute_evidence_conditions([ev], None)
        assert cond.missing_retrieval_score_count == 1

    def test_present_provider_score_not_counted(self) -> None:
        ev = make_ranked_evidence(provider_score=0.8)
        cond = compute_evidence_conditions([ev], None)
        assert cond.missing_retrieval_score_count == 0

    def test_near_duplicate_always_zero_in_rc6(self) -> None:
        ev = make_ranked_evidence()
        cond = compute_evidence_conditions([ev], None)
        assert cond.near_duplicate_evidence_count == 0
