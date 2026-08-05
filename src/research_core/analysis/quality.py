"""
Quality dimension scoring for the gap analysis layer.

Each dimension is scored independently from available explicit values.
None signals "unavailable / not assessed" — never coerced to 0.0.

Supported dimensions (from QualityDiagnostics and EvidenceQuality):
  relevance              — EvidenceQuality.relevance
  authority              — EvidenceQuality.authority
  recency                — EvidenceQuality.recency
  extraction_confidence  — EvidenceQuality.extraction_confidence
  provenance_completeness — RankedEvidence.components["provenance_completeness"].raw_value

Dimensions unavailable in RC6 (require future phases):
  corroboration, independence, contradiction_severity, uncertainty, reproducibility
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence

from research_core.analysis.config import GapAnalysisConfig
from research_core.analysis.contracts import (
    CoverageDiagnostics,
    DiagnosticStatus,
    QualityDimensionSummary,
)
from research_core.contracts.common import EMPTY_METADATA
from research_core.normalization.contracts import RankedEvidence

# Ordered list of dimensions scored in RC6
SCORED_DIMENSIONS: tuple[str, ...] = (
    "relevance",
    "authority",
    "recency",
    "extraction_confidence",
    "provenance_completeness",
)


def score_all_dimensions(
    ranked_evidence: Sequence[RankedEvidence],
    coverage: CoverageDiagnostics,
    cfg: GapAnalysisConfig,
) -> tuple[QualityDimensionSummary, ...]:
    """Score all supported quality dimensions.

    Returns a tuple in a fixed deterministic order.
    """
    thresholds: dict[str, float] = {
        "relevance": cfg.minimum_relevance_score,
        "authority": cfg.minimum_authority_score,
        "recency": cfg.minimum_recency_score,
        "extraction_confidence": cfg.minimum_extraction_confidence_score,
        "provenance_completeness": cfg.minimum_provenance_completeness_score,
    }

    results: list[QualityDimensionSummary] = []
    for dim in SCORED_DIMENSIONS:
        values = _collect_values(ranked_evidence, dim)
        threshold = thresholds.get(dim)
        results.append(_score_dimension(dim, values, threshold))

    return tuple(results)


def _collect_values(
    ranked_evidence: Sequence[RankedEvidence],
    dimension: str,
) -> list[tuple[str, float | None]]:
    """Return [(evidence_id, score_or_None), ...] for the requested dimension."""
    result: list[tuple[str, float | None]] = []
    for item in ranked_evidence:
        ev = item.normalized_evidence.evidence
        eid = ev.evidence_id
        if dimension == "relevance":
            score: float | None = ev.quality.relevance
        elif dimension == "authority":
            score = ev.quality.authority
        elif dimension == "recency":
            score = ev.quality.recency
        elif dimension == "extraction_confidence":
            score = ev.quality.extraction_confidence
        elif dimension == "provenance_completeness":
            score = next(
                (
                    c.raw_value
                    for c in item.components
                    if c.name == "provenance_completeness"
                ),
                None,
            )
        else:
            score = None
        result.append((eid, score))
    return result


def _score_dimension(
    dimension: str,
    values: list[tuple[str, float | None]],
    threshold: float | None,
) -> QualityDimensionSummary:
    """Compute summary statistics for one dimension."""
    measured: list[tuple[str, float]] = [(eid, s) for eid, s in values if s is not None]
    missing_count = len(values) - len(measured)

    if not measured:
        return QualityDimensionSummary(
            dimension=dimension,
            status=DiagnosticStatus.UNAVAILABLE,
            measured_count=0,
            missing_count=missing_count,
            minimum=None,
            maximum=None,
            mean=None,
            median=None,
            threshold=threshold,
            below_threshold_count=0,
            affected_evidence_ids=(),
            metadata=EMPTY_METADATA,
        )

    scores = [s for _, s in measured]
    mean_val = statistics.fmean(scores)
    median_val = statistics.median(scores)
    min_val = min(scores)
    max_val = max(scores)

    below_ids: list[str] = []
    if threshold is not None:
        below_ids = sorted(eid for eid, s in measured if s < threshold)

    if threshold is not None:
        status = DiagnosticStatus.PASS if mean_val >= threshold else DiagnosticStatus.FAIL
    else:
        status = DiagnosticStatus.PASS

    return QualityDimensionSummary(
        dimension=dimension,
        status=status,
        measured_count=len(measured),
        missing_count=missing_count,
        minimum=min_val,
        maximum=max_val,
        mean=mean_val,
        median=median_val,
        threshold=threshold,
        below_threshold_count=len(below_ids),
        affected_evidence_ids=tuple(below_ids),
        metadata=EMPTY_METADATA,
    )


def compute_overall_score(
    dimensions: tuple[QualityDimensionSummary, ...],
) -> float | None:
    """Compute an equal-weighted mean of available dimension means.

    Returns None when no dimension has any measured values.
    """
    measured_means = [d.mean for d in dimensions if d.mean is not None]
    if not measured_means:
        return None
    return statistics.fmean(measured_means)


def compute_overall_status(
    score: float | None,
    gaps: list[object],  # list[ResearchGap] — avoid circular
    evidence_count: int,
) -> DiagnosticStatus:
    """Determine overall quality status from score, gaps, and evidence count.

    Rules (highest priority first):
    1. No evidence → FAIL
    2. Any critical gap → FAIL
    3. No measured quality signal → INDETERMINATE
    4. score < any dimension threshold → FAIL
    5. Gaps present (non-critical) → INDETERMINATE
    6. All measured dimensions pass → PASS
    """
    from research_core.contracts.gaps import GapSeverity, ResearchGap

    if evidence_count == 0:
        return DiagnosticStatus.FAIL

    for gap in gaps:
        if isinstance(gap, ResearchGap) and gap.severity == GapSeverity.CRITICAL:
            return DiagnosticStatus.FAIL

    if score is None:
        return DiagnosticStatus.INDETERMINATE

    if gaps:
        return DiagnosticStatus.INDETERMINATE

    return DiagnosticStatus.PASS
