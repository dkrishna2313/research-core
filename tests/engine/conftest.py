"""
Shared fixtures and in-memory providers for engine tests.

All providers are deterministic, in-memory, and require no network or
external dependencies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from research_core.contracts.claims import Claim, ClaimType
from research_core.contracts.common import SourceType
from research_core.contracts.contradictions import Contradiction
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.gaps import OpenQuestion, ResearchGap
from research_core.contracts.request import ResearchRequest
from research_core.contracts.result import (
    SynthesisResult,  # noqa: F401 (used by FailingSynthesizer type annotation)
)
from research_core.contracts.sources import EvidenceQuality, Provenance, Source
from research_core.protocols.knowledge import (
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResult,
)
from research_core.protocols.profiles import ResolvedProfile
from research_core.protocols.web import WebSearchRequest, WebSearchResult

FIXED_TS = datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)


def fixed_clock() -> datetime:
    return FIXED_TS


def make_source(source_id: str = "src-1", source_type: SourceType = SourceType.KNOWLEDGE) -> Source:
    return Source(
        source_id=source_id,
        source_type=source_type,
        title=f"Test Source {source_id}",
    )


def make_provenance(
    source_id: str = "src-1", source_type: SourceType = SourceType.KNOWLEDGE
) -> Provenance:
    return Provenance(
        source_id=source_id,
        source_type=source_type,
        retrieved_at=FIXED_TS,
    )


def make_evidence(
    evidence_id: str = "ev-1",
    source_id: str = "src-1",
    content: str = "Climate change significantly affects biodiversity.",
    source_type: SourceType = SourceType.KNOWLEDGE,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        content=content,
        source_id=source_id,
        provenance=make_provenance(source_id=source_id, source_type=source_type),
        quality=EvidenceQuality(relevance=0.8, authority=0.7, recency=0.9),
    )


class FixedKnowledgeProvider:
    """Returns a fixed set of sources and evidence. No network required."""

    def __init__(self, sources: tuple[Source, ...], evidence: tuple[EvidenceItem, ...]) -> None:
        self._sources = sources
        self._evidence = evidence

    def retrieve(self, request: KnowledgeRetrievalRequest) -> KnowledgeRetrievalResult:
        return KnowledgeRetrievalResult(sources=self._sources, evidence=self._evidence)


class EmptyKnowledgeProvider:
    """Returns empty results. Used to test empty-evidence behavior."""

    def retrieve(self, request: KnowledgeRetrievalRequest) -> KnowledgeRetrievalResult:
        return KnowledgeRetrievalResult(sources=(), evidence=())


class FailingKnowledgeProvider:
    """Raises ProviderExecutionError on every call."""

    def retrieve(self, request: KnowledgeRetrievalRequest) -> KnowledgeRetrievalResult:
        from research_core.exceptions import ProviderExecutionError
        raise ProviderExecutionError("Knowledge provider intentionally failed.")


class FixedWebProvider:
    """Returns a fixed set of web sources and evidence."""

    def __init__(self, sources: tuple[Source, ...], evidence: tuple[EvidenceItem, ...]) -> None:
        self._sources = sources
        self._evidence = evidence

    def search(self, request: WebSearchRequest) -> WebSearchResult:
        return WebSearchResult(sources=self._sources, evidence=self._evidence)


class FailingWebProvider:
    """Raises on every call."""

    def search(self, request: WebSearchRequest) -> WebSearchResult:
        from research_core.exceptions import ProviderExecutionError
        raise ProviderExecutionError("Web provider intentionally failed.")


class FixedProfileProvider:
    """Resolves profile IDs from a supplied mapping."""

    def __init__(self, profiles: dict[str, str] | None = None) -> None:
        self._profiles = profiles or {"default": "Default profile"}

    def resolve(self, profile_id: str) -> ResolvedProfile:
        from research_core.exceptions import UnknownProfileError
        if profile_id not in self._profiles:
            raise UnknownProfileError(profile_id)
        return ResolvedProfile(
            profile_id=profile_id,
            display_name=self._profiles[profile_id],
        )

    def resolve_many(self, profile_ids: tuple[str, ...]) -> tuple[ResolvedProfile, ...]:
        return tuple(self.resolve(pid) for pid in profile_ids)


class SimpleCLaimExtractor:
    """Extracts one claim per evidence item."""

    def extract(
        self, evidence: tuple[EvidenceItem, ...], request: Any
    ) -> tuple[Claim, ...]:
        return tuple(
            Claim(
                claim_id=f"cl-{ev.evidence_id}",
                statement=ev.content,
                claim_type=ClaimType.FACTUAL,
                supporting_evidence_ids=(ev.evidence_id,),
            )
            for ev in evidence
        )


class FailingClaimExtractor:
    """Raises on every call."""

    def extract(
        self, evidence: tuple[EvidenceItem, ...], request: Any
    ) -> tuple[Claim, ...]:
        raise RuntimeError("Claim extraction intentionally failed.")


class SimpleGapAnalyzer:
    """Returns a fixed gap referencing no specific claims or evidence."""

    def analyze(
        self,
        claims: tuple[Claim, ...],
        evidence: tuple[EvidenceItem, ...],
        contradictions: tuple[Contradiction, ...],
        request: Any,
    ) -> tuple[tuple[ResearchGap, ...], tuple[OpenQuestion, ...]]:
        from research_core.contracts.gaps import GapSeverity, GapStatus, GapType
        gaps = (
            ResearchGap(
                gap_id="gap-test-001",
                gap_type=GapType.INSUFFICIENT_COVERAGE,
                description="Insufficient coverage from available sources.",
                severity=GapSeverity.MEDIUM,
                status=GapStatus.OPEN,
            ),
        )
        return gaps, ()


class FailingGapAnalyzer:
    """Raises on every call."""

    def analyze(
        self,
        claims: tuple[Claim, ...],
        evidence: tuple[EvidenceItem, ...],
        contradictions: tuple[Contradiction, ...],
        request: Any,
    ) -> tuple[tuple[ResearchGap, ...], tuple[OpenQuestion, ...]]:
        raise RuntimeError("Gap analysis intentionally failed.")


class FailingSynthesizer:
    """Raises on every call — used to test synthesis-failure partial-result behavior."""

    def synthesize(self, inputs: Any, *, config: Any = None) -> SynthesisResult:
        raise RuntimeError("Synthesis intentionally failed.")


@pytest.fixture
def fixed_ts() -> datetime:
    return FIXED_TS


@pytest.fixture
def simple_request() -> ResearchRequest:
    return ResearchRequest(question="What is the impact of climate change on biodiversity?")


@pytest.fixture
def knowledge_src() -> Source:
    return make_source("src-k1", SourceType.KNOWLEDGE)


@pytest.fixture
def knowledge_ev(knowledge_src: Source) -> EvidenceItem:
    return make_evidence("ev-k1", "src-k1")


@pytest.fixture
def fixed_knowledge_provider(
    knowledge_src: Source, knowledge_ev: EvidenceItem
) -> FixedKnowledgeProvider:
    return FixedKnowledgeProvider(
        sources=(knowledge_src,),
        evidence=(knowledge_ev,),
    )
