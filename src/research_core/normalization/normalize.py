"""
Evidence normalization — produce NormalizedEvidence from raw sources and evidence.

Validates consistency, segments long items, and derives normalized retrieval signals.
"""

from __future__ import annotations

import math

from research_core.contracts.common import SourceType
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.sources import Source
from research_core.exceptions import ContractValidationError
from research_core.normalization.config import NormalizationConfig
from research_core.normalization.contracts import NormalizedEvidence
from research_core.normalization.segmenter import segment_evidence

_DEFAULT_CONFIG = NormalizationConfig()


def normalize_evidence(
    *,
    sources: tuple[Source, ...],
    evidence: tuple[EvidenceItem, ...],
    config: NormalizationConfig | None = None,
) -> tuple[NormalizedEvidence, ...]:
    """Normalize and segment evidence items.

    Validates:
    - All source_ids in sources are unique
    - All evidence_ids are unique
    - Every evidence item's source_id resolves to a source
    - provenance.source_id == evidence.source_id for each item

    Segments items whose content exceeds segmentation config max_characters.
    Derives normalized_retrieval_signal from provider score or rank position.
    """
    cfg = config or _DEFAULT_CONFIG

    # Validate unique source IDs
    source_by_id: dict[str, Source] = {}
    for src in sources:
        if src.source_id in source_by_id:
            raise ContractValidationError(
                f"Duplicate source_id {src.source_id!r} in sources"
            )
        source_by_id[src.source_id] = src

    # Validate unique evidence IDs and source resolution
    seen_evidence_ids: set[str] = set()
    for item in evidence:
        if item.evidence_id in seen_evidence_ids:
            raise ContractValidationError(
                f"Duplicate evidence_id {item.evidence_id!r} in evidence"
            )
        seen_evidence_ids.add(item.evidence_id)

        if item.source_id not in source_by_id:
            raise ContractValidationError(
                f"Evidence {item.evidence_id!r} references unknown source_id {item.source_id!r}"
            )
        if item.provenance.source_id != item.source_id:
            raise ContractValidationError(
                f"Evidence {item.evidence_id!r}: provenance.source_id "
                f"{item.provenance.source_id!r} != source_id {item.source_id!r}"
            )

    result: list[NormalizedEvidence] = []

    for item in evidence:
        segments = segment_evidence(item, cfg.segmentation)
        src = source_by_id[item.source_id]

        for seg_idx, seg in enumerate(segments):
            is_segmented = len(segments) > 1

            # Extract segment metadata set by segmenter
            segment_index: int | None = None
            segment_count: int | None = None
            parent_evidence_id: str | None = None
            if is_segmented:
                segment_index = int(seg.metadata.get("segment_index", seg_idx))
                segment_count = int(seg.metadata.get("segment_count", len(segments)))
                parent_evidence_id = str(seg.metadata.get("parent_evidence_id", item.evidence_id))

            provider = str(seg.provenance.source_type)
            provider_rank = seg.provenance.retrieval_rank
            provider_score = seg.provenance.retrieval_score

            normalized_retrieval_signal = _compute_retrieval_signal(
                provider=provider,
                provider_score=provider_score,
                provider_rank=provider_rank,
            )

            result.append(
                NormalizedEvidence(
                    evidence=seg,
                    source=src,
                    provider=provider,
                    provider_rank=provider_rank,
                    provider_score=provider_score,
                    normalized_retrieval_signal=normalized_retrieval_signal,
                    content_length=len(seg.content),
                    segment_index=segment_index,
                    segment_count=segment_count,
                    parent_evidence_id=parent_evidence_id,
                )
            )

    return tuple(result)


def _compute_retrieval_signal(
    *,
    provider: str,
    provider_score: float | None,
    provider_rank: int | None,
) -> float | None:
    if provider_score is not None:
        # Already [0,1] — use directly
        return provider_score

    if provider == str(SourceType.WEB) and provider_rank is not None:
        # Rank-position feature (not a provider score)
        return 1.0 / (1.0 + math.log2(provider_rank + 1))

    return None
