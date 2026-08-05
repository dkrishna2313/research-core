"""
RC6 gap analysis and quality diagnostics contracts.

These types are distinct from the high-level ResearchResult quality model
(research_core.contracts.quality.QualityDiagnostics), which is used in the
final orchestrated result. These types represent the richer diagnostic layer
produced by the standalone DeterministicGapAnalyzer.

None throughout means "unavailable / not assessed" — never coerced to 0.0.
"""

from __future__ import annotations

import types
from dataclasses import dataclass, field
from enum import StrEnum

from research_core.contracts.common import EMPTY_METADATA, Metadata, _to_proxy
from research_core.contracts.gaps import ResearchGap
from research_core.contracts.result import ResearchStatus
from research_core.exceptions import ContractValidationError


class DiagnosticStatus(StrEnum):
    """Status of an evaluated diagnostic condition.

    PASS           — condition evaluated and threshold was satisfied.
    FAIL           — condition evaluated and threshold was not satisfied.
    INDETERMINATE  — artifacts exist but evidence is insufficient to decide.
    UNAVAILABLE    — required input signal is absent (missing values).
    NOT_APPLICABLE — condition does not apply to the current artifact set.
    """

    PASS = "pass"
    FAIL = "fail"
    INDETERMINATE = "indeterminate"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class QualityDimensionSummary:
    """Aggregate summary for one quality dimension across all evidence.

    Offsets into the evidence pool:
    - measured_count: items with a non-None score
    - missing_count:  items with a None score
    - total_count:    measured_count + missing_count

    Statistics are None when measured_count == 0.
    Threshold comparison is based on the mean of measured values.
    A measured score of 0.0 is distinct from a missing score (None).
    """

    dimension: str
    status: DiagnosticStatus
    measured_count: int
    missing_count: int
    minimum: float | None
    maximum: float | None
    mean: float | None
    median: float | None
    threshold: float | None
    below_threshold_count: int
    affected_evidence_ids: tuple[str, ...]
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if self.measured_count < 0:
            raise ContractValidationError(
                f"QualityDimensionSummary.measured_count must be >= 0, got {self.measured_count}"
            )
        if self.missing_count < 0:
            raise ContractValidationError(
                f"QualityDimensionSummary.missing_count must be >= 0, got {self.missing_count}"
            )
        if self.below_threshold_count < 0:
            raise ContractValidationError(
                f"QualityDimensionSummary.below_threshold_count must be >= 0, got "
                f"{self.below_threshold_count}"
            )
        for attr, val in (
            ("minimum", self.minimum),
            ("maximum", self.maximum),
            ("mean", self.mean),
            ("median", self.median),
        ):
            if val is not None and not 0.0 <= val <= 1.0:
                raise ContractValidationError(
                    f"QualityDimensionSummary.{attr} must be in [0,1] when not None, got {val}"
                )
        if self.threshold is not None and not 0.0 <= self.threshold <= 1.0:
            raise ContractValidationError(
                f"QualityDimensionSummary.threshold must be in [0,1] when not None, "
                f"got {self.threshold}"
            )
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))

    @property
    def total_count(self) -> int:
        return self.measured_count + self.missing_count


@dataclass(frozen=True)
class CoverageDiagnostics:
    """Structural coverage of evidence, sources, and claims.

    Ratios are None when the denominator is zero — a zero denominator is
    semantically different from a ratio of 0.0.
    """

    source_count: int
    evidence_count: int
    ranked_evidence_count: int
    claim_count: int
    claims_with_evidence: int
    claims_without_evidence: int
    evidence_with_claims: int
    evidence_without_claims: int
    unique_parent_evidence_count: int
    segmented_evidence_count: int
    sources_with_claims: int
    sources_without_claims: int
    claim_coverage_ratio: float | None
    evidence_utilization_ratio: float | None

    def __post_init__(self) -> None:
        for name, val in (
            ("source_count", self.source_count),
            ("evidence_count", self.evidence_count),
            ("ranked_evidence_count", self.ranked_evidence_count),
            ("claim_count", self.claim_count),
            ("claims_with_evidence", self.claims_with_evidence),
            ("claims_without_evidence", self.claims_without_evidence),
            ("evidence_with_claims", self.evidence_with_claims),
            ("evidence_without_claims", self.evidence_without_claims),
            ("unique_parent_evidence_count", self.unique_parent_evidence_count),
            ("segmented_evidence_count", self.segmented_evidence_count),
            ("sources_with_claims", self.sources_with_claims),
            ("sources_without_claims", self.sources_without_claims),
        ):
            if val < 0:
                raise ContractValidationError(
                    f"CoverageDiagnostics.{name} must be >= 0, got {val}"
                )
        for ratio_name, ratio_val in (
            ("claim_coverage_ratio", self.claim_coverage_ratio),
            ("evidence_utilization_ratio", self.evidence_utilization_ratio),
        ):
            if ratio_val is not None and not 0.0 <= ratio_val <= 1.0:
                raise ContractValidationError(
                    f"CoverageDiagnostics.{ratio_name} must be in [0,1] "
                    f"when not None, got {ratio_val}"
                )


