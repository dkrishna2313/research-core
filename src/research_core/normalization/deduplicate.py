"""
Evidence deduplication — detect and remove exact and near-duplicate evidence.

Exact dedup: SHA256 of NFC-normalized content.
Near-dup: Jaccard similarity on lowercased token sets (numeric tokens excluded).

Canonical item selection: best provenance completeness → lower rank →
source_id asc → evidence_id asc.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

from research_core.normalization.config import RankingConfig
from research_core.normalization.contracts import (
    DuplicateEvidence,
    ExcludedEvidence,
    NormalizedEvidence,
)

_DEFAULT_CONFIG = RankingConfig()

# Fields counted for provenance completeness scoring
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


def detect_duplicates(
    items: list[NormalizedEvidence],
    config: RankingConfig | None = None,
) -> tuple[list[NormalizedEvidence], list[DuplicateEvidence], list[ExcludedEvidence]]:
    """Detect exact and near-duplicate evidence items.

    Returns (kept_items, duplicate_records, excluded_records).
    kept_items contains only canonical items (no duplicates).
    """
    cfg = config or _DEFAULT_CONFIG

    kept, duplicates, excluded = _exact_dedup(items)
    kept, near_dups, near_excl = _near_dedup(kept, cfg)

    duplicates.extend(near_dups)
    excluded.extend(near_excl)

    return kept, duplicates, excluded


def _exact_dedup(
    items: list[NormalizedEvidence],
) -> tuple[list[NormalizedEvidence], list[DuplicateEvidence], list[ExcludedEvidence]]:
    """Remove exact duplicates, keeping the canonical item per content hash."""
    # Group items by content hash
    hash_groups: dict[str, list[NormalizedEvidence]] = {}
    for item in items:
        h = _content_hash(item.evidence.content)
        hash_groups.setdefault(h, []).append(item)

    kept: list[NormalizedEvidence] = []
    duplicates: list[DuplicateEvidence] = []
    excluded: list[ExcludedEvidence] = []

    for group in hash_groups.values():
        if len(group) == 1:
            kept.append(group[0])
            continue

        canonical = _select_canonical(group)
        kept.append(canonical)
        canonical_id = canonical.evidence.evidence_id

        for item in group:
            if item.evidence.evidence_id == canonical_id:
                continue
            duplicates.append(
                DuplicateEvidence(
                    evidence_id=item.evidence.evidence_id,
                    canonical_id=canonical_id,
                    similarity=1.0,
                    method="exact",
                )
            )
            excluded.append(
                ExcludedEvidence(
                    evidence_id=item.evidence.evidence_id,
                    reason=f"exact duplicate of {canonical_id!r}",
                )
            )

    return kept, duplicates, excluded


def _near_dedup(
    items: list[NormalizedEvidence],
    config: RankingConfig,
) -> tuple[list[NormalizedEvidence], list[DuplicateEvidence], list[ExcludedEvidence]]:
    """Remove near-duplicates above the Jaccard threshold."""
    duplicates: list[DuplicateEvidence] = []
    excluded: list[ExcludedEvidence] = []
    excluded_ids: set[str] = set()

    # Only compare items with sufficient content
    candidates = [i for i in items if i.content_length >= 200]
    skipped = [i for i in items if i.content_length < 200]

    # Precompute token sets
    token_sets: dict[str, frozenset[str]] = {
        item.evidence.evidence_id: _tokenize(item.evidence.content) for item in candidates
    }

    comparisons = 0
    comparisons_exhausted = False

    for i in range(len(candidates)):
        item_a = candidates[i]
        if item_a.evidence.evidence_id in excluded_ids:
            continue

        for j in range(i + 1, len(candidates)):
            if comparisons >= config.max_near_duplicate_comparisons:
                comparisons_exhausted = True
                break

            item_b = candidates[j]
            if item_b.evidence.evidence_id in excluded_ids:
                continue

            comparisons += 1
            jaccard = _jaccard(
                token_sets[item_a.evidence.evidence_id],
                token_sets[item_b.evidence.evidence_id],
            )

            if jaccard >= config.near_duplicate_threshold:
                canonical, duplicate = _select_canonical_pair(item_a, item_b)
                canonical_id = canonical.evidence.evidence_id
                dup_id = duplicate.evidence.evidence_id
                excluded_ids.add(dup_id)

                duplicates.append(
                    DuplicateEvidence(
                        evidence_id=dup_id,
                        canonical_id=canonical_id,
                        similarity=jaccard,
                        method="near_duplicate",
                    )
                )
                excluded.append(
                    ExcludedEvidence(
                        evidence_id=dup_id,
                        reason=f"near-duplicate of {canonical_id!r} (Jaccard={jaccard:.3f})",
                    )
                )

        if comparisons_exhausted:
            break

    kept = (
        [i for i in candidates if i.evidence.evidence_id not in excluded_ids]
        + skipped
    )

    return kept, duplicates, excluded


def _content_hash(content: str) -> str:
    normalized = unicodedata.normalize("NFC", content)
    return hashlib.sha256(normalized.encode()).hexdigest()


def _tokenize(content: str) -> frozenset[str]:
    """Lowercase word tokens, including numeric tokens.

    Numeric tokens are retained so that texts differing only in numeric values
    (e.g. '$10 million' vs '$100 million', '2024' vs '2025') produce distinct
    token sets and are not collapsed as near-duplicates.
    """
    tokens = re.findall(r"\b\w+\b", content.lower())
    return frozenset(tokens)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union > 0 else 0.0


def _provenance_completeness(item: NormalizedEvidence) -> int:
    """Count non-None provenance fields (higher = more complete)."""
    prov = item.evidence.provenance
    count = 0
    for field_name in _PROVENANCE_FIELDS:
        if getattr(prov, field_name, None) is not None:
            count += 1
    return count


def _select_canonical(group: list[NormalizedEvidence]) -> NormalizedEvidence:
    """Select the canonical item: best completeness → lowest rank → source_id → evidence_id."""

    def key(item: NormalizedEvidence) -> tuple[int, int, str, str]:
        completeness = _provenance_completeness(item)
        rank = item.provider_rank if item.provider_rank is not None else 999999
        return (-completeness, rank, item.source.source_id, item.evidence.evidence_id)

    return min(group, key=key)


def _select_canonical_pair(
    a: NormalizedEvidence, b: NormalizedEvidence
) -> tuple[NormalizedEvidence, NormalizedEvidence]:
    """Return (canonical, duplicate) for a near-duplicate pair."""
    a_comp = _provenance_completeness(a)
    b_comp = _provenance_completeness(b)

    if a_comp != b_comp:
        canonical, dup = (a, b) if a_comp > b_comp else (b, a)
    elif (a.provider_rank or 999999) != (b.provider_rank or 999999):
        canonical, dup = (
            (a, b) if (a.provider_rank or 999999) < (b.provider_rank or 999999) else (b, a)
        )
    elif a.source.source_id != b.source.source_id:
        canonical, dup = (a, b) if a.source.source_id < b.source.source_id else (b, a)
    else:
        canonical, dup = (
            (a, b)
            if a.evidence.evidence_id < b.evidence.evidence_id
            else (b, a)
        )

    return canonical, dup
