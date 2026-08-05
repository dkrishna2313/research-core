# Diagnostic Contracts

RC6 introduces the `research_core.analysis` package with these immutable dataclasses.
All types are available from the public re-export at `research_core.diagnostics`.

## GapAnalysisConfig

Immutable configuration for `DeterministicGapAnalyzer`. All ratio fields must be in `[0, 1]`.

```python
@dataclass(frozen=True)
class GapAnalysisConfig:
    minimum_evidence_count: int = 2
    minimum_source_count: int = 1
    minimum_claim_coverage_ratio: float = 0.5
    minimum_evidence_utilization_ratio: float = 0.3
    maximum_single_source_share: float = 0.9
    maximum_single_provider_share: float = 0.95
    maximum_duplicate_share: float = 0.5
    maximum_truncated_share: float = 0.5
    minimum_relevance_score: float = 0.3
    minimum_authority_score: float = 0.2
    minimum_recency_score: float = 0.2
    minimum_extraction_confidence_score: float = 0.3
    minimum_provenance_completeness_score: float = 0.5
    minimum_quality_coverage_ratio: float = 0.3
    include_passed_conditions: bool = False  # reserved; no effect in RC6
    analyzer_version: str = "1"

    @property
    def fingerprint(self) -> str:
        """Stable 16-char SHA256 fingerprint of all semantic fields."""
```

## DiagnosticStatus

```python
class DiagnosticStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INDETERMINATE = "indeterminate"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"
```

## QualityDimensionSummary

Aggregate statistics for one quality dimension across all evidence.

| Field | Type | Notes |
|-------|------|-------|
| `dimension` | `str` | e.g. `"relevance"` |
| `status` | `DiagnosticStatus` | based on mean vs threshold |
| `measured_count` | `int` | evidence items with non-None score |
| `missing_count` | `int` | evidence items with None score |
| `minimum` | `float \| None` | None when `measured_count == 0` |
| `maximum` | `float \| None` | None when `measured_count == 0` |
| `mean` | `float \| None` | None when `measured_count == 0` |
| `median` | `float \| None` | None when `measured_count == 0` |
| `threshold` | `float \| None` | from config |
| `below_threshold_count` | `int` | items with score < threshold |
| `affected_evidence_ids` | `tuple[str, ...]` | IDs below threshold |
| `total_count` | `int` (property) | `measured_count + missing_count` |

## CoverageDiagnostics

Structural coverage of evidence, sources, and claims.

| Field | Type |
|-------|------|
| `source_count` | `int` |
| `evidence_count` | `int` |
| `ranked_evidence_count` | `int` |
| `claim_count` | `int` |
| `claims_with_evidence` | `int` |
| `claims_without_evidence` | `int` |
| `evidence_with_claims` | `int` |
| `evidence_without_claims` | `int` |
| `unique_parent_evidence_count` | `int` |
| `segmented_evidence_count` | `int` |
| `sources_with_claims` | `int` |
| `sources_without_claims` | `int` |
| `claim_coverage_ratio` | `float \| None` |
| `evidence_utilization_ratio` | `float \| None` |

## DistributionDiagnostics

Source and provider distribution of evidence.

| Field | Type |
|-------|------|
| `unique_source_count` | `int` |
| `unique_provider_count` | `int` |
| `largest_source_share` | `float \| None` |
| `largest_provider_share` | `float \| None` |
| `source_diversity_score` | `float \| None` |
| `provider_diversity_score` | `float \| None` |
| `evidence_per_source` | `Metadata` (MappingProxyType) |
| `evidence_per_provider` | `Metadata` (MappingProxyType) |

## EvidenceConditionDiagnostics

Low-level evidence state diagnostics.

| Field | Type | Notes |
|-------|------|-------|
| `truncated_evidence_count` | `int` | `metadata["truncated"] is True` |
| `duplicate_evidence_count` | `int` | from `EvidenceRankingResult.duplicates` |
| `near_duplicate_evidence_count` | `int` | always 0 in RC6 |
| `missing_retrieval_score_count` | `int` | `provider_score is None` |
| `missing_retrieval_rank_count` | `int` | `provider_rank is None` |
| `invalid_lineage_count` | `int` | `segment_index` and `parent_evidence_id` inconsistent |

## QualityDiagnosticsResult

Rich quality breakdown for a gap analysis run.

| Field | Type |
|-------|------|
| `overall_status` | `DiagnosticStatus` |
| `overall_score` | `float \| None` |
| `dimensions` | `tuple[QualityDimensionSummary, ...]` |
| `coverage` | `CoverageDiagnostics` |
| `distribution` | `DistributionDiagnostics` |
| `evidence_conditions` | `EvidenceConditionDiagnostics` |
| `gap_count` | `int` |
| `critical_gap_count` | `int` |
| `high_gap_count` | `int` |
| `configuration_fingerprint` | `str` |
| `analyzer` | `str` |
| `analyzer_version` | `str` |

## GapAnalysisDiagnostics

Execution diagnostics for a gap analysis run.

Invariant: `conditions_evaluated == conditions_passed + conditions_failed + conditions_indeterminate + conditions_unavailable`

| Field | Type |
|-------|------|
| `input_source_count` | `int` |
| `input_evidence_count` | `int` |
| `input_ranked_evidence_count` | `int` |
| `input_claim_count` | `int` |
| `conditions_evaluated` | `int` |
| `conditions_passed` | `int` |
| `conditions_failed` | `int` |
| `conditions_indeterminate` | `int` |
| `conditions_unavailable` | `int` |
| `gaps_emitted` | `int` |
| `gaps_by_category` | `Metadata` |
| `gaps_by_severity` | `Metadata` |
| `configuration_fingerprint` | `str` |
| `analyzer` | `str` |
| `analyzer_version` | `str` |

## GapAnalysisResult

Immutable result of a gap analysis run.

| Field | Type | Notes |
|-------|------|-------|
| `gaps` | `tuple[ResearchGap, ...]` | sorted by severity DESC, type ASC |
| `quality_diagnostics` | `QualityDiagnosticsResult` | |
| `gap_analysis_diagnostics` | `GapAnalysisDiagnostics` | |
| `recommended_status` | `ResearchStatus` | COMPLETE or PARTIAL |
| `is_complete` | `bool` | `recommended_status == COMPLETE` |

Invariant: `is_complete == (recommended_status == ResearchStatus.COMPLETE)`