@dataclass(frozen=True)
class DistributionDiagnostics:
    """Source and provider distribution diagnostics.

    Concentration measures source/provider dominance. High concentration
    is a structural observation — not a quality or authority judgment.

    evidence_per_source and evidence_per_provider are immutable mappings
    from ID/name to count.
    """

    unique_source_count: int
    unique_provider_count: int
    largest_source_share: float | None
    largest_provider_share: float | None
    source_diversity_score: float | None
    provider_diversity_score: float | None
    evidence_per_source: Metadata
    evidence_per_provider: Metadata

    def __post_init__(self) -> None:
        for name, val in (
            ("largest_source_share", self.largest_source_share),
            ("largest_provider_share", self.largest_provider_share),
            ("source_diversity_score", self.source_diversity_score),
            ("provider_diversity_score", self.provider_diversity_score),
        ):
            if val is not None and not 0.0 <= val <= 1.0:
                raise ContractValidationError(
                    f"DistributionDiagnostics.{name} must be in [0,1] when not None, got {val}"
                )
        if not isinstance(self.evidence_per_source, types.MappingProxyType):
            object.__setattr__(
                self, "evidence_per_source", _to_proxy(self.evidence_per_source)
            )
        if not isinstance(self.evidence_per_provider, types.MappingProxyType):
            object.__setattr__(
                self, "evidence_per_provider", _to_proxy(self.evidence_per_provider)
            )


@dataclass(frozen=True)
class EvidenceConditionDiagnostics:
    """Low-level evidence state diagnostics.

    truncated_evidence_count: items where metadata["truncated"] is True.
    duplicate_evidence_count: from EvidenceRankingResult.duplicates.
    near_duplicate_evidence_count: always 0 in RC6 (not yet implemented).
    missing_retrieval_score_count: items where provider_score is None.
    missing_retrieval_rank_count: items where provider_rank is None.
    invalid_lineage_count: items with inconsistent segment lineage.
    """

    truncated_evidence_count: int
    duplicate_evidence_count: int
    near_duplicate_evidence_count: int
    missing_retrieval_score_count: int
    missing_retrieval_rank_count: int
    invalid_lineage_count: int

    def __post_init__(self) -> None:
        for name, val in (
            ("truncated_evidence_count", self.truncated_evidence_count),
            ("duplicate_evidence_count", self.duplicate_evidence_count),
            ("near_duplicate_evidence_count", self.near_duplicate_evidence_count),
            ("missing_retrieval_score_count", self.missing_retrieval_score_count),
            ("missing_retrieval_rank_count", self.missing_retrieval_rank_count),
            ("invalid_lineage_count", self.invalid_lineage_count),
        ):
            if val < 0:
                raise ContractValidationError(
                    f"EvidenceConditionDiagnostics.{name} must be >= 0, got {val}"
                )


@dataclass(frozen=True)
class QualityDiagnosticsResult:
    """Rich quality diagnostics from the gap analyzer.

    Distinct from research_core.contracts.quality.QualityDiagnostics, which is
    the summary type embedded in the final ResearchResult.

    overall_score is None when no quality dimension has any measured values.
    overall_status is never PASS when evidence is empty or critical gaps exist.
    """

    overall_status: DiagnosticStatus
    overall_score: float | None
    dimensions: tuple[QualityDimensionSummary, ...]
    coverage: CoverageDiagnostics
    distribution: DistributionDiagnostics
    evidence_conditions: EvidenceConditionDiagnostics
    gap_count: int
    critical_gap_count: int
    high_gap_count: int
    configuration_fingerprint: str
    analyzer: str
    analyzer_version: str
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if self.overall_score is not None and not 0.0 <= self.overall_score <= 1.0:
            raise ContractValidationError(
                f"QualityDiagnosticsResult.overall_score must be in [0,1] when not None, "
                f"got {self.overall_score}"
            )
        for name, val in (
            ("gap_count", self.gap_count),
            ("critical_gap_count", self.critical_gap_count),
            ("high_gap_count", self.high_gap_count),
        ):
            if val < 0:
                raise ContractValidationError(
                    f"QualityDiagnosticsResult.{name} must be >= 0, got {val}"
                )
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


