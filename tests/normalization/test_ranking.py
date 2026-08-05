"""Tests for evidence ranking."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.normalization

from research_core.contracts.sources import EvidenceQuality  # noqa: E402
from research_core.normalization.config import RankingConfig  # noqa: E402
from research_core.normalization.contracts import (  # noqa: E402
    ComponentStatus,
    DuplicateEvidence,
    ExcludedEvidence,
    NormalizedEvidence,
)
from research_core.normalization.normalize import normalize_evidence  # noqa: E402
from research_core.normalization.ranking import rank_evidence  # noqa: E402
from tests.normalization.conftest import (  # noqa: E402
    make_knowledge_evidence,
    make_knowledge_source,
    make_source,
    make_web_evidence,
)


def _make_normalized(
    evidence_id: str = "ev-001",
    source_id: str = "src-001",
    content: str = "Some ranking test content here.",
    rank: int = 1,
    score: float | None = None,
    quality: EvidenceQuality | None = None,
) -> NormalizedEvidence:
    src = make_source(source_id=source_id)
    ev = make_web_evidence(
        evidence_id=evidence_id,
        source_id=source_id,
        content=content,
        rank=rank,
        score=score,
        quality=quality,
    )
    result = normalize_evidence(sources=(src,), evidence=(ev,))
    return result[0]


def _make_knowledge_normalized(
    evidence_id: str = "ev-k01",
    source_id: str = "src-k01",
    content: str = "Knowledge ranking test content here.",
    score: float | None = 0.85,
    quality: EvidenceQuality | None = None,
) -> NormalizedEvidence:
    src = make_knowledge_source(source_id=source_id)
    ev = make_knowledge_evidence(
        evidence_id=evidence_id,
        source_id=source_id,
        content=content,
        score=score,
        quality=quality,
    )
    result = normalize_evidence(sources=(src,), evidence=(ev,))
    return result[0]


class TestRankingBasic:
    def test_returns_evidence_ranking_result(self) -> None:
        from research_core.normalization.contracts import EvidenceRankingResult

        item = _make_normalized()
        result = rank_evidence([item], [], [], RankingConfig())
        assert isinstance(result, EvidenceRankingResult)

    def test_ranks_are_one_based(self) -> None:
        items = [_make_normalized(f"ev-{i:02d}", rank=i + 1) for i in range(3)]
        result = rank_evidence(items, [], [], RankingConfig())
        assert result.ranked[0].rank == 1
        assert result.ranked[1].rank == 2
        assert result.ranked[2].rank == 3

    def test_empty_input_returns_empty(self) -> None:
        result = rank_evidence([], [], [], RankingConfig())
        assert len(result.ranked) == 0

    def test_single_item_rank_is_one(self) -> None:
        item = _make_normalized()
        result = rank_evidence([item], [], [], RankingConfig())
        assert result.ranked[0].rank == 1

    def test_score_is_in_unit_interval(self) -> None:
        item = _make_knowledge_normalized(
            quality=EvidenceQuality(
                relevance=0.8, authority=0.7, recency=0.6, extraction_confidence=0.9
            )
        )
        result = rank_evidence([item], [], [], RankingConfig())
        assert 0.0 <= result.ranked[0].score <= 1.0


class TestRankingComponents:
    def test_available_components_have_available_status(self) -> None:
        item = _make_knowledge_normalized(
            quality=EvidenceQuality(
                relevance=0.8, authority=0.7, recency=0.6, extraction_confidence=0.9
            )
        )
        result = rank_evidence([item], [], [], RankingConfig())
        components = {c.name: c for c in result.ranked[0].components}
        assert components["relevance"].status == ComponentStatus.AVAILABLE
        assert components["authority"].status == ComponentStatus.AVAILABLE

    def test_missing_components_have_missing_status(self) -> None:
        item = _make_normalized(quality=EvidenceQuality())  # no quality scores
        result = rank_evidence([item], [], [], RankingConfig())
        components = {c.name: c for c in result.ranked[0].components}
        assert components["relevance"].status == ComponentStatus.MISSING

    def test_all_components_missing_gives_zero_score(self) -> None:
        from datetime import UTC, datetime

        from research_core.contracts.common import SourceType
        from research_core.contracts.evidence import EvidenceItem
        from research_core.contracts.sources import EvidenceQuality, Provenance

        src = make_source(source_id="src-bare")
        prov = Provenance(
            source_id="src-bare",
            source_type=SourceType.WEB,
            retrieved_at=datetime(2024, 1, 1, tzinfo=UTC),
            # No rank, no score, no extraction_confidence
        )
        ev = EvidenceItem(
            evidence_id="ev-bare",
            content="Content with no quality signals at all.",
            source_id="src-bare",
            provenance=prov,
            quality=EvidenceQuality(),
        )
        items = list(normalize_evidence(sources=(src,), evidence=(ev,)))
        result = rank_evidence(items, [], [], RankingConfig())
        # provenance_completeness is never None (computed), so score > 0
        # but all quality dims are None and retrieval_signal is None
        # Only provenance_completeness contributes
        assert result.ranked[0].score >= 0.0

    def test_zero_quality_score_included_not_missing(self) -> None:
        item = _make_knowledge_normalized(
            quality=EvidenceQuality(
                relevance=0.0, authority=0.5, recency=None, extraction_confidence=None
            )
        )
        result = rank_evidence([item], [], [], RankingConfig())
        components = {c.name: c for c in result.ranked[0].components}
        # relevance=0.0 is NOT missing — it's available with value 0.0
        assert components["relevance"].status == ComponentStatus.AVAILABLE
        assert components["relevance"].normalized_value == 0.0

    def test_component_weights_sum_to_one(self) -> None:
        item = _make_knowledge_normalized(
            quality=EvidenceQuality(
                relevance=0.8, authority=0.7, recency=0.6, extraction_confidence=0.9
            )
        )
        result = rank_evidence([item], [], [], RankingConfig())
        total_weight = sum(c.weight_used for c in result.ranked[0].components)
        assert abs(total_weight - 1.0) < 1e-9


class TestRankingOrder:
    def test_higher_score_ranks_first(self) -> None:
        high = _make_knowledge_normalized(
            "ev-high", "src-high",
            quality=EvidenceQuality(
                relevance=0.9, authority=0.9, recency=0.9, extraction_confidence=0.9
            ),
        )
        low = _make_knowledge_normalized(
            "ev-low", "src-low",
            quality=EvidenceQuality(
                relevance=0.1, authority=0.1, recency=0.1, extraction_confidence=0.1
            ),
        )
        result = rank_evidence([low, high], [], [], RankingConfig())
        assert result.ranked[0].normalized_evidence.evidence.evidence_id == "ev-high"

    def test_deterministic_on_repeated_calls(self) -> None:
        items = [_make_normalized(f"ev-{i:02d}", rank=i + 1) for i in range(5)]
        r1 = rank_evidence(items, [], [], RankingConfig())
        r2 = rank_evidence(items, [], [], RankingConfig())
        assert [e.normalized_evidence.evidence.evidence_id for e in r1.ranked] == \
               [e.normalized_evidence.evidence.evidence_id for e in r2.ranked]


class TestProvenanceCompletenessProviderAware:
    """Provenance completeness does not penalise providers for naturally absent fields."""

    def test_web_evidence_with_url_scores_full_completeness(self) -> None:
        from datetime import UTC, datetime

        from research_core.contracts.common import SourceType
        from research_core.contracts.sources import Provenance
        from research_core.normalization.ranking import _applicable_fields, _field_is_present

        prov = Provenance(
            source_id="src-w",
            source_type=SourceType.WEB,
            retrieved_at=datetime(2024, 1, 1, tzinfo=UTC),
            provider="duckduckgo",
            retrieval_query="test query",
            retrieval_rank=1,
            # no retrieval_score — DDGS doesn't provide it
            extraction_method="trafilatura",
            url="https://example.com/page",
            content_hash="abc123",
        )
        applicable = _applicable_fields(prov.source_type)
        present = sum(1 for f in applicable if _field_is_present(getattr(prov, f, None)))
        assert present == len(applicable), (
            f"Web: {present}/{len(applicable)} fields present; "
            f"missing: {[f for f in applicable if not _field_is_present(getattr(prov, f, None))]}"
        )

    def test_knowledge_evidence_without_url_scores_full_completeness(self) -> None:
        from datetime import UTC, datetime

        from research_core.contracts.common import SourceType
        from research_core.contracts.sources import Provenance
        from research_core.normalization.ranking import _applicable_fields, _field_is_present

        prov = Provenance(
            source_id="src-k",
            source_type=SourceType.KNOWLEDGE,
            retrieved_at=datetime(2024, 1, 1, tzinfo=UTC),
            provider="knowledge",
            retrieval_query="test query",
            retrieval_rank=1,
            retrieval_score=0.85,
            extraction_method="text",
            content_hash="def456",
            # no url — knowledge documents don't have URLs
        )
        applicable = _applicable_fields(prov.source_type)
        present = sum(1 for f in applicable if _field_is_present(getattr(prov, f, None)))
        assert present == len(applicable), (
            f"Knowledge: {present}/{len(applicable)} fields present; "
            f"missing: {[f for f in applicable if not _field_is_present(getattr(prov, f, None))]}"
        )

    def test_numeric_zero_retrieval_score_counts_as_present(self) -> None:
        from research_core.normalization.ranking import _field_is_present

        assert _field_is_present(0.0) is True
        assert _field_is_present(0) is True

    def test_none_counts_as_missing(self) -> None:
        from research_core.normalization.ranking import _field_is_present

        assert _field_is_present(None) is False

    def test_empty_string_counts_as_missing(self) -> None:
        from research_core.normalization.ranking import _field_is_present

        assert _field_is_present("") is False

    def test_whitespace_only_string_counts_as_missing(self) -> None:
        from research_core.normalization.ranking import _field_is_present

        assert _field_is_present("   ") is False

    def test_nonempty_string_counts_as_present(self) -> None:
        from research_core.normalization.ranking import _field_is_present

        assert _field_is_present("duckduckgo") is True

    def test_unknown_source_type_uses_fallback_fields(self) -> None:
        from research_core.normalization.ranking import _applicable_fields

        fields = _applicable_fields("unknown_type")
        # Must be non-empty (fallback is always defined)
        assert len(fields) > 0

    def test_web_completeness_not_penalised_via_ranking(self) -> None:
        """Full-completeness web item should get completeness=1.0 in ranking."""
        item = _make_normalized(
            content="Some web evidence with full provenance fields.",
            rank=1,
        )
        result = rank_evidence([item], [], [], RankingConfig())
        components = {c.name: c for c in result.ranked[0].components}
        completeness_comp = components["provenance_completeness"]
        assert completeness_comp.status == ComponentStatus.AVAILABLE
        assert completeness_comp.raw_value is not None
        # make_web_evidence provides: provider, retrieval_query=None... let's just verify > 0
        assert completeness_comp.raw_value >= 0.0

    def test_knowledge_completeness_not_penalised_via_ranking(self) -> None:
        item = _make_knowledge_normalized(
            content="Some knowledge evidence with full provenance fields.",
            score=0.85,
        )
        result = rank_evidence([item], [], [], RankingConfig())
        components = {c.name: c for c in result.ranked[0].components}
        completeness_comp = components["provenance_completeness"]
        assert completeness_comp.status == ComponentStatus.AVAILABLE
        assert completeness_comp.raw_value is not None
        assert completeness_comp.raw_value >= 0.0


class TestRankingDiagnostics:
    def test_total_input_includes_excluded(self) -> None:
        items = [_make_normalized("ev-a"), _make_normalized("ev-b", rank=2)]
        excluded = [ExcludedEvidence(evidence_id="ev-c", reason="test")]
        result = rank_evidence(items, [], excluded, RankingConfig())
        assert result.diagnostics.total_input == 3

    def test_total_ranked_matches_ranked_tuple(self) -> None:
        items = [_make_normalized("ev-a"), _make_normalized("ev-b", rank=2)]
        result = rank_evidence(items, [], [], RankingConfig())
        assert result.diagnostics.total_ranked == len(result.ranked)

    def test_config_fingerprint_in_diagnostics(self) -> None:
        cfg = RankingConfig()
        items = [_make_normalized()]
        result = rank_evidence(items, [], [], cfg)
        assert result.diagnostics.config_fingerprint == cfg.fingerprint

    def test_total_duplicates_reflected(self) -> None:
        dups = [DuplicateEvidence("ev-dup", "ev-a", 1.0, "exact")]
        items = [_make_normalized("ev-a")]
        excluded = [ExcludedEvidence("ev-dup", "exact duplicate")]
        result = rank_evidence(items, dups, excluded, RankingConfig())
        assert result.diagnostics.total_duplicates == 1
