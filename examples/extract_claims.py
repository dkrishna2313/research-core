"""
Example: extract structured claims from ranked evidence using research_core.claims.

Demonstrates:
1. Building synthetic RankedEvidence objects from all claim types
2. Extracting claims with DeterministicClaimExtractor
3. Inspecting claim type, modality, polarity, quantitative/temporal expressions
4. Reading extraction diagnostics
5. Using custom ClaimExtractionConfig

No optional dependencies required — uses only standard library and research-core.
"""

from __future__ import annotations

from datetime import UTC, datetime

from research_core.claims import (
    ClaimExtractionConfig,
    DeterministicClaimExtractor,
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

FIXED_TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def _make_ranked(
    evidence_id: str,
    source_id: str,
    content: str,
    rank: int,
    source_type: SourceType = SourceType.KNOWLEDGE,
) -> RankedEvidence:
    provenance = Provenance(
        source_id=source_id,
        source_type=source_type,
        retrieved_at=FIXED_TS,
    )
    source = Source(source_id=source_id, source_type=source_type)
    evidence = EvidenceItem(
        evidence_id=evidence_id,
        content=content,
        source_id=source_id,
        provenance=provenance,
        quality=EvidenceQuality(),
    )
    norm = NormalizedEvidence(
        evidence=evidence,
        source=source,
        provider="example-provider",
        provider_rank=rank,
        provider_score=None,
        normalized_retrieval_signal=None,
        content_length=len(content),
        parent_evidence_id=None,
        segment_index=None,
    )
    return RankedEvidence(
        normalized_evidence=norm,
        rank=rank,
        score=1.0 / rank,
        components=(
            RankingComponent(
                name="retrieval",
                status=ComponentStatus.MISSING,
                raw_value=None,
                normalized_value=None,
                weight_used=0.0,
            ),
        ),
    )


EVIDENCE = [
    _make_ranked(
        "ev-factual",
        "src-report",
        "Global average temperatures have risen by 1.1°C since pre-industrial levels.",
        rank=1,
    ),
    _make_ranked(
        "ev-quantitative",
        "src-data",
        "Renewable energy capacity grew by 295 GW in 2023, a 50% increase over 2022.",
        rank=2,
    ),
    _make_ranked(
        "ev-causal",
        "src-study",
        "Higher carbon prices led to a 15% reduction in industrial emissions.",
        rank=3,
    ),
    _make_ranked(
        "ev-predictive",
        "src-forecast",
        "Solar capacity is projected to reach 5,000 GW by 2030.",
        rank=4,
    ),
    _make_ranked(
        "ev-normative",
        "src-policy",
        "Member states must reduce emissions by at least 55% compared to 1990 levels by 2030.",
        rank=5,
    ),
    _make_ranked(
        "ev-definitional",
        "src-glossary",
        "Net zero refers to achieving a balance between greenhouse gas emissions and removals.",
        rank=6,
    ),
    _make_ranked(
        "ev-comparative",
        "src-comparison",
        "Offshore wind has a higher capacity factor than onshore wind in most regions.",
        rank=7,
    ),
    _make_ranked(
        "ev-modal",
        "src-analysis",
        "Carbon capture technologies may reduce costs by up to 40% over the next decade.",
        rank=8,
    ),
    _make_ranked(
        "ev-negation",
        "src-report-2",
        "The 2023 targets were not met in eight of the twelve member states.",
        rank=9,
    ),
    _make_ranked(
        "ev-attribution",
        "src-news",
        "According to the IEA, clean energy investment exceeded $1.7 trillion in 2023.",
        rank=10,
        source_type=SourceType.WEB,
    ),
    _make_ranked(
        "ev-temporal",
        "src-timeline",
        "The Paris Agreement entered into force in November 2016 and covers the period 2020–2030.",
        rank=11,
    ),
    _make_ranked(
        "ev-multi",
        "src-summary",
        (
            "Emissions rose by 3% in 2022 because of post-pandemic recovery. "
            "Renewables must scale faster to meet the 1.5°C pathway. "
            "The policy may reduce emissions if fully implemented by 2025."
        ),
        rank=12,
    ),
]


def main() -> None:
    extractor = DeterministicClaimExtractor()

    print("=" * 72)
    print("RC5 Claim Extraction — Example")
    print("=" * 72)

    # --- Default extraction ---
    result = extractor.extract(EVIDENCE)

    print(f"\nInput evidence items : {result.diagnostics.input_evidence_count}")
    print(f"Claims extracted     : {result.diagnostics.claims_extracted}")
    print(f"Claims rejected      : {result.diagnostics.claims_rejected}")
    print(f"Duplicates collapsed : {result.diagnostics.duplicate_claims}")
    print(f"Evidence without claims: {result.diagnostics.evidence_without_claims}")
    print(f"Config fingerprint   : {result.diagnostics.configuration_fingerprint}")

    print("\n--- Claims ---\n")
    for i, claim in enumerate(result.claims, 1):
        qe = claim.quantitative_expressions
        te = claim.temporal_expressions
        attr = claim.attribution

        print(f"{i:2d}. [{claim.claim_type}][{claim.modality}][{claim.polarity}]")
        print(f"    {claim.claim_text}")
        print(f"    ID: {claim.claim_id}")
        print(f"    Source: {claim.source_id} / Evidence: {claim.evidence_id}")
        print(f"    Span: [{claim.evidence_start_char}:{claim.evidence_end_char}]")
        if qe:
            print(f"    Quantitative: {[q.text for q in qe]}")
        if te:
            print(f"    Temporal: {[t.text for t in te]}")
        if attr:
            print(f"    Attribution: '{attr.source_text}' via '{attr.reporting_verb}'")
        print()

    # --- By type breakdown ---
    print("--- Claim counts by type ---")
    for key, count in result.diagnostics.claims_by_type.items():
        if count > 0:
            print(f"  {key:<14} {count}")

    print("\n--- Claim counts by modality ---")
    for key, count in result.diagnostics.claims_by_modality.items():
        if count > 0:
            print(f"  {key:<14} {count}")

    print("\n--- Claim counts by polarity ---")
    for key, count in result.diagnostics.claims_by_polarity.items():
        if count > 0:
            print(f"  {key:<14} {count}")

    # --- Custom config ---
    print("\n--- Custom config: preserve questions, no deduplication ---\n")
    cfg = ClaimExtractionConfig(
        preserve_questions=True,
        deduplicate_exact=False,
        include_rejections=True,
    )
    result2 = extractor.extract(EVIDENCE, config=cfg)
    print(f"Claims extracted (no dedup): {result2.diagnostics.claims_extracted}")
    print(f"Config fingerprint: {result2.diagnostics.configuration_fingerprint}")
    differs = (
        result2.diagnostics.configuration_fingerprint
        != result.diagnostics.configuration_fingerprint
    )
    print(f"  (differs from default: {differs})")

    # --- Determinism check ---
    print("\n--- Determinism check ---\n")
    reversed_evidence = list(reversed(EVIDENCE))
    result_rev = extractor.extract(reversed_evidence)
    ids_forward = {c.claim_id for c in result.claims}
    ids_reversed = {c.claim_id for c in result_rev.claims}
    print(f"Same claim IDs regardless of input order: {ids_forward == ids_reversed}")

    print("\nDone.")


if __name__ == "__main__":
    main()
