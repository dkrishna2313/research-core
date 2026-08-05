# Quality Diagnostics

## Overview

Quality diagnostics evaluate five evidence quality dimensions across all ranked evidence items. Results are aggregated per dimension (mean, min, max, median, below-threshold count) and combined into an overall score and status.

Quality scoring is:
- **Explicit-only** — scores come from `EvidenceQuality` fields; missing values remain `None`, never coerced to `0.0`
- **Score non-fabrication** — a missing score is semantically different from a score of `0.0`
- **Authority note** — authority scores are based solely on explicit `EvidenceQuality.authority` values, not inferred from source names or URLs

## Scored Dimensions

| Dimension | Source | Config Threshold |
|-----------|--------|-----------------|
| `relevance` | `EvidenceQuality.relevance` | `minimum_relevance_score` |
| `authority` | `EvidenceQuality.authority` | `minimum_authority_score` |
| `recency` | `EvidenceQuality.recency` | `minimum_recency_score` |
| `extraction_confidence` | `EvidenceQuality.extraction_confidence` | `minimum_extraction_confidence_score` |
| `provenance_completeness` | `RankedEvidence.components["provenance_completeness"].raw_value` | `minimum_provenance_completeness_score` |

## Per-Dimension Status

Each dimension gets a `DiagnosticStatus`:
- `PASS` — `mean >= threshold` (for measured values)
- `FAIL` — `mean < threshold`
- `UNAVAILABLE` — no measured values (`measured_count == 0`)

## Overall Score

The overall score is the equal-weighted `statistics.fmean` of all dimension means that are not `None`. Returns `None` when no dimension has any measured values.

## Overall Status Rules

Priority order (highest first):
1. No evidence → `FAIL`
2. Any `CRITICAL` gap → `FAIL`
3. Overall score is `None` → `INDETERMINATE`
4. Any gap present (non-critical) → `INDETERMINATE`
5. All measured dimensions pass → `PASS`

## Coverage Threshold

The `minimum_quality_coverage_ratio` config controls how many evidence items must have explicit scores for a dimension to be considered evaluable. If fewer than this fraction have a score, the `missing_quality_dimension` gap fires.

## Example

```python
from research_core.diagnostics import DeterministicGapAnalyzer, GapAnalysisConfig

result = analyzer.analyze(sources, ranked_evidence, claims, ranking_result, config)
qd = result.quality_diagnostics

print(f"Overall score  : {qd.overall_score:.3f}")
print(f"Overall status : {qd.overall_status}")

for dim in qd.dimensions:
    mean = f"{dim.mean:.3f}" if dim.mean is not None else "N/A"
    print(f"  {dim.dimension:30s}  mean={mean:>7s}  status={dim.status}")
```
