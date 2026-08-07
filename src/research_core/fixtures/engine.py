"""
Deterministic fixture engine for research-core.

build_fixture_engine() returns a fully configured ResearchEngine backed by
in-memory providers and the real RC4–RC7 pipeline.  It requires no network,
no Knowledge Layer runtime, and no external configuration.  Output is stable
across runs given the same inputs and the default fixed clock.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from research_core.contracts.common import SourceType
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.sources import EvidenceQuality, Provenance, Source
from research_core.engine import ResearchEngine
from research_core.exceptions import UnknownProfileError
from research_core.protocols.knowledge import (
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResult,
)
from research_core.protocols.profiles import ResolvedProfile
from research_core.protocols.web import WebSearchRequest, WebSearchResult

FIXTURE_CLOCK_TS = datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)

FIXTURE_PROFILE_IDS = frozenset({"fixture", "default", "demo"})


class _FixtureProfileProvider:
    """Resolves fixture profile IDs. Raises UnknownProfileError for all others."""

    def resolve(self, profile_id: str) -> ResolvedProfile:
        if profile_id not in FIXTURE_PROFILE_IDS:
            raise UnknownProfileError(
                profile_id,
                f"unknown profile {profile_id!r}; fixture mode recognizes: "
                + ", ".join(sorted(FIXTURE_PROFILE_IDS)),
            )
        return ResolvedProfile(
            profile_id=profile_id,
            display_name="Fixture Profile",
            description="Deterministic in-memory fixture for demos and testing.",
        )

    def resolve_many(self, profile_ids: tuple[str, ...]) -> tuple[ResolvedProfile, ...]:
        return tuple(self.resolve(pid) for pid in profile_ids)


class _FixtureKnowledgeProvider:
    """Returns hard-coded, deterministic evidence. No network required."""

    def retrieve(self, request: KnowledgeRetrievalRequest) -> KnowledgeRetrievalResult:
        src = Source(
            source_id="src-fixture-01",
            source_type=SourceType.KNOWLEDGE,
            title="Fixture Knowledge Source",
            publisher="Fixture Publisher",
        )
        ev1 = EvidenceItem(
            evidence_id="ev-fixture-01",
            content=(
                "Global surface temperature increased by approximately 1.1 degrees Celsius "
                "above the pre-industrial baseline as of the most recent assessment period."
            ),
            source_id="src-fixture-01",
            provenance=Provenance(
                source_id="src-fixture-01",
                source_type=SourceType.KNOWLEDGE,
                retrieved_at=FIXTURE_CLOCK_TS,
            ),
            quality=EvidenceQuality(relevance=0.90, authority=0.88, recency=0.75),
        )
        ev2 = EvidenceItem(
            evidence_id="ev-fixture-02",
            content=(
                "Human activities are estimated to have caused approximately 1.0 degrees Celsius "
                "of global warming above pre-industrial levels, with a range of 0.8 to 1.2 degrees."
            ),
            source_id="src-fixture-01",
            provenance=Provenance(
                source_id="src-fixture-01",
                source_type=SourceType.KNOWLEDGE,
                retrieved_at=FIXTURE_CLOCK_TS,
            ),
            quality=EvidenceQuality(relevance=0.88, authority=0.90, recency=0.70),
        )
        ev3 = EvidenceItem(
            evidence_id="ev-fixture-03",
            content=(
                "Warming of 1.5 degrees Celsius or higher increases the risk associated with "
                "long-lasting or irreversible changes, such as the loss of some ecosystems."
            ),
            source_id="src-fixture-01",
            provenance=Provenance(
                source_id="src-fixture-01",
                source_type=SourceType.KNOWLEDGE,
                retrieved_at=FIXTURE_CLOCK_TS,
            ),
            quality=EvidenceQuality(relevance=0.85, authority=0.88, recency=0.72),
        )
        return KnowledgeRetrievalResult(sources=(src,), evidence=(ev1, ev2, ev3))


class _FixtureWebProvider:
    """Returns hard-coded, deterministic web evidence. No network required."""

    def search(self, request: WebSearchRequest) -> WebSearchResult:
        src = Source(
            source_id="src-fixture-web-01",
            source_type=SourceType.WEB,
            title="Fixture Web Source",
            url="https://fixture.example/climate",
        )
        ev = EvidenceItem(
            evidence_id="ev-fixture-web-01",
            content=(
                "Recent observational records confirm that the last decade was the "
                "warmest on record since systematic measurements began."
            ),
            source_id="src-fixture-web-01",
            provenance=Provenance(
                source_id="src-fixture-web-01",
                source_type=SourceType.WEB,
                retrieved_at=FIXTURE_CLOCK_TS,
                url="https://fixture.example/climate",
            ),
            quality=EvidenceQuality(relevance=0.80, authority=0.72, recency=0.90),
        )
        return WebSearchResult(sources=(src,), evidence=(ev,))


def build_fixture_engine(
    *,
    use_web: bool = False,
    clock: Callable[[], datetime] | None = None,
    use_rc_pipeline: bool = True,
) -> ResearchEngine:
    """Return a ResearchEngine backed entirely by deterministic in-memory fixtures.

    When use_rc_pipeline=True (default), wires the real RC4 normalizer, RC4 ranker,
    RC5 DeterministicClaimExtractor, RC6 DeterministicGapAnalyzer, and
    RC7 DeterministicSynthesizer for end-to-end structured output.

    The clock defaults to a fixed timestamp for deterministic trace events.
    No network access, no Knowledge Layer runtime, no external configuration needed.
    """
    fixed_clock = clock if clock is not None else (lambda: FIXTURE_CLOCK_TS)

    web_provider = _FixtureWebProvider() if use_web else None

    if use_rc_pipeline:
        from research_core.analysis.analyzer import DeterministicGapAnalyzer
        from research_core.claims.extractor import DeterministicClaimExtractor
        from research_core.normalization.normalizer import EvidenceNormalizer
        from research_core.normalization.ranker import EvidenceRanker
        from research_core.synthesis import DeterministicSynthesizer

        return ResearchEngine(
            profile_provider=_FixtureProfileProvider(),
            knowledge_provider=_FixtureKnowledgeProvider(),
            web_search_provider=web_provider,
            evidence_normalizer=EvidenceNormalizer(),
            evidence_ranker=EvidenceRanker(),
            rc5_claim_extractor=DeterministicClaimExtractor(),
            rc6_gap_analyzer=DeterministicGapAnalyzer(),
            synthesizer=DeterministicSynthesizer(),
            clock=fixed_clock,
        )

    # Legacy path (fallback for isolated unit tests)
    from research_core.synthesis import DeterministicSynthesizer

    return ResearchEngine(
        profile_provider=_FixtureProfileProvider(),
        knowledge_provider=_FixtureKnowledgeProvider(),
        web_search_provider=web_provider,
        synthesizer=DeterministicSynthesizer(),
        clock=fixed_clock,
    )
