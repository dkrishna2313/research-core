# Gap Analysis

## Overview

The `research_core.analysis` package (RC6) provides deterministic gap analysis: given a set of ranked evidence and extracted claims, it evaluates a fixed battery of conditions and returns structured `ResearchGap` objects describing each shortfall.

Gap analysis is:
- **Domain-neutral** — no assumption about the research topic
- **Deterministic** — identical inputs produce identical outputs and gap IDs
- **Side-effect-free** — no LLM calls, no network access, no I/O

## Entry Point

```python
from research_core.diagnostics import DeterministicGapAnalyzer, GapAnalysisConfig

analyzer = DeterministicGapAnalyzer()
result = analyzer.analyze(
    sources=sources,
    ranked_evidence=ranked_evidence,
    claims=claims,
    ranking_result=ranking_result,   # EvidenceRankingResult | None
    config=GapAnalysisConfig(),
)
```

The result type is `GapAnalysisResult` (see [DIAGNOSTIC_CONTRACTS.md](DIAGNOSTIC_CONTRACTS.md)).

## Gap Types

All gap types are drawn from `research_core.contracts.gaps.GapType`:

| Type | Meaning |
|------|---------|
| `NO_EVIDENCE` | No evidence was retrieved at all |
| `INSUFFICIENT_COVERAGE` | Structural coverage threshold not met |
| `WEAK_AUTHORITY` | Mean authority score below threshold |
| `STALE_EVIDENCE` | Mean recency score below threshold |
| `LOW_EXTRACTION_CONFIDENCE` | Mean extraction confidence below threshold |
| `MISSING_DIMENSION` | Quality dimension absent or sparsely populated |

## Conditions Evaluated (RC6)

Seventeen conditions are evaluated in a fixed deterministic order:

| Condition | Fires When | Severity |
|-----------|-----------|---------|
| `no_sources` | No source objects provided | CRITICAL |
| `no_evidence` | No ranked evidence items | CRITICAL |
| `insufficient_evidence` | `len(evidence) < minimum_evidence_count` | HIGH |
| `insufficient_sources` | Unique source count < `minimum_source_count` | HIGH |
| `no_claims` | Evidence present but zero claims extracted | MEDIUM |
| `evidence_without_claims` | Any evidence items without associated claims | LOW |
| `low_claim_coverage` | Claim coverage ratio < threshold | MEDIUM |
| `stale_evidence` | Mean recency dimension score < threshold | MEDIUM |
| `low_extraction_confidence` | Mean extraction_confidence score < threshold | MEDIUM |
| `source_concentration` | Largest source share > `maximum_single_source_share` | HIGH |
| `provider_concentration` | Largest provider share > `maximum_single_provider_share` | MEDIUM |
| `low_relevance` | Mean relevance score < threshold | MEDIUM |
| `low_authority` | Mean authority score < threshold | HIGH |
| `low_provenance_completeness` | Mean provenance completeness < threshold | LOW |
| `missing_quality_dimension` | Quality dimension coverage below threshold | LOW |
| `duplicate_concentration` | Duplicate share > `maximum_duplicate_share` | MEDIUM |
| `truncation` | Truncated evidence share > `maximum_truncated_share` | LOW |

## Gap Severity

`GapSeverity` values (from `research_core.contracts.gaps`):
- `CRITICAL` — analysis cannot proceed reliably
- `HIGH` — significant structural or quality problem
- `MEDIUM` — quality concern requiring attention
- `LOW` — minor issue or informational

## Recommended Status

The analyzer returns a `recommended_status` (`ResearchStatus.COMPLETE` or `PARTIAL`) using a conservative rule:
- **PARTIAL** — no evidence provided, or any gap was detected
- **COMPLETE** — evidence present and no gaps detected

## Gap IDs

Gap IDs are deterministic SHA256-based identifiers of the form `gap-<20hex>`. They encode: gap type, severity, status, observed value, threshold, affected IDs, analyzer version, and config fingerprint. The same gap in two separate runs of the same configuration produces the same ID.

**Edge case:** The gap ID formula does not include the condition name. Two distinct conditions that produce identical structural parameters (same gap type, severity, observed value, threshold, and affected IDs) will generate the same gap ID and be deduplicated to a single gap. This can occur with non-default zero-threshold configurations (`minimum_evidence_count=0`, `minimum_source_count=0`), where both `no_sources` and `no_evidence` emit a CRITICAL gap with threshold `0.0`. The `conditions_failed` count in diagnostics may therefore exceed `gaps_emitted` when this occurs.

## Configuration

See [GapAnalysisConfig](DIAGNOSTIC_CONTRACTS.md#gapanalysisconfig) for all threshold parameters.
