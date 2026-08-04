"""
Example: normalize and rank evidence items using research_core.normalization.

Demonstrates:
1. Building synthetic Source and EvidenceItem objects
2. Normalizing with EvidenceNormalizer
3. Ranking with EvidenceRanker
4. Printing ranked results with scores and explainability components

No optional dependencies required — uses only standard library and research-core.
"""

from __future__ import annotations

from datetime import UTC, datetime

from research_core.contracts.common import SourceType
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.sources import EvidenceQuality, Provenance, Source
from research_core.normalization import EvidenceNormalizer, EvidenceRanker

FIXED_TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def main() -> None:
    # --- Build sources ---
    sources = (
        Source(
            source_id="src-web-01",
            source_type=SourceType.WEB,
            title="IPCC AR6 Summary",
            url="https://www.ipcc.ch/report/ar6/syr/",
        ),
        Source(
            source_id="src-web-02",
            source_type=SourceType.WEB,
            title="NASA Climate Facts",
            url="https://climate.nasa.gov/evidence/",
        ),
        Source(
            source_id="src-kb-01",
            source_type=SourceType.KNOWLEDGE,
            title="Internal Research Report Q3",
        ),
    )

    # --- Build evidence items ---
    evidence = (
        EvidenceItem(
            evidence_id="ev-web-01",
            content=(
                "Global surface temperature has increased faster since 1970 than in any other "
                "50-year period over at least the last 2000 years. Global mean sea level "
                "increased by 0.20 m between 1901 and 2018."
            ),
            source_id="src-web-01",
            provenance=Provenance(
                source_id="src-web-01",
                source_type=SourceType.WEB,
                retrieved_at=FIXED_TS,
                provider="duckduckgo",
                retrieval_rank=1,
                retrieval_score=None,
                extraction_method="trafilatura",
                extraction_confidence=0.90,
            ),
            quality=EvidenceQuality(relevance=0.95, authority=0.90),
        ),
        EvidenceItem(
            evidence_id="ev-web-02",
            content=(
                "Earth's average surface temperature has risen about 2 degrees Fahrenheit "
                "since the late 19th century, driven largely by increased carbon dioxide emissions "
                "into the atmosphere."
            ),
            source_id="src-web-02",
            provenance=Provenance(
                source_id="src-web-02",
                source_type=SourceType.WEB,
                retrieved_at=FIXED_TS,
                provider="duckduckgo",
                retrieval_rank=2,
                retrieval_score=None,
                extraction_method="trafilatura",
                extraction_confidence=0.85,
            ),
            quality=EvidenceQuality(relevance=0.80, authority=0.85),
        ),
        EvidenceItem(
            evidence_id="ev-kb-01",
            content=(
                "Analysis of 15 years of climate models shows consistent underestimation of "
                "Arctic warming rates. Current models project 3.5°C warming by 2100 under "
                "business-as-usual scenarios, with high confidence intervals."
            ),
            source_id="src-kb-01",
            provenance=Provenance(
                source_id="src-kb-01",
                source_type=SourceType.KNOWLEDGE,
                retrieved_at=FIXED_TS,
                provider="knowledge",
                retrieval_rank=1,
                retrieval_score=0.92,
                extraction_method="text",
                extraction_confidence=0.95,
                document_id="doc-internal-q3-2024",
            ),
            quality=EvidenceQuality(
                relevance=0.88, authority=0.75, recency=0.70, extraction_confidence=0.95
            ),
        ),
    )

    # --- Normalize ---
    normalizer = EvidenceNormalizer()
    normalized = normalizer.normalize(sources=sources, evidence=evidence)

    print(f"Normalized {len(normalized)} evidence items (from {len(evidence)} originals)\n")

    # --- Rank ---
    ranker = EvidenceRanker()
    result = ranker.rank(normalized)

    print(f"Ranked {result.diagnostics.total_ranked} items")
    print(f"Excluded: {result.diagnostics.total_excluded}")
    print(f"Duplicates: {result.diagnostics.total_duplicates}")
    print(f"Config fingerprint: {result.diagnostics.config_fingerprint}")
    print()

    # --- Print results ---
    for ranked in result.ranked:
        ne = ranked.normalized_evidence
        ev = ne.evidence
        print(f"#{ranked.rank}  score={ranked.score:.4f}  [{ne.provider}]")
        print(f"    evidence_id: {ev.evidence_id}")
        print(f"    content: {ev.content[:80].strip()}...")
        print(f"    provider_rank={ne.provider_rank}  signal={ne.normalized_retrieval_signal}")
        print("    components:")
        for comp in ranked.components:
            if comp.normalized_value is not None:
                print(
                    f"      {comp.name:<28} "
                    f"val={comp.normalized_value:.3f}  weight={comp.weight_used:.3f}"
                )
            else:
                print(f"      {comp.name:<28} MISSING")
        print()


if __name__ == "__main__":
    main()
