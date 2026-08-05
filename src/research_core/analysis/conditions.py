"""
Individual gap condition evaluators for DeterministicGapAnalyzer.

Each condition is a pure function that takes the analysis state and returns
either a ResearchGap or None. Conditions are provider-neutral and domain-neutral.

Nine required architecture gap conditions are implemented here, plus additional
diagnostics-layer conditions from the RC6 spec.

Gap type mapping (existing GapType values used):
  No sources            → GapType.NO_EVIDENCE / CRITICAL
  No evidence           → GapType.NO_EVIDENCE / CRITICAL
  Insufficient evidence → GapType.INSUFFICIENT_COVERAGE / HIGH
  Insufficient sources  → GapType.INSUFFICIENT_COVERAGE / HIGH
  No claims             → GapType.INSUFFICIENT_COVERAGE / MEDIUM
  Evidence without claims → GapType.INSUFFICIENT_COVERAGE / LOW
  Low claim coverage    → GapType.INSUFFICIENT_COVERAGE / MEDIUM
  Stale evidence        → GapType.STALE_EVIDENCE / MEDIUM
  Low extraction conf.  → GapType.LOW_EXTRACTION_CONFIDENCE / MEDIUM
  Source concentration  → GapType.INSUFFICIENT_COVERAGE / HIGH
  Provider concentration → GapType.INSUFFICIENT_COVERAGE / MEDIUM
  Low relevance         → GapType.INSUFFICIENT_COVERAGE / MEDIUM
  Low authority         → GapType.WEAK_AUTHORITY / HIGH
  Low provenance compl. → GapType.MISSING_DIMENSION / LOW
  Missing quality dim.  → GapType.MISSING_DIMENSION / LOW
  Duplicate conc.       → GapType.INSUFFICIENT_COVERAGE / MEDIUM
  Truncation            → GapType.INSUFFICIENT_COVERAGE / LOW
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from research_core.analysis.config import GapAnalysisConfig
from research_core.analysis.contracts import (
    CoverageDiagnostics,
    DiagnosticStatus,
    DistributionDiagnostics,
    EvidenceConditionDiagnostics,
    QualityDimensionSummary,
)
from research_core.claims.contracts import ExtractedClaim
from research_core.contracts.common import EMPTY_METADATA
from research_core.contracts.gaps import GapSeverity, GapStatus, GapType, ResearchGap
from research_core.contracts.sources import Source
from research_core.normalization.contracts import RankedEvidence


class ConditionStatus(StrEnum):
    """Internal status of a condition evaluation."""

    PASS = "pass"
    FAIL = "fail"
    INDETERMINATE = "indeterminate"
    UNAVAILABLE = "unavailable"


@dataclass
class ConditionResult:
    """Internal result for one evaluated condition."""

    condition_name: str
    status: ConditionStatus
    gap: ResearchGap | None  # only set when status == FAIL


def _make_gap_id(
    condition_name: str,
    gap_type: GapType,
    severity: GapSeverity,
    status: DiagnosticStatus,
    observed_value: float | None,
    threshold_value: float | None,
    affected_source_ids: tuple[str, ...],
    affected_evidence_ids: tuple[str, ...],
    affected_claim_ids: tuple[str, ...],
    analyzer_version: str,
    config_fingerprint: str,
) -> str:
    """Return a deterministic SHA256-based gap ID.

    Formula (sorted canonical JSON → SHA-256 → first 20 hex chars):
      condition      — stable internal condition name (e.g. "no_sources")
      type           — GapType string value
      severity       — GapSeverity string value
      status         — DiagnosticStatus string value
      observed       — str(observed_value)
      threshold      — str(threshold_value)
      sources        — sorted list of affected source IDs
      evidence       — sorted list of affected evidence IDs
      claims         — sorted list of affected claim IDs
      version        — analyzer version string
      config         — configuration fingerprint

    Including condition_name prevents collisions when two distinct conditions
    emit a gap with otherwise identical structural parameters.
    """
    payload = {
        "condition": condition_name,
        "type": str(gap_type),
        "severity": str(severity),
        "status": str(status),
        "observed": str(observed_value),
        "threshold": str(threshold_value),
        "sources": sorted(affected_source_ids),
        "evidence": sorted(affected_evidence_ids),
        "claims": sorted(affected_claim_ids),
        "version": analyzer_version,
        "config": config_fingerprint,
    }
    key = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "gap-" + hashlib.sha256(key.encode()).hexdigest()[:20]


def _make_gap(
    *,
    condition_name: str,
    gap_type: GapType,
    severity: GapSeverity,
    description: str,
    recommended_action: str = "",
    related_source_ids: tuple[str, ...] = (),
    related_evidence_ids: tuple[str, ...] = (),
    related_claim_ids: tuple[str, ...] = (),
    observed_value: float | None = None,
    threshold_value: float | None = None,
    cfg: GapAnalysisConfig,
) -> ResearchGap:
    gap_id = _make_gap_id(
        condition_name=condition_name,
        gap_type=gap_type,
        severity=severity,
        status=DiagnosticStatus.FAIL,
        observed_value=observed_value,
        threshold_value=threshold_value,
        affected_source_ids=related_source_ids,
        affected_evidence_ids=related_evidence_ids,
        affected_claim_ids=related_claim_ids,
        analyzer_version=cfg.analyzer_version,
        config_fingerprint=cfg.fingerprint,
    )
    return ResearchGap(
        gap_id=gap_id,
        gap_type=gap_type,
        description=description,
        related_claim_ids=related_claim_ids,
        related_evidence_ids=related_evidence_ids,
        severity=severity,
        recommended_action=recommended_action,
        status=GapStatus.OPEN,
        condition=condition_name,
        metadata=EMPTY_METADATA,
    )


# ---------------------------------------------------------------------------
# Condition evaluators — architecture nine + additional
# ---------------------------------------------------------------------------


def cond_no_sources(
    sources: Sequence[Source],
    cfg: GapAnalysisConfig,
) -> ConditionResult:
    if not sources:
        gap = _make_gap(
            condition_name="no_sources",
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.CRITICAL,
            description="No source documents were loaded. Analysis cannot proceed.",
            recommended_action="Collect at least one source document.",
            observed_value=0.0,
            threshold_value=float(cfg.minimum_source_count),
            cfg=cfg,
        )
        return ConditionResult("no_sources", ConditionStatus.FAIL, gap)
    return ConditionResult("no_sources", ConditionStatus.PASS, None)


def cond_no_evidence(
    ranked_evidence: Sequence[RankedEvidence],
    cfg: GapAnalysisConfig,
) -> ConditionResult:
    if not ranked_evidence:
        gap = _make_gap(
            condition_name="no_evidence",
            gap_type=GapType.NO_EVIDENCE,
            severity=GapSeverity.CRITICAL,
            description="No usable evidence was retrieved. Quality cannot be assessed.",
            recommended_action="Retrieve evidence from one or more sources.",
            observed_value=0.0,
            threshold_value=float(cfg.minimum_evidence_count),
            cfg=cfg,
        )
        return ConditionResult("no_evidence", ConditionStatus.FAIL, gap)
    return ConditionResult("no_evidence", ConditionStatus.PASS, None)


def cond_insufficient_evidence(
    ranked_evidence: Sequence[RankedEvidence],
    cfg: GapAnalysisConfig,
) -> ConditionResult:
    count = len(ranked_evidence)
    if count >= cfg.minimum_evidence_count:
        return ConditionResult("insufficient_evidence", ConditionStatus.PASS, None)
    gap = _make_gap(
        condition_name="insufficient_evidence",
        gap_type=GapType.INSUFFICIENT_COVERAGE,
        severity=GapSeverity.HIGH,
        description=(
            f"Evidence count ({count}) is below the minimum threshold "
            f"({cfg.minimum_evidence_count})."
        ),
        recommended_action="Retrieve additional evidence items.",
        related_evidence_ids=tuple(
            sorted(r.normalized_evidence.evidence.evidence_id for r in ranked_evidence)
        ),
        observed_value=float(count),
        threshold_value=float(cfg.minimum_evidence_count),
        cfg=cfg,
    )
    return ConditionResult("insufficient_evidence", ConditionStatus.FAIL, gap)


def cond_insufficient_sources(
    sources: Sequence[Source],
    ranked_evidence: Sequence[RankedEvidence],
    cfg: GapAnalysisConfig,
) -> ConditionResult:
    # Only evaluate when evidence exists
    if not ranked_evidence:
        return ConditionResult("insufficient_sources", ConditionStatus.UNAVAILABLE, None)
    unique_sources = {r.normalized_evidence.source.source_id for r in ranked_evidence}
    count = len(unique_sources)
    if count >= cfg.minimum_source_count:
        return ConditionResult("insufficient_sources", ConditionStatus.PASS, None)
    gap = _make_gap(
        condition_name="insufficient_sources",
        gap_type=GapType.INSUFFICIENT_COVERAGE,
        severity=GapSeverity.HIGH,
        description=(
            f"Unique source count ({count}) is below the minimum threshold "
            f"({cfg.minimum_source_count})."
        ),
        recommended_action="Add evidence from additional independent sources.",
        related_source_ids=tuple(sorted(unique_sources)),
        observed_value=float(count),
        threshold_value=float(cfg.minimum_source_count),
        cfg=cfg,
    )
    return ConditionResult("insufficient_sources", ConditionStatus.FAIL, gap)


def cond_no_claims(
    ranked_evidence: Sequence[RankedEvidence],
    claims: Sequence[ExtractedClaim],
    cfg: GapAnalysisConfig,
) -> ConditionResult:
    if not ranked_evidence:
        return ConditionResult("no_claims", ConditionStatus.UNAVAILABLE, None)
    if claims:
        return ConditionResult("no_claims", ConditionStatus.PASS, None)
    evidence_ids = tuple(
        sorted(r.normalized_evidence.evidence.evidence_id for r in ranked_evidence)
    )
    gap = _make_gap(
        condition_name="no_claims",
        gap_type=GapType.INSUFFICIENT_COVERAGE,
        severity=GapSeverity.MEDIUM,
        description="Evidence was retrieved but no claims were extracted from it.",
        recommended_action="Review evidence content; run claim extraction.",
        related_evidence_ids=evidence_ids,
        observed_value=0.0,
        cfg=cfg,
    )
    return ConditionResult("no_claims", ConditionStatus.FAIL, gap)


def cond_evidence_without_claims(
    coverage: CoverageDiagnostics,
    ranked_evidence: Sequence[RankedEvidence],
    cfg: GapAnalysisConfig,
) -> ConditionResult:
    if coverage.evidence_count == 0 or coverage.claim_count == 0:
        return ConditionResult("evidence_without_claims", ConditionStatus.UNAVAILABLE, None)
    if coverage.evidence_without_claims == 0:
        return ConditionResult("evidence_without_claims", ConditionStatus.PASS, None)
    gap = _make_gap(
        condition_name="evidence_without_claims",
        gap_type=GapType.INSUFFICIENT_COVERAGE,
        severity=GapSeverity.LOW,
        description=(
            f"{coverage.evidence_without_claims} of {coverage.evidence_count} "
            "evidence items contributed no extracted claims."
        ),
        recommended_action="Review evidence items that yielded no claims.",
        observed_value=float(coverage.evidence_without_claims),
        cfg=cfg,
    )
    return ConditionResult("evidence_without_claims", ConditionStatus.FAIL, gap)


def cond_low_claim_coverage(
    coverage: CoverageDiagnostics,
    cfg: GapAnalysisConfig,
) -> ConditionResult:
    ratio = coverage.claim_coverage_ratio
    if ratio is None:
        return ConditionResult("low_claim_coverage", ConditionStatus.UNAVAILABLE, None)
    if ratio >= cfg.minimum_claim_coverage_ratio:
        return ConditionResult("low_claim_coverage", ConditionStatus.PASS, None)
    gap = _make_gap(
        condition_name="low_claim_coverage",
        gap_type=GapType.INSUFFICIENT_COVERAGE,
        severity=GapSeverity.MEDIUM,
        description=(
            f"Claim coverage ratio ({ratio:.2f}) is below the threshold "
            f"({cfg.minimum_claim_coverage_ratio:.2f}). "
            f"{coverage.claims_without_evidence} claims lack evidence lineage."
        ),
        recommended_action="Ensure claims reference known evidence items.",
        observed_value=ratio,
        threshold_value=cfg.minimum_claim_coverage_ratio,
        cfg=cfg,
    )
    return ConditionResult("low_claim_coverage", ConditionStatus.FAIL, gap)


def cond_stale_evidence(
    dimensions: tuple[QualityDimensionSummary, ...],
    ranked_evidence: Sequence[RankedEvidence],
    cfg: GapAnalysisConfig,
) -> ConditionResult:
    """Evaluate recency dimension — architecture condition 8."""
    recency_dim = next((d for d in dimensions if d.dimension == "recency"), None)
    if recency_dim is None or recency_dim.measured_count == 0:
        return ConditionResult("stale_evidence", ConditionStatus.UNAVAILABLE, None)
    if recency_dim.status == DiagnosticStatus.PASS:
        return ConditionResult("stale_evidence", ConditionStatus.PASS, None)
    mean = recency_dim.mean
    gap = _make_gap(
        condition_name="stale_evidence",
        gap_type=GapType.STALE_EVIDENCE,
        severity=GapSeverity.MEDIUM,
        description=(
            f"Mean recency score ({mean:.3f}) is below the threshold "
            f"({cfg.minimum_recency_score:.3f}). Evidence may be stale."
        ),
        recommended_action="Retrieve more recent evidence.",
        related_evidence_ids=recency_dim.affected_evidence_ids,
        observed_value=mean,
        threshold_value=cfg.minimum_recency_score,
        cfg=cfg,
    )
    return ConditionResult("stale_evidence", ConditionStatus.FAIL, gap)


def cond_low_extraction_confidence(
    dimensions: tuple[QualityDimensionSummary, ...],
    cfg: GapAnalysisConfig,
) -> ConditionResult:
    """Evaluate extraction confidence — architecture condition 9."""
    dim = next((d for d in dimensions if d.dimension == "extraction_confidence"), None)
    if dim is None or dim.measured_count == 0:
        return ConditionResult("low_extraction_confidence", ConditionStatus.UNAVAILABLE, None)
    if dim.status == DiagnosticStatus.PASS:
        return ConditionResult("low_extraction_confidence", ConditionStatus.PASS, None)
    mean = dim.mean
    gap = _make_gap(
        condition_name="low_extraction_confidence",
        gap_type=GapType.LOW_EXTRACTION_CONFIDENCE,
        severity=GapSeverity.MEDIUM,
        description=(
            f"Mean extraction confidence ({mean:.3f}) is below the threshold "
            f"({cfg.minimum_extraction_confidence_score:.3f})."
        ),
        recommended_action="Review extraction pipeline; add higher-confidence sources.",
        related_evidence_ids=dim.affected_evidence_ids,
        observed_value=mean,
        threshold_value=cfg.minimum_extraction_confidence_score,
        cfg=cfg,
    )
    return ConditionResult("low_extraction_confidence", ConditionStatus.FAIL, gap)


def cond_source_concentration(
    distribution: DistributionDiagnostics,
    cfg: GapAnalysisConfig,
) -> ConditionResult:
    share = distribution.largest_source_share
    if share is None:
        return ConditionResult("source_concentration", ConditionStatus.UNAVAILABLE, None)
    if share <= cfg.maximum_single_source_share:
        return ConditionResult("source_concentration", ConditionStatus.PASS, None)
    gap = _make_gap(
        condition_name="source_concentration",
        gap_type=GapType.INSUFFICIENT_COVERAGE,
        severity=GapSeverity.HIGH,
        description=(
            f"A single source accounts for {share:.1%} of evidence, exceeding the "
            f"maximum allowed concentration ({cfg.maximum_single_source_share:.1%})."
        ),
        recommended_action="Add evidence from additional independent sources.",
        observed_value=share,
        threshold_value=cfg.maximum_single_source_share,
        cfg=cfg,
    )
    return ConditionResult("source_concentration", ConditionStatus.FAIL, gap)


def cond_provider_concentration(
    distribution: DistributionDiagnostics,
    cfg: GapAnalysisConfig,
) -> ConditionResult:
    share = distribution.largest_provider_share
    if share is None:
        return ConditionResult("provider_concentration", ConditionStatus.UNAVAILABLE, None)
    if share <= cfg.maximum_single_provider_share:
        return ConditionResult("provider_concentration", ConditionStatus.PASS, None)
    gap = _make_gap(
        condition_name="provider_concentration",
        gap_type=GapType.INSUFFICIENT_COVERAGE,
        severity=GapSeverity.MEDIUM,
        description=(
            f"A single provider accounts for {share:.1%} of evidence, exceeding the "
            f"maximum allowed concentration ({cfg.maximum_single_provider_share:.1%})."
        ),
        recommended_action="Add evidence from another provider.",
        observed_value=share,
        threshold_value=cfg.maximum_single_provider_share,
        cfg=cfg,
    )
    return ConditionResult("provider_concentration", ConditionStatus.FAIL, gap)


def cond_low_relevance(
    dimensions: tuple[QualityDimensionSummary, ...],
    cfg: GapAnalysisConfig,
) -> ConditionResult:
    dim = next((d for d in dimensions if d.dimension == "relevance"), None)
    if dim is None or dim.measured_count == 0:
        return ConditionResult("low_relevance", ConditionStatus.UNAVAILABLE, None)
    if dim.status == DiagnosticStatus.PASS:
        return ConditionResult("low_relevance", ConditionStatus.PASS, None)
    mean = dim.mean
    gap = _make_gap(
        condition_name="low_relevance",
        gap_type=GapType.INSUFFICIENT_COVERAGE,
        severity=GapSeverity.MEDIUM,
        description=(
            f"Mean relevance score ({mean:.3f}) is below the threshold "
            f"({cfg.minimum_relevance_score:.3f})."
        ),
        recommended_action="Refine the retrieval query or add more relevant evidence.",
        related_evidence_ids=dim.affected_evidence_ids,
        observed_value=mean,
        threshold_value=cfg.minimum_relevance_score,
        cfg=cfg,
    )
    return ConditionResult("low_relevance", ConditionStatus.FAIL, gap)


def cond_low_authority(
    dimensions: tuple[QualityDimensionSummary, ...],
    cfg: GapAnalysisConfig,
) -> ConditionResult:
    dim = next((d for d in dimensions if d.dimension == "authority"), None)
    if dim is None or dim.measured_count == 0:
        return ConditionResult("low_authority", ConditionStatus.UNAVAILABLE, None)
    if dim.status == DiagnosticStatus.PASS:
        return ConditionResult("low_authority", ConditionStatus.PASS, None)
    mean = dim.mean
    gap = _make_gap(
        condition_name="low_authority",
        gap_type=GapType.WEAK_AUTHORITY,
        severity=GapSeverity.HIGH,
        description=(
            f"Mean authority score ({mean:.3f}) is below the threshold "
            f"({cfg.minimum_authority_score:.3f}). "
            "Note: authority is based solely on explicit scores — not inferred from source names."
        ),
        recommended_action="Add evidence with higher explicit authority scores.",
        related_evidence_ids=dim.affected_evidence_ids,
        observed_value=mean,
        threshold_value=cfg.minimum_authority_score,
        cfg=cfg,
    )
    return ConditionResult("low_authority", ConditionStatus.FAIL, gap)


def cond_low_provenance_completeness(
    dimensions: tuple[QualityDimensionSummary, ...],
    cfg: GapAnalysisConfig,
) -> ConditionResult:
    dim = next((d for d in dimensions if d.dimension == "provenance_completeness"), None)
    if dim is None or dim.measured_count == 0:
        return ConditionResult(
            "low_provenance_completeness", ConditionStatus.UNAVAILABLE, None
        )
    if dim.status == DiagnosticStatus.PASS:
        return ConditionResult("low_provenance_completeness", ConditionStatus.PASS, None)
    mean = dim.mean
    gap = _make_gap(
        condition_name="low_provenance_completeness",
        gap_type=GapType.MISSING_DIMENSION,
        severity=GapSeverity.LOW,
        description=(
            f"Mean provenance completeness ({mean:.3f}) is below the threshold "
            f"({cfg.minimum_provenance_completeness_score:.3f}). "
            "Evidence items are missing retrieval metadata fields."
        ),
        recommended_action="Ensure evidence has complete provenance metadata.",
        related_evidence_ids=dim.affected_evidence_ids,
        observed_value=mean,
        threshold_value=cfg.minimum_provenance_completeness_score,
        cfg=cfg,
    )
    return ConditionResult("low_provenance_completeness", ConditionStatus.FAIL, gap)


def cond_missing_quality_dimension(
    dimensions: tuple[QualityDimensionSummary, ...],
    ranked_evidence: Sequence[RankedEvidence],
    cfg: GapAnalysisConfig,
) -> ConditionResult:
    """Fire when quality coverage is too low for any mandatory dimension."""
    if not ranked_evidence:
        return ConditionResult("missing_quality_dimension", ConditionStatus.UNAVAILABLE, None)
    total = len(ranked_evidence)
    gaps_emitted: list[ResearchGap] = []

    for dim in dimensions:
        coverage_ratio = dim.measured_count / total if total > 0 else 0.0
        if coverage_ratio < cfg.minimum_quality_coverage_ratio and dim.missing_count > 0:
            gap = _make_gap(
                condition_name="missing_quality_dimension",
                gap_type=GapType.MISSING_DIMENSION,
                severity=GapSeverity.LOW,
                description=(
                    f"Quality dimension '{dim.dimension}' is available for only "
                    f"{dim.measured_count}/{total} evidence items "
                    f"({coverage_ratio:.1%} < required {cfg.minimum_quality_coverage_ratio:.1%})."
                ),
                recommended_action=(
                    f"Add explicit {dim.dimension} scores to more evidence items."
                ),
                observed_value=coverage_ratio,
                threshold_value=cfg.minimum_quality_coverage_ratio,
                cfg=cfg,
            )
            gaps_emitted.append(gap)

    if not gaps_emitted:
        return ConditionResult("missing_quality_dimension", ConditionStatus.PASS, None)
    # Return the first gap; others are surfaced in future as multi-gap conditions
    return ConditionResult("missing_quality_dimension", ConditionStatus.FAIL, gaps_emitted[0])


def cond_duplicate_concentration(
    ev_conditions: EvidenceConditionDiagnostics,
    ranked_evidence: Sequence[RankedEvidence],
    cfg: GapAnalysisConfig,
) -> ConditionResult:
    if not ranked_evidence:
        return ConditionResult("duplicate_concentration", ConditionStatus.UNAVAILABLE, None)
    total = len(ranked_evidence)
    dup_count = ev_conditions.duplicate_evidence_count
    share = dup_count / total if total > 0 else 0.0
    if share <= cfg.maximum_duplicate_share:
        return ConditionResult("duplicate_concentration", ConditionStatus.PASS, None)
    gap = _make_gap(
        condition_name="duplicate_concentration",
        gap_type=GapType.INSUFFICIENT_COVERAGE,
        severity=GapSeverity.MEDIUM,
        description=(
            f"Duplicate evidence concentration ({share:.1%}) exceeds the threshold "
            f"({cfg.maximum_duplicate_share:.1%}). "
            f"{dup_count} of {total} evidence items were flagged as duplicates."
        ),
        recommended_action="Remove or deduplicate evidence before analysis.",
        observed_value=share,
        threshold_value=cfg.maximum_duplicate_share,
        cfg=cfg,
    )
    return ConditionResult("duplicate_concentration", ConditionStatus.FAIL, gap)


def cond_truncation(
    ev_conditions: EvidenceConditionDiagnostics,
    ranked_evidence: Sequence[RankedEvidence],
    cfg: GapAnalysisConfig,
) -> ConditionResult:
    if not ranked_evidence:
        return ConditionResult("truncation", ConditionStatus.UNAVAILABLE, None)
    total = len(ranked_evidence)
    trunc_count = ev_conditions.truncated_evidence_count
    share = trunc_count / total if total > 0 else 0.0
    if share <= cfg.maximum_truncated_share:
        return ConditionResult("truncation", ConditionStatus.PASS, None)
    gap = _make_gap(
        condition_name="truncation",
        gap_type=GapType.INSUFFICIENT_COVERAGE,
        severity=GapSeverity.LOW,
        description=(
            f"Truncated evidence concentration ({share:.1%}) exceeds the threshold "
            f"({cfg.maximum_truncated_share:.1%}). "
            f"{trunc_count} of {total} evidence items were truncated."
        ),
        recommended_action="Review truncated source content for completeness.",
        observed_value=share,
        threshold_value=cfg.maximum_truncated_share,
        cfg=cfg,
    )
    return ConditionResult("truncation", ConditionStatus.FAIL, gap)


def evaluate_all_conditions(
    sources: Sequence[Source],
    ranked_evidence: Sequence[RankedEvidence],
    claims: Sequence[ExtractedClaim],
    coverage: CoverageDiagnostics,
    distribution: DistributionDiagnostics,
    ev_conditions: EvidenceConditionDiagnostics,
    dimensions: tuple[QualityDimensionSummary, ...],
    cfg: GapAnalysisConfig,
) -> list[ConditionResult]:
    """Evaluate all conditions deterministically and return results."""
    return [
        cond_no_sources(sources, cfg),
        cond_no_evidence(ranked_evidence, cfg),
        cond_insufficient_evidence(ranked_evidence, cfg),
        cond_insufficient_sources(sources, ranked_evidence, cfg),
        cond_no_claims(ranked_evidence, claims, cfg),
        cond_evidence_without_claims(coverage, ranked_evidence, cfg),
        cond_low_claim_coverage(coverage, cfg),
        cond_stale_evidence(dimensions, ranked_evidence, cfg),
        cond_low_extraction_confidence(dimensions, cfg),
        cond_source_concentration(distribution, cfg),
        cond_provider_concentration(distribution, cfg),
        cond_low_relevance(dimensions, cfg),
        cond_low_authority(dimensions, cfg),
        cond_low_provenance_completeness(dimensions, cfg),
        cond_missing_quality_dimension(dimensions, ranked_evidence, cfg),
        cond_duplicate_concentration(ev_conditions, ranked_evidence, cfg),
        cond_truncation(ev_conditions, ranked_evidence, cfg),
    ]