@dataclass(frozen=True)
class GapAnalysisDiagnostics:
    """Execution diagnostics for a gap analysis run.

    conditions_evaluated = conditions_passed + conditions_failed
                         + conditions_indeterminate + conditions_unavailable
    gaps_emitted = len(GapAnalysisResult.gaps)
    """

    input_source_count: int
    input_evidence_count: int
    input_ranked_evidence_count: int
    input_claim_count: int
    conditions_evaluated: int
    conditions_passed: int
    conditions_failed: int
    conditions_indeterminate: int
    conditions_unavailable: int
    gaps_emitted: int
    gaps_by_category: Metadata
    gaps_by_severity: Metadata
    configuration_fingerprint: str
    analyzer: str
    analyzer_version: str
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        total = (
            self.conditions_passed
            + self.conditions_failed
            + self.conditions_indeterminate
            + self.conditions_unavailable
        )
        if total != self.conditions_evaluated:
            raise ContractValidationError(
                f"GapAnalysisDiagnostics: conditions_evaluated ({self.conditions_evaluated}) "
                f"must equal sum of pass/fail/indeterminate/unavailable ({total})"
            )
        for name, val in (
            ("input_source_count", self.input_source_count),
            ("input_evidence_count", self.input_evidence_count),
            ("input_ranked_evidence_count", self.input_ranked_evidence_count),
            ("input_claim_count", self.input_claim_count),
            ("conditions_evaluated", self.conditions_evaluated),
            ("conditions_passed", self.conditions_passed),
            ("conditions_failed", self.conditions_failed),
            ("conditions_indeterminate", self.conditions_indeterminate),
            ("conditions_unavailable", self.conditions_unavailable),
            ("gaps_emitted", self.gaps_emitted),
        ):
            if val < 0:
                raise ContractValidationError(
                    f"GapAnalysisDiagnostics.{name} must be >= 0, got {val}"
                )
        if not isinstance(self.gaps_by_category, types.MappingProxyType):
            object.__setattr__(self, "gaps_by_category", _to_proxy(self.gaps_by_category))
        if not isinstance(self.gaps_by_severity, types.MappingProxyType):
            object.__setattr__(self, "gaps_by_severity", _to_proxy(self.gaps_by_severity))
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


@dataclass(frozen=True)
class GapAnalysisResult:
    """Immutable result of a gap analysis run.

    gaps: all detected research gaps, sorted by severity DESC then category ASC.
    quality_diagnostics: rich quality breakdown for this analysis.
    gap_analysis_diagnostics: execution diagnostics with condition counts.
    recommended_status: COMPLETE or PARTIAL recommendation for orchestration.
      - PARTIAL whenever evidence is empty or any gap was detected.
      - COMPLETE only when evidence is present and no gaps were detected.
    is_complete: True iff recommended_status == COMPLETE.
    """

    gaps: tuple[ResearchGap, ...]
    quality_diagnostics: QualityDiagnosticsResult
    gap_analysis_diagnostics: GapAnalysisDiagnostics
    recommended_status: ResearchStatus
    is_complete: bool
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        expected_is_complete = self.recommended_status == ResearchStatus.COMPLETE
        if self.is_complete != expected_is_complete:
            raise ContractValidationError(
                f"GapAnalysisResult.is_complete must be "
                f"{expected_is_complete} when recommended_status is "
                f"{self.recommended_status!r}"
            )
        gap_ids = [g.gap_id for g in self.gaps]
        seen: set[str] = set()
        for gid in gap_ids:
            if gid in seen:
                raise ContractValidationError(
                    f"GapAnalysisResult: duplicate gap_id {gid!r}"
                )
            seen.add(gid)
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


__all__ = [
    "DiagnosticStatus",
    "QualityDimensionSummary",
    "CoverageDiagnostics",
    "DistributionDiagnostics",
    "EvidenceConditionDiagnostics",
    "QualityDiagnosticsResult",
    "GapAnalysisDiagnostics",
    "GapAnalysisResult",
]
