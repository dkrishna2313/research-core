"""
Shared fixtures for claim extraction tests.

Provides helpers to build NormalizedEvidence and RankedEvidence without
requiring real adapters or network access.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from research_core.claims.contracts import (
    ClaimModality,
    ClaimPolarity,
    ClaimScope,
    ClaimType,
    ExtractedClaim,
)
from research_core.contracts.common import SourceType
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.sources import EvidenceQuality, Provenance, Source
from research_core.normalization.contracts import (
    ComponentStatus,
    NormalizedEvidence,
    RankedEvidence,
    RankingComponent,
)

FIXED_TS = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)


def make_source(
    source_id: str = "src-1",
    source_type: SourceType = SourceType.KNOWLEDGE,
    **kwargs: Any,
) -> Source:
    return Source(source_id=source_id, source_type=source_type, **kwargs)


def make_provenance(
    source_id: str = "src-1",
    source_type: SourceType = SourceType.KNOWLEDGE,
    **kwargs: Any,
) -> Provenance:
    defaults: dict[str, Any] = {
        "source_id": source_id,
        "source_type": source_type,
        "retrieved_at": FIXED_TS,
    }
    defaults.update(kwargs)
    return Provenance(**defaults)


def make_evidence(
    evidence_id: str = "ev-1",
    content: str = "Revenue increased by 12%. The policy may reduce emissions.",
    source_id: str = "src-1",
    **kwargs: Any,
) -> EvidenceItem:
    defaults: dict[str, Any] = {
        "evidence_id": evidence_id,
        "content": content,
        "source_id": source_id,
        "provenance": make_provenance(source_id=source_id),
        "quality": EvidenceQuality(),
    }
    defaults.update(kwargs)
    return EvidenceItem(**defaults)


def make_normalized_evidence(
    evidence_id: str = "ev-1",
    content: str = "Revenue increased by 12%. The policy may reduce emissions.",
    source_id: str = "src-1",
    source_type: SourceType = SourceType.KNOWLEDGE,
    parent_evidence_id: str | None = None,
    segment_index: int | None = None,
    **kwargs: Any,
) -> NormalizedEvidence:
    source = make_source(source_id=source_id, source_type=source_type)
    evidence = make_evidence(evidence_id=evidence_id, content=content, source_id=source_id)
    defaults: dict[str, Any] = {
        "evidence": evidence,
        "source": source,
        "provider": "test-provider",
        "provider_rank": 1,
        "provider_score": None,
        "normalized_retrieval_signal": None,
        "content_length": len(content),
        "parent_evidence_id": parent_evidence_id,
        "segment_index": segment_index,
    }
    defaults.update(kwargs)
    return NormalizedEvidence(**defaults)


def make_ranking_components() -> tuple[RankingComponent, ...]:
    return (
        RankingComponent(
            name="retrieval",
            status=ComponentStatus.MISSING,
            raw_value=None,
            normalized_value=None,
            weight_used=0.0,
        ),
    )


def make_ranked_evidence(
    evidence_id: str = "ev-1",
    content: str = "Revenue increased by 12%. The policy may reduce emissions.",
    source_id: str = "src-1",
    source_type: SourceType = SourceType.KNOWLEDGE,
    rank: int = 1,
    score: float = 0.5,
    parent_evidence_id: str | None = None,
    segment_index: int | None = None,
    **kwargs: Any,
) -> RankedEvidence:
    norm_ev = make_normalized_evidence(
        evidence_id=evidence_id,
        content=content,
        source_id=source_id,
        source_type=source_type,
        parent_evidence_id=parent_evidence_id,
        segment_index=segment_index,
    )
    return RankedEvidence(
        normalized_evidence=norm_ev,
        rank=rank,
        score=score,
        components=make_ranking_components(),
        **kwargs,
    )


def make_extracted_claim(
    claim_id: str = "clm-abc123",
    claim_text: str = "Revenue increased by 12%.",
    normalized_text: str = "Revenue increased by 12%.",
    claim_type: ClaimType = ClaimType.QUANTITATIVE,
    modality: ClaimModality = ClaimModality.ASSERTED,
    polarity: ClaimPolarity = ClaimPolarity.POSITIVE,
    source_id: str = "src-1",
    evidence_id: str = "ev-1",
    evidence_start_char: int = 0,
    evidence_end_char: int = 25,
    sentence_index: int = 0,
    clause_index: int = 0,
    **kwargs: Any,
) -> ExtractedClaim:
    defaults: dict[str, Any] = {
        "claim_id": claim_id,
        "claim_text": claim_text,
        "normalized_text": normalized_text,
        "claim_type": claim_type,
        "modality": modality,
        "polarity": polarity,
        "scope": ClaimScope(),
        "qualifiers": (),
        "quantitative_expressions": (),
        "temporal_expressions": (),
        "attribution": None,
        "source_id": source_id,
        "evidence_id": evidence_id,
        "parent_evidence_id": None,
        "segment_index": None,
        "evidence_start_char": evidence_start_char,
        "evidence_end_char": evidence_end_char,
        "sentence_index": sentence_index,
        "clause_index": clause_index,
        "extractor": "DeterministicClaimExtractor",
        "extractor_version": "1",
    }
    defaults.update(kwargs)
    return ExtractedClaim(**defaults)
