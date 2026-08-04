"""
Tests for protocol structural checking.

These tests verify that the protocols are runtime-checkable and that
properly-shaped objects satisfy isinstance() checks.
"""

from __future__ import annotations

from typing import Any

from research_core.contracts.claims import Claim
from research_core.contracts.contradictions import Contradiction
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.gaps import OpenQuestion, ResearchGap
from research_core.contracts.request import ResearchRequest
from research_core.contracts.result import ResearchResult, SynthesisResult
from research_core.protocols.analysis import ClaimExtractor, ContradictionDetector, GapAnalyzer
from research_core.protocols.knowledge import KnowledgeProvider, KnowledgeRetrievalRequest
from research_core.protocols.profiles import ProfileProvider, ResolvedProfile
from research_core.protocols.rendering import Renderer
from research_core.protocols.synthesis import Synthesizer
from research_core.protocols.web import WebSearchProvider, WebSearchRequest
from tests.conftest import (
    make_research_request,
    make_synthesis_result,
)


class _StubKnowledgeProvider:
    def retrieve(self, request: KnowledgeRetrievalRequest) -> tuple[EvidenceItem, ...]:
        return ()


class _StubWebSearchProvider:
    def search(
        self, request: WebSearchRequest
    ) -> tuple[tuple[Any, EvidenceItem], ...]:
        return ()


class _StubProfileProvider:
    def resolve(self, profile_id: str) -> ResolvedProfile:
        return ResolvedProfile(profile_id=profile_id)

    def resolve_many(self, profile_ids: tuple[str, ...]) -> tuple[ResolvedProfile, ...]:
        return tuple(self.resolve(pid) for pid in profile_ids)


class _StubClaimExtractor:
    def extract(
        self, evidence: tuple[EvidenceItem, ...], request: ResearchRequest
    ) -> tuple[Claim, ...]:
        return ()


class _StubContradictionDetector:
    def detect(
        self,
        claims: tuple[Claim, ...],
        evidence: tuple[EvidenceItem, ...],
        request: ResearchRequest,
    ) -> tuple[Contradiction, ...]:
        return ()


class _StubGapAnalyzer:
    def analyze(
        self,
        claims: tuple[Claim, ...],
        evidence: tuple[EvidenceItem, ...],
        contradictions: tuple[Contradiction, ...],
        request: ResearchRequest,
    ) -> tuple[tuple[ResearchGap, ...], tuple[OpenQuestion, ...]]:
        return (), ()


class _StubSynthesizer:
    def synthesize(
        self,
        request: ResearchRequest,
        evidence: tuple[EvidenceItem, ...],
        claims: tuple[Claim, ...],
        contradictions: tuple[Contradiction, ...],
        gaps: tuple[ResearchGap, ...],
        open_questions: tuple[OpenQuestion, ...],
    ) -> SynthesisResult:
        return make_synthesis_result()


class _StubRenderer:
    def render(self, result: ResearchResult) -> str:
        return "rendered"


class TestProtocolIsInstance:
    def test_knowledge_provider_isinstance(self) -> None:
        assert isinstance(_StubKnowledgeProvider(), KnowledgeProvider)

    def test_web_search_provider_isinstance(self) -> None:
        assert isinstance(_StubWebSearchProvider(), WebSearchProvider)

    def test_profile_provider_isinstance(self) -> None:
        assert isinstance(_StubProfileProvider(), ProfileProvider)

    def test_claim_extractor_isinstance(self) -> None:
        assert isinstance(_StubClaimExtractor(), ClaimExtractor)

    def test_contradiction_detector_isinstance(self) -> None:
        assert isinstance(_StubContradictionDetector(), ContradictionDetector)

    def test_gap_analyzer_isinstance(self) -> None:
        assert isinstance(_StubGapAnalyzer(), GapAnalyzer)

    def test_synthesizer_isinstance(self) -> None:
        assert isinstance(_StubSynthesizer(), Synthesizer)

    def test_renderer_isinstance(self) -> None:
        assert isinstance(_StubRenderer(), Renderer)


class TestProtocolMissingMethod:
    def test_object_without_retrieve_is_not_knowledge_provider(self) -> None:
        class NoRetrieve:
            pass

        assert not isinstance(NoRetrieve(), KnowledgeProvider)

    def test_object_without_resolve_is_not_profile_provider(self) -> None:
        class NoResolve:
            pass

        assert not isinstance(NoResolve(), ProfileProvider)

    def test_object_without_synthesize_is_not_synthesizer(self) -> None:
        class NoSynthesize:
            pass

        assert not isinstance(NoSynthesize(), Synthesizer)


class TestKnowledgeRetrievalRequest:
    def test_effective_max_results_uses_parent_when_none(self) -> None:
        req = make_research_request(max_knowledge_results=15)
        kreq = KnowledgeRetrievalRequest(query="test", parent_request=req)
        assert kreq.effective_max_results == 15

    def test_effective_max_results_uses_override_when_set(self) -> None:
        req = make_research_request(max_knowledge_results=15)
        kreq = KnowledgeRetrievalRequest(query="test", parent_request=req, max_results=5)
        assert kreq.effective_max_results == 5


class TestWebSearchRequest:
    def test_effective_values_use_parent_when_none(self) -> None:
        req = make_research_request(max_web_results=8, max_web_pages=3, language="de")
        wreq = WebSearchRequest(query="test", parent_request=req)
        assert wreq.effective_max_results == 8
        assert wreq.effective_max_pages == 3
        assert wreq.effective_language == "de"
