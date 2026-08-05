"""
Shared fixtures for diagnostics (RC6 gap analysis) tests.

Provides factory helpers to build Sources, RankedEvidence, and ExtractedClaims
without requiring real adapters or network access.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from research_core.analysis.config import GapAnalysisConfig
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


def make_quality(**kwargs: Any) -> EvidenceQuality:
    return EvidenceQuality(**kwargs)


def make_evidence(
    evidence_id: str = "ev-1",
    content: str = "Revenue increased by 12%.",
    source_id: str = "src-1",
    quality_kwargs: dict[str, Any] | None = None,
    **kwargs: Any,
) -> EvidenceItem:
    defaults: dict[str, Any] = {
        "evidence_id": evidence_id,
        "content": content,
        "source_id": source_id,
        "provenance": make_provenance(source_id=source_id),
        "quality": make_quality(**(quality_kwargs or {})),
    }
    defaults.update(kwargs)
    return EvidenceItem(**defaults)


def make_provenance_completeness_component(value: float | None) -> RankingComponent:
    return RankingComponent(
        name="provenance_completeness",
        status=ComponentStatus.AVAILABLE if value is not None else ComponentStatus.MISSING,
        raw_value=value,
        normalized_value=value,
        weight_used=0.0,
    )


def make_ranked_evidence(
    evidence_id: str = "ev-1",
    content: str = "Revenue increased by 12%.",
    source_id: str = "src-1",
    source_type: SourceType = SourceType.KNOWLEDGE,
    rank: int = 1,
    score: float = 0.5,
    provider: str = "test-provider",
    provider_rank: int | None = 1,
    provider_score: float | None = None,
    parent_evidence_id: str | None = None,
    segment_index: int | None = None,
    provenance_completeness: float | None = None,
    quality_kwargs: dict[str, Any] | None = None,
    **kwargs: Any,
) -> RankedEvidence:
    source = make_source(source_id=source_id, source_type=source_type)
    evidence = make_evidence(
        evidence_id=evidence_id,
        content=content,
        source_id=source_id,
        quality_kwargs=quality_kwargs,
    )
    norm_ev = NormalizedEvidence(
        evidence=evidence,
        source=source,
        provider=provider,
        provider_rank=provider_rank,
        provider_score=provider_score,
        normalized_retrieval_signal=None,
        content_length=len(content),
        parent_evidence_id=parent_evidence_id,
        segment_index=segment_index,
    )
    components: tuple[RankingComponent, ...] = (
        make_provenance_completeness_component(provenance_completeness),
    )
    return RankedEvidence(
        normalized_evidence=norm_ev,
        rank=rank,
        score=score,
        components=components,
        **kwargs,
    )


def make_claim(
    claim_id: str = "clm-test1",
    claim_text: str = "Revenue increased by 12%.",
    source_id: str = "src-1",
    evidence_id: str = "ev-1",
    **kwargs: Any,
) -> ExtractedClaim:
    defaults: dict[str, Any] = {
        "claim_id": claim_id,
        "claim_text": claim_text,
        "normalized_text": claim_text.lower(),
        "claim_type": ClaimType.QUANTITATIVE,
        "modality": ClaimModality.ASSERTED,
        "polarity": ClaimPolarity.POSITIVE,
        "scope": ClaimScope(),
        "qualifiers": (),
        "quantitative_expressions": (),
        "temporal_expressions": (),
        "attribution": None,
        "source_id": source_id,
        "evidence_id": evidence_id,
        "parent_evidence_id": None,
        "segment_index": None,
        "evidence_start_char": 0,
        "evidence_end_char": len(claim_text),
        "sentence_index": 0,
        "clause_index": 0,
        "extractor": "DeterministicClaimExtractor",
        "extractor_version": "1",
    }
    defaults.update(kwargs)
    return ExtractedClaim(**defaults)


@pytest.fixture
def default_config() -> GapAnalysisConfig:
    return GapAnalysisConfig()


@pytest.fixture
def single_source() -> Source:
    return make_source()


@pytest.fixture
def single_ranked_evidence() -> RankedEvidence:
    return make_ranked_evidence()


@pytest.fixture
def two_ranked_evidence() -> list[RankedEvidence]:
    return [
        make_ranked_evidence(evidence_id="ev-1", rank=1),
        make_ranked_evidence(evidence_id="ev-2", rank=2),
    ]


@pytest.fixture
def single_claim() -> ExtractedClaim:
    return make_claim()
