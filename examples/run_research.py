"""
Example: Full research engine run with in-memory providers.

Demonstrates building a ResearchEngine with deterministic in-memory providers
and running it end-to-end to produce a ResearchResult.

Usage:
    python examples/run_research.py
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from research_core.contracts.claims import Claim, ClaimType
from research_core.contracts.common import SourceType
from research_core.contracts.contradictions import Contradiction
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.gaps import (
    GapSeverity,
    GapStatus,
    GapType,
    OpenQuestion,
    ResearchGap,
)
from research_core.contracts.request import ResearchRequest
from research_core.contracts.sources import EvidenceQuality, Provenance, Source
from research_core.engine import ResearchEngine
from research_core.protocols.knowledge import (
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResult,
)
from research_core.synthesis import DeterministicSynthesizer

FIXED_TS = datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# In-memory providers (no network, no SDK required)
# ---------------------------------------------------------------------------

class InMemoryKnowledgeProvider:
    """Returns a hard-coded knowledge base — for demonstration only."""

    def retrieve(self, request: KnowledgeRetrievalRequest) -> KnowledgeRetrievalResult:
        src = Source(
            source_id="src-ipcc-2023",
            source_type=SourceType.KNOWLEDGE,
            title="IPCC Sixth Assessment Report",
            publisher="IPCC",
        )
        ev1 = EvidenceItem(
            evidence_id="ev-001",
            content=(
                "Global surface temperature has increased faster since 1970 than in any "
                "other 50-year period over at least the last 2000 years."
            ),
            source_id="src-ipcc-2023",
            provenance=Provenance(
                source_id="src-ipcc-2023",
                source_type=SourceType.KNOWLEDGE,
                retrieved_at=FIXED_TS,
            ),
            quality=EvidenceQuality(relevance=0.95, authority=0.92),
        )
        ev2 = EvidenceItem(
            evidence_id="ev-002",
            content=(
                "Human influence has warmed the atmosphere, ocean, and land. "
                "Widespread and rapid changes have occurred in the atmosphere, ocean, "
                "cryosphere, and biosphere."
            ),
            source_id="src-ipcc-2023",
            provenance=Provenance(
                source_id="src-ipcc-2023",
                source_type=SourceType.KNOWLEDGE,
                retrieved_at=FIXED_TS,
            ),
            quality=EvidenceQuality(relevance=0.88, authority=0.92),
        )
        return KnowledgeRetrievalResult(sources=(src,), evidence=(ev1, ev2))


class SimpleClaimExtractor:
    """Extracts one claim per evidence item (demonstration only)."""

    def extract(
        self, evidence: tuple[EvidenceItem, ...], request: Any
    ) -> tuple[Claim, ...]:
        return tuple(
            Claim(
                claim_id=f"cl-{i:03d}",
                statement=ev.content,
                claim_type=ClaimType.FACTUAL,
                supporting_evidence_ids=(ev.evidence_id,),
            )
            for i, ev in enumerate(evidence, 1)
        )


class SimpleGapAnalyzer:
    """Returns a minimal gap to illustrate the structure."""

    def analyze(
        self,
        claims: tuple[Claim, ...],
        evidence: tuple[EvidenceItem, ...],
        contradictions: tuple[Contradiction, ...],
        request: Any,
    ) -> tuple[tuple[ResearchGap, ...], tuple[OpenQuestion, ...]]:
        gap = ResearchGap(
            gap_id="gap-001",
            gap_type=GapType.INSUFFICIENT_COVERAGE,
            description="Analysis is limited to IPCC AR6; regional studies not retrieved.",
            severity=GapSeverity.MEDIUM,
            status=GapStatus.OPEN,
            recommended_action="Supplement with regional climate studies.",
        )
        oq = OpenQuestion(
            question="What are projected regional temperature changes by 2100?",
            priority="high",
            reason="Current evidence focuses on global averages only.",
        )
        return (gap,), (oq,)


# ---------------------------------------------------------------------------
# Run the pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    engine = ResearchEngine(
        knowledge_provider=InMemoryKnowledgeProvider(),
        claim_extractor=SimpleClaimExtractor(),
        gap_analyzer=SimpleGapAnalyzer(),
        synthesizer=DeterministicSynthesizer(),
    )

    request = ResearchRequest(
        question="What is the scientific consensus on climate change?",
        use_web=False,
    )

    print(f"Running research pipeline for: {request.question!r}\n")
    result = engine.run(request)

    print(f"Status:    {result.status.value}")
    print(f"Sources:   {len(result.sources)}")
    print(f"Evidence:  {len(result.evidence)}")
    print(f"Claims:    {len(result.claims)}")
    print(f"Gaps:      {len(result.gaps)}")
    print(f"Synthesis: {'available' if result.synthesis else 'not available'}")
    print()

    if result.synthesis:
        print("Narrative:")
        print(result.synthesis.narrative)
        print()
        if result.synthesis.key_findings:
            print("Key findings:")
            for f in result.synthesis.key_findings:
                print(f"  - {f}")
        print()

    if result.trace:
        print("Execution trace:")
        for ev in result.trace.events:
            print(f"  [{ev.stage.value}] {ev.status.value.upper()} — {ev.message}")


if __name__ == "__main__":
    main()
