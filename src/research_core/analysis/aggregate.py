"""
Coverage and distribution aggregation helpers for the gap analyzer.

All functions are deterministic and pure — no side effects.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from research_core.analysis.contracts import (
    CoverageDiagnostics,
    DistributionDiagnostics,
    EvidenceConditionDiagnostics,
)
from research_core.claims.contracts import ExtractedClaim
from research_core.contracts.common import _to_proxy
from research_core.contracts.sources import Source
from research_core.normalization.contracts import EvidenceRankingResult, RankedEvidence


def compute_coverage(
    sources: Sequence[Source],
    ranked_evidence: Sequence[RankedEvidence],
    claims: Sequence[ExtractedClaim],
) -> CoverageDiagnostics:
    """Compute structural coverage of evidence, sources, and claims."""
    evidence_ids = {
        r.normalized_evidence.evidence.evidence_id for r in ranked_evidence
    }
    source_ids = {s.source_id for s in sources}

    # Claims that reference a known evidence item
    claims_with_evidence_set = {c.claim_id for c in claims if c.evidence_id in evidence_ids}

    # Evidence that has at least one claim pointing to it
    evidence_with_claims_set = {c.evidence_id for c in claims if c.evidence_id in evidence_ids}

    # Segmented evidence
    segmented_ids = {
        r.normalized_evidence.evidence.evidence_id
        for r in ranked_evidence
        if r.normalized_evidence.segment_index is not None
    }
    parent_ids = {
        r.normalized_evidence.parent_evidence_id
        for r in ranked_evidence
        if r.normalized_evidence.parent_evidence_id is not None
    }

    # Sources with at least one claim
    sources_with_claims_set = {c.source_id for c in claims if c.source_id in source_ids}

    ev_count = len(ranked_evidence)
    claim_count = len(claims)

    return CoverageDiagnostics(
        source_count=len(sources),
        evidence_count=ev_count,
        ranked_evidence_count=ev_count,
        claim_count=claim_count,
        claims_with_evidence=len(claims_with_evidence_set),
        claims_without_evidence=claim_count - len(claims_with_evidence_set),
        evidence_with_claims=len(evidence_with_claims_set),
        evidence_without_claims=ev_count - len(evidence_with_claims_set),
        unique_parent_evidence_count=len(parent_ids),
        segmented_evidence_count=len(segmented_ids),
        sources_with_claims=len(sources_with_claims_set),
        sources_without_claims=len(sources) - len(sources_with_claims_set),
        claim_coverage_ratio=(
            len(claims_with_evidence_set) / claim_count if claim_count > 0 else None
        ),
        evidence_utilization_ratio=(
            len(evidence_with_claims_set) / ev_count if ev_count > 0 else None
        ),
    )


def compute_distribution(
    ranked_evidence: Sequence[RankedEvidence],
) -> DistributionDiagnostics:
    """Compute source and provider distribution diagnostics."""
    ev_by_source: Counter[str] = Counter()
    ev_by_provider: Counter[str] = Counter()

    for item in ranked_evidence:
        ev_by_source[item.normalized_evidence.source.source_id] += 1
        ev_by_provider[item.normalized_evidence.provider] += 1

    total = len(ranked_evidence)

    largest_source_share: float | None
    largest_provider_share: float | None
    source_diversity: float | None
    provider_diversity: float | None

    if total > 0:
        _lss: float = max(ev_by_source.values()) / total
        _lps: float = max(ev_by_provider.values()) / total
        largest_source_share = _lss
        largest_provider_share = _lps
        source_diversity = 1.0 - _lss
        provider_diversity = 1.0 - _lps
    else:
        largest_source_share = None
        largest_provider_share = None
        source_diversity = None
        provider_diversity = None

    return DistributionDiagnostics(
        unique_source_count=len(ev_by_source),
        unique_provider_count=len(ev_by_provider),
        largest_source_share=largest_source_share,
        largest_provider_share=largest_provider_share,
        source_diversity_score=source_diversity,
        provider_diversity_score=provider_diversity,
        evidence_per_source=_to_proxy(dict(ev_by_source)),
        evidence_per_provider=_to_proxy(dict(ev_by_provider)),
    )


def compute_evidence_conditions(
    ranked_evidence: Sequence[RankedEvidence],
    ranking_result: EvidenceRankingResult | None,
) -> EvidenceConditionDiagnostics:
    """Compute low-level evidence state diagnostics."""
    truncated = 0
    missing_score = 0
    missing_rank = 0
    invalid_lineage = 0

    for item in ranked_evidence:
        norm_ev = item.normalized_evidence
        ev = norm_ev.evidence

        # Truncation: check metadata["truncated"]
        if ev.metadata.get("truncated") is True:
            truncated += 1

        # Provider score
        if norm_ev.provider_score is None:
            missing_score += 1

        # Provider rank
        if norm_ev.provider_rank is None:
            missing_rank += 1

        # Invalid lineage: segment_index set but parent_evidence_id absent, or vice versa
        has_idx = norm_ev.segment_index is not None
        has_parent = norm_ev.parent_evidence_id is not None
        if has_idx != has_parent:
            invalid_lineage += 1

    duplicate_count = len(ranking_result.duplicates) if ranking_result is not None else 0

    return EvidenceConditionDiagnostics(
        truncated_evidence_count=truncated,
        duplicate_evidence_count=duplicate_count,
        near_duplicate_evidence_count=0,
        missing_retrieval_score_count=missing_score,
        missing_retrieval_rank_count=missing_rank,
        invalid_lineage_count=invalid_lineage,
    )
