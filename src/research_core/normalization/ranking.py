"""
Evidence ranking — compute composite scores and assign final ranks.

Scoring uses six components with configurable weights. Missing values (None)
are handled by "proportional" reweighting: available weights renormalize to
sum to 1.0 among themselves; missing components contribute 0 and are excluded
from the denominator. Real 0.0 values ARE included.

Tie-breaking is fully deterministic:
  score DESC → retrieval_signal DESC (None=-inf) → rank ASC (None=+inf) →
  source_id ASC → evidence_id ASC → segment_index ASC (None=-1)
"""

from __future__ import annotations

from research_core.normalization.config import RankingConfig
from research_core.normalization.contracts import (
    ComponentStatus,
    DuplicateEvidence,
    EvidenceRankingResult,
    ExcludedEvidence,
    NormalizedEvidence,
    RankedEvidence,
    RankingComponent,
    RankingDiagnostics,
)

_DEFAULT_CONFIG = RankingConfig()

# Fields counted for provenance completeness
_PROVENANCE_FIELDS = (
    "provider",
    "retrieval_query",
    "retrieval_rank",
    "retrieval_score",
    "extraction_method",
    "extraction_confidence",
    "content_hash",
    "url",
    "document_id",
)
_NUM_PROVENANCE_FIELDS = len(_PROVENANCE_FIELDS)


def rank_evidence(
    items: list[NormalizedEvidence],
    duplicates: list[DuplicateEvidence],
    excluded: list[ExcludedEvidence],
    config: RankingConfig | None = None,
) -> EvidenceRankingResult:
    """Score and rank evidence items.

    items should already have duplicates removed (call detect_duplicates first).
    duplicates and excluded are carried through into diagnostics.
    """
    cfg = config or _DEFAULT_CONFIG
    w = cfg.weights

    # Six component definitions: (name, base_weight, extractor)
    components_def = [
        ("retrieval", w.retrieval),
        ("relevance", w.relevance),
        ("authority", w.authority),
        ("recency", w.recency),
        ("extraction_confidence", w.extraction_confidence),
        ("provenance_completeness", w.provenance_completeness),
    ]

    scored: list[tuple[NormalizedEvidence, float, tuple[RankingComponent, ...]]] = []

    for item in items:
        raw_values = _extract_raw_values(item)
        score, components = _compute_score(raw_values, components_def)
        scored.append((item, score, components))

    # Sort with deterministic tie-breaking
    scored.sort(key=lambda t: _sort_key(t[0], t[1]))

    ranked_list: list[RankedEvidence] = []
    for rank_idx, (item, score, components) in enumerate(scored):
        ranked_list.append(
            RankedEvidence(
                normalized_evidence=item,
                rank=rank_idx + 1,
                score=score,
                components=components,
            )
        )

    diagnostics = RankingDiagnostics(
        total_input=len(items) + len(excluded),
        total_ranked=len(ranked_list),
        total_excluded=len(excluded),
        total_duplicates=len(duplicates),
        config_fingerprint=cfg.fingerprint,
    )

    return EvidenceRankingResult(
        ranked=tuple(ranked_list),
        excluded=tuple(excluded),
        duplicates=tuple(duplicates),
        diagnostics=diagnostics,
    )


def _extract_raw_values(item: NormalizedEvidence) -> dict[str, float | None]:
    prov = item.evidence.provenance
    quality = item.evidence.quality

    completeness_count = sum(
        1 for f in _PROVENANCE_FIELDS if getattr(prov, f, None) is not None
    )
    completeness = completeness_count / _NUM_PROVENANCE_FIELDS

    return {
        "retrieval": item.normalized_retrieval_signal,
        "relevance": quality.relevance,
        "authority": quality.authority,
        "recency": quality.recency,
        "extraction_confidence": prov.extraction_confidence,
        "provenance_completeness": completeness,
    }


def _compute_score(
    raw_values: dict[str, float | None],
    components_def: list[tuple[str, float]],
) -> tuple[float, tuple[RankingComponent, ...]]:
    """Compute composite score using proportional reweighting for missing values."""
    available: list[tuple[str, float, float]] = []
    missing_names: set[str] = set()

    for name, base_weight in components_def:
        val = raw_values.get(name)
        if val is not None:
            available.append((name, val, base_weight))
        else:
            missing_names.add(name)

    total_available_weight = sum(w for _, _, w in available)

    components: list[RankingComponent] = []

    if total_available_weight <= 0.0:
        score = 0.0
        for name, _base_weight in components_def:
            components.append(
                RankingComponent(
                    name=name,
                    status=ComponentStatus.MISSING,
                    raw_value=None,
                    normalized_value=None,
                    weight_used=0.0,
                )
            )
        return score, tuple(components)

    score = 0.0
    for name, base_weight in components_def:
        val = raw_values.get(name)
        if val is not None:
            reweighted = base_weight / total_available_weight
            score += val * reweighted
            components.append(
                RankingComponent(
                    name=name,
                    status=ComponentStatus.AVAILABLE,
                    raw_value=val,
                    normalized_value=val,
                    weight_used=reweighted,
                )
            )
        else:
            components.append(
                RankingComponent(
                    name=name,
                    status=ComponentStatus.MISSING,
                    raw_value=None,
                    normalized_value=None,
                    weight_used=0.0,
                )
            )

    return score, tuple(components)


def _sort_key(item: NormalizedEvidence, score: float) -> tuple[float, float, int, str, str, int]:
    retrieval_signal = (
        item.normalized_retrieval_signal
        if item.normalized_retrieval_signal is not None
        else float("-inf")
    )
    rank = item.provider_rank if item.provider_rank is not None else 999999
    seg_idx = item.segment_index if item.segment_index is not None else -1
    return (
        -score,
        -retrieval_signal,
        rank,
        item.source.source_id,
        item.evidence.evidence_id,
        seg_idx,
    )
