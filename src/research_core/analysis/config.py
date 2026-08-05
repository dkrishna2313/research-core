"""
Configuration for the gap analysis and quality diagnostics layer.

All thresholds are normalized to [0,1] where applicable. Counts must be
non-negative. The configuration fingerprint is stable across processes and
changes whenever any semantic field changes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from research_core.exceptions import ContractValidationError


@dataclass(frozen=True)
class GapAnalysisConfig:
    """Immutable configuration for DeterministicGapAnalyzer.

    Evidence count thresholds
    -------------------------
    minimum_evidence_count: minimum ranked evidence items before an
        INSUFFICIENT_EVIDENCE gap is emitted.
    minimum_source_count: minimum unique sources before an
        INSUFFICIENT_SOURCES gap is emitted.

    Coverage thresholds
    -------------------
    minimum_claim_coverage_ratio: fraction of claims that must resolve to
        known evidence IDs. Below this → LOW_CLAIM_COVERAGE gap.
    minimum_evidence_utilization_ratio: fraction of evidence items that must
        contribute at least one claim. Below this → LOW_EVIDENCE_UTILIZATION gap.

    Distribution thresholds
    -----------------------
    maximum_single_source_share: if the largest source's share of evidence
        exceeds this → SOURCE_CONCENTRATION gap.
    maximum_single_provider_share: same for providers.
    maximum_duplicate_share: fraction of evidence that is duplicated before a
        DUPLICATE_CONCENTRATION gap fires (requires ranking_result).
    maximum_truncated_share: fraction of truncated evidence before a
        TRUNCATION gap fires.

    Quality thresholds (applied to measured values only)
    -------------------------------------------------------
    minimum_*_score: threshold for the mean of available scores in each
        quality dimension.
    minimum_quality_coverage_ratio: fraction of evidence items that must
        have explicit quality scores for a dimension to be evaluable.

    Behavior
    --------
    include_passed_conditions: whether to include PASS conditions in
        GapAnalysisDiagnostics (does not affect gap output).
    analyzer_version: version tag included in gap IDs and diagnostics.
    """

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
    include_passed_conditions: bool = False
    analyzer_version: str = "1"

    def __post_init__(self) -> None:
        if self.minimum_evidence_count < 0:
            raise ContractValidationError(
                f"minimum_evidence_count must be >= 0, got {self.minimum_evidence_count}"
            )
        if self.minimum_source_count < 0:
            raise ContractValidationError(
                f"minimum_source_count must be >= 0, got {self.minimum_source_count}"
            )
        _check_ratio("minimum_claim_coverage_ratio", self.minimum_claim_coverage_ratio)
        _check_ratio(
            "minimum_evidence_utilization_ratio", self.minimum_evidence_utilization_ratio
        )
        _check_ratio("maximum_single_source_share", self.maximum_single_source_share)
        _check_ratio("maximum_single_provider_share", self.maximum_single_provider_share)
        _check_ratio("maximum_duplicate_share", self.maximum_duplicate_share)
        _check_ratio("maximum_truncated_share", self.maximum_truncated_share)
        _check_ratio("minimum_relevance_score", self.minimum_relevance_score)
        _check_ratio("minimum_authority_score", self.minimum_authority_score)
        _check_ratio("minimum_recency_score", self.minimum_recency_score)
        _check_ratio(
            "minimum_extraction_confidence_score", self.minimum_extraction_confidence_score
        )
        _check_ratio(
            "minimum_provenance_completeness_score",
            self.minimum_provenance_completeness_score,
        )
        _check_ratio("minimum_quality_coverage_ratio", self.minimum_quality_coverage_ratio)
        if not self.analyzer_version.strip():
            raise ContractValidationError("analyzer_version must not be empty")

    @property
    def fingerprint(self) -> str:
        """Stable SHA256-based fingerprint of all semantic fields.

        Changes whenever any semantic configuration field changes.
        Stable across processes. Dictionary key order does not affect it.
        """
        payload = {
            "minimum_evidence_count": self.minimum_evidence_count,
            "minimum_source_count": self.minimum_source_count,
            "minimum_claim_coverage_ratio": self.minimum_claim_coverage_ratio,
            "minimum_evidence_utilization_ratio": self.minimum_evidence_utilization_ratio,
            "maximum_single_source_share": self.maximum_single_source_share,
            "maximum_single_provider_share": self.maximum_single_provider_share,
            "maximum_duplicate_share": self.maximum_duplicate_share,
            "maximum_truncated_share": self.maximum_truncated_share,
            "minimum_relevance_score": self.minimum_relevance_score,
            "minimum_authority_score": self.minimum_authority_score,
            "minimum_recency_score": self.minimum_recency_score,
            "minimum_extraction_confidence_score": self.minimum_extraction_confidence_score,
            "minimum_provenance_completeness_score": self.minimum_provenance_completeness_score,
            "minimum_quality_coverage_ratio": self.minimum_quality_coverage_ratio,
            "analyzer_version": self.analyzer_version,
        }
        key = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(key.encode()).hexdigest()[:16]


def _check_ratio(name: str, value: float) -> None:
    import math

    if math.isnan(value) or math.isinf(value):
        raise ContractValidationError(f"{name} must be a finite number, got {value}")
    if not 0.0 <= value <= 1.0:
        raise ContractValidationError(f"{name} must be in [0,1], got {value}")
