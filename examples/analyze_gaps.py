"""
Example: RC6 gap analysis and quality diagnostics.

Demonstrates how to use DeterministicGapAnalyzer to evaluate a set of
ranked evidence and extracted claims, producing structured gap diagnostics.

No LLM calls, no network access, no side effects.
Run:
    python examples/analyze_gaps.py
"""

from __future__ import annotations

from datetime import UTC, datetime

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
from research_core.diagnostics import (
    DeterministicGapAnalyzer,
    GapAnalysisConfig,
)
from research_core.normalization.contracts import (
    ComponentStatus,
    NormalizedEvidence,
    RankedEvidence,
    RankingComponent,
)

# ---------------------------------------------------------------------------
# Build sample data
# ---------------------------------------------------------------------------

RETRIEVED_AT = datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)

source_a = Source(source_id="src-ipcc-2023", source_type=SourceType.WEB)
source_b = Source(source_id="src-nature-2023", source_type=SourceType.WEB)

provenance_a = Provenance(
    source_id="src-ipcc-2023",
    source_type=SourceType.WEB,
    retrieved_at=RETRIEVED_AT,
    url="https://www.ipcc.ch/report/ar6/",
)
provenance_b = Provenance(
    source_id="src-nature-2023",
    source_type=SourceType.WEB,
    retrieved_at=RETRIEVED_AT,
    url="https://www.nature.com/articles/example",
)

ev_a = EvidenceItem(
    evidence_id="ev-ipcc-01",
    content=(
        "Global surface temperature increased by approximately 1.1°C above the "
        "1850–1900 baseline as of 2011–2020."
    ),
    source_id="src-ipcc-2023",
    provenance=provenance_a,
    quality=EvidenceQuality(relevance=0.95, authority=0.92, recency=0.80),
)
ev_b = EvidenceItem(
    evidence_id="ev-nature-01",
    content=(
        "Ocean heat content has increased substantially over the past five decades, "
        "absorbing over 90% of the excess energy trapped by greenhouse gases."
    ),
    source_id="src-nature-2023",
    provenance=provenance_b,
    quality=EvidenceQuality(relevance=0.88, authority=0.85, recency=0.78),
)

norm_a = NormalizedEvidence(
    evidence=ev_a,
    source=source_a,
    provider="web",
    provider_rank=1,
    provider_score=0.95,
    normalized_retrieval_signal=0.95,
    content_length=len(ev_a.content),
    parent_evidence_id=None,
    segment_index=None,
)
norm_b = NormalizedEvidence(
    evidence=ev_b,
    source=source_b,
    provider="web",
    provider_rank=2,
    provider_score=0.85,
    normalized_retrieval_signal=0.85,
    content_length=len(ev_b.content),
    parent_evidence_id=None,
    segment_index=None,
)

pc_component = RankingComponent(
    name="provenance_completeness",
    status=ComponentStatus.AVAILABLE,
    raw_value=0.8,
    normalized_value=0.8,
    weight_used=0.2,
)

ranked_a = RankedEvidence(
    normalized_evidence=norm_a,
    rank=1,
    score=0.95,
    components=(pc_component,),
)
ranked_b = RankedEvidence(
    normalized_evidence=norm_b,
    rank=2,
    score=0.85,
    components=(pc_component,),
)

claim_a = ExtractedClaim(
    claim_id="clm-001",
    claim_text="Global surface temperature increased by 1.1°C above the 1850–1900 baseline.",
    normalized_text="global surface temperature increased by 1.1°c above the 1850–1900 baseline.",
    claim_type=ClaimType.QUANTITATIVE,
    modality=ClaimModality.ASSERTED,
    polarity=ClaimPolarity.POSITIVE,
    scope=ClaimScope(),
    qualifiers=(),
    quantitative_expressions=(),
    temporal_expressions=(),
    attribution=None,
    source_id="src-ipcc-2023",
    evidence_id="ev-ipcc-01",
    parent_evidence_id=None,
    segment_index=None,
    evidence_start_char=0,
    evidence_end_char=73,
    sentence_index=0,
    clause_index=0,
    extractor="DeterministicClaimExtractor",
    extractor_version="1",
)

# ---------------------------------------------------------------------------
# Run gap analysis
# ---------------------------------------------------------------------------

config = GapAnalysisConfig(
    minimum_evidence_count=2,
    minimum_source_count=2,
    minimum_relevance_score=0.5,
    minimum_authority_score=0.5,
    minimum_recency_score=0.3,
    minimum_extraction_confidence_score=0.3,
    minimum_provenance_completeness_score=0.5,
)

analyzer = DeterministicGapAnalyzer()
result = analyzer.analyze(
    sources=[source_a, source_b],
    ranked_evidence=[ranked_a, ranked_b],
    claims=[claim_a],
    ranking_result=None,
    config=config,
)

# ---------------------------------------------------------------------------
# Print results
# ---------------------------------------------------------------------------

print(f"Recommended status : {result.recommended_status}")
print(f"Is complete        : {result.is_complete}")
print(f"Gaps detected      : {len(result.gaps)}")
print()

if result.gaps:
    print("Gaps:")
    for gap in result.gaps:
        print(f"  [{gap.severity.upper()}] {gap.gap_type}: {gap.description}")
        if gap.recommended_action:
            print(f"    → {gap.recommended_action}")
    print()

qd = result.quality_diagnostics
print(f"Overall quality status : {qd.overall_status}")
print(f"Overall quality score  : {qd.overall_score:.3f}" if qd.overall_score is not None else "Overall quality score  : N/A")
print()

print("Dimension breakdown:")
for dim in qd.dimensions:
    mean_str = f"{dim.mean:.3f}" if dim.mean is not None else "N/A"
    print(
        f"  {dim.dimension:30s}  mean={mean_str:>7s}  status={dim.status}"
    )
print()

diag = result.gap_analysis_diagnostics
print(f"Conditions evaluated  : {diag.conditions_evaluated}")
print(f"  passed              : {diag.conditions_passed}")
print(f"  failed              : {diag.conditions_failed}")
print(f"  unavailable         : {diag.conditions_unavailable}")
print(f"Config fingerprint    : {config.fingerprint}")
