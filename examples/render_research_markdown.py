"""
Example: Render a ResearchResult to Markdown.

Demonstrates using MarkdownRenderer to convert a ResearchResult produced
by the ResearchEngine into a Markdown string.

Usage:
    python examples/render_research_markdown.py
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from research_core.contracts.claims import Claim, ClaimType
from research_core.contracts.common import SourceType
from research_core.contracts.contradictions import Contradiction
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.gaps import GapSeverity, GapStatus, GapType, OpenQuestion, ResearchGap
from research_core.contracts.request import ResearchRequest
from research_core.contracts.sources import EvidenceQuality, Provenance, Source
from research_core.engine import ResearchEngine
from research_core.protocols.knowledge import (
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResult,
)
from research_core.renderers import MarkdownRenderer
from research_core.synthesis import DeterministicSynthesizer

FIXED_TS = datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)


class _FixedProvider:
    def retrieve(self, request: KnowledgeRetrievalRequest) -> KnowledgeRetrievalResult:
        src = Source(
            source_id="src-001",
            source_type=SourceType.KNOWLEDGE,
            title="Climate Science Review 2024",
            publisher="Research Institute",
        )
        ev = EvidenceItem(
            evidence_id="ev-001",
            content=(
                "Arctic sea ice extent has declined approximately 13% per decade "
                "since satellite observations began in 1979."
            ),
            source_id="src-001",
            provenance=Provenance(
                source_id="src-001",
                source_type=SourceType.KNOWLEDGE,
                retrieved_at=FIXED_TS,
            ),
            quality=EvidenceQuality(relevance=0.90, authority=0.85),
        )
        return KnowledgeRetrievalResult(sources=(src,), evidence=(ev,))


class _SimpleExtractor:
    def extract(self, evidence: tuple[EvidenceItem, ...], request: Any) -> tuple[Claim, ...]:
        return tuple(
            Claim(
                claim_id=f"cl-{i:03d}",
                statement=ev.content,
                claim_type=ClaimType.FACTUAL,
                supporting_evidence_ids=(ev.evidence_id,),
            )
            for i, ev in enumerate(evidence, 1)
        )


class _SimpleGapAnalyzer:
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
            description="Only one source retrieved; cross-validation not possible.",
            severity=GapSeverity.MEDIUM,
            status=GapStatus.OPEN,
        )
        return (gap,), ()


def main() -> None:
    engine = ResearchEngine(
        knowledge_provider=_FixedProvider(),
        claim_extractor=_SimpleExtractor(),
        gap_analyzer=_SimpleGapAnalyzer(),
        synthesizer=DeterministicSynthesizer(),
    )

    request = ResearchRequest(
        question="What is happening to Arctic sea ice?",
        use_web=False,
    )

    result = engine.run(request)

    renderer = MarkdownRenderer()
    md = renderer.render(result)

    print(md)

    # Optionally, write to a file:
    # output_path = Path("research_output.md")
    # output_path.write_text(md, encoding="utf-8")
    # print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()
