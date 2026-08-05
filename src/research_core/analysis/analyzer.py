"""
Gap analysis and quality diagnostics analyzer.

GapAnalyzer is the protocol (structural subtyping).
DeterministicGapAnalyzer is the concrete, side-effect-free implementation.

Inputs:
  sources           — sequence of Source objects loaded for this analysis
  ranked_evidence   — the ranked evidence pool (from DeterministicEvidenceRanker)
  claims            — extracted claims (from DeterministicClaimExtractor); may be empty
  ranking_result    — full EvidenceRankingResult (for duplicate counts); may be None
  config            — GapAnalysisConfig

Outputs:
  GapAnalysisResult — immutable result with gaps, quality diagnostics, and run diagnostics

The analyzer is deterministic: identical inputs produce identical outputs.
No LLM calls, no I/O, no randomness.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from research_core.analysis.aggregate import (
    compute_coverage,
    compute_distribution,
    compute_evidence_conditions,
)
from research_core.analysis.conditions import (
    ConditionStatus,
    evaluate_all_conditions,
)
from research_core.analysis.config import GapAnalysisConfig
from research_core.analysis.contracts import (
    GapAnalysisDiagnostics,
    GapAnalysisResult,
    QualityDiagnosticsResult,
)
from research_core.analysis.quality import (
    compute_overall_score,
    compute_overall_status,
    score_all_dimensions,
)
from research_core.claims.contracts import ExtractedClaim
from research_core.contracts.common import EMPTY_METADATA, _to_proxy
from research_core.contracts.gaps import GapSeverity, ResearchGap
from research_core.contracts.result import ResearchStatus
from research_core.contracts.sources import Source
from research_core.normalization.contracts import EvidenceRankingResult, RankedEvidence

_ANALYZER_NAME = "DeterministicGapAnalyzer"

_SEVERITY_ORDER: dict[GapSeverity, int] = {
    GapSeverity.CRITICAL: 0,
    GapSeverity.HIGH: 1,
    GapSeverity.MEDIUM: 2,
    GapSeverity.LOW: 3,
}


def _gap_sort_key(gap: ResearchGap) -> tuple[int, str, str, str, str, str]:
    return (
        _SEVERITY_ORDER.get(gap.severity, 99),
        str(gap.gap_type),
        str(gap.status),
        str(sorted(gap.related_evidence_ids)),
        str(sorted(gap.related_claim_ids)),
        gap.gap_id,
    )


@runtime_checkable
class GapAnalyzer(Protocol):
    """Protocol for gap analysis and quality diagnostics.

    Implementors must be deterministic: identical inputs → identical outputs.
    No side effects, no LLM calls.
    """

    def analyze(
        self,
        sources: Sequence[Source],
        ranked_evidence: Sequence[RankedEvidence],
        claims: Sequence[ExtractedClaim],
        ranking_result: EvidenceRankingResult | None,
        config: GapAnalysisConfig,
    ) -> GapAnalysisResult:
        """Run gap analysis and return an immutable result."""
        ...


class DeterministicGapAnalyzer:
    """Pure, deterministic gap analysis and quality diagnostics analyzer.

    Thread-safe: the instance holds no mutable state.
    """

    def analyze(
        self,
        sources: Sequence[Source],
        ranked_evidence: Sequence[RankedEvidence],
        claims: Sequence[ExtractedClaim],
        ranking_result: EvidenceRankingResult | None,
        config: GapAnalysisConfig,
    ) -> GapAnalysisResult:
        """Run gap analysis and quality diagnostics.

        Steps:
        1. Compute structural aggregates (coverage, distribution, conditions)
        2. Score quality dimensions
        3. Evaluate all gap conditions
        4. Build GapAnalysisDiagnostics and QualityDiagnosticsResult
        5. Assemble GapAnalysisResult

        All steps are pure and deterministic.
        """
        coverage = compute_coverage(sources, ranked_evidence, claims)
        distribution = compute_distribution(ranked_evidence)
        ev_conditions = compute_evidence_conditions(ranked_evidence, ranking_result)
        dimensions = score_all_dimensions(ranked_evidence, coverage, config)

        condition_results = evaluate_all_conditions(
            sources=sources,
            ranked_evidence=ranked_evidence,
            claims=claims,
            coverage=coverage,
            distribution=distribution,
            ev_conditions=ev_conditions,
            dimensions=dimensions,
            cfg=config,
        )

        gaps: list[ResearchGap] = []
        n_pass = n_fail = n_indeterminate = n_unavailable = 0
        for cr in condition_results:
            if cr.status == ConditionStatus.PASS:
                n_pass += 1
            elif cr.status == ConditionStatus.FAIL:
                n_fail += 1
                if cr.gap is not None:
                    gaps.append(cr.gap)
            elif cr.status == ConditionStatus.INDETERMINATE:
                n_indeterminate += 1
            elif cr.status == ConditionStatus.UNAVAILABLE:
                n_unavailable += 1

        # Deduplicate gaps by gap_id (conditions may rarely emit the same gap)
        seen_ids: set[str] = set()
        unique_gaps: list[ResearchGap] = []
        for g in gaps:
            if g.gap_id not in seen_ids:
                seen_ids.add(g.gap_id)
                unique_gaps.append(g)

        # Sort deterministically: severity DESC, then type/status/ids/id ASC
        sorted_gaps = sorted(unique_gaps, key=_gap_sort_key)

        # Gap categorization for diagnostics
        by_category: Counter[str] = Counter(str(g.gap_type) for g in sorted_gaps)
        by_severity: Counter[str] = Counter(str(g.severity) for g in sorted_gaps)

        critical_count = by_severity.get(str(GapSeverity.CRITICAL), 0)
        high_count = by_severity.get(str(GapSeverity.HIGH), 0)

        # Overall quality score and status
        overall_score = compute_overall_score(dimensions)
        overall_status = compute_overall_status(
            overall_score, list(sorted_gaps), len(ranked_evidence)
        )

        quality_diagnostics = QualityDiagnosticsResult(
            overall_status=overall_status,
            overall_score=overall_score,
            dimensions=dimensions,
            coverage=coverage,
            distribution=distribution,
            evidence_conditions=ev_conditions,
            gap_count=len(sorted_gaps),
            critical_gap_count=critical_count,
            high_gap_count=high_count,
            configuration_fingerprint=config.fingerprint,
            analyzer=_ANALYZER_NAME,
            analyzer_version=config.analyzer_version,
            metadata=EMPTY_METADATA,
        )

        gap_analysis_diagnostics = GapAnalysisDiagnostics(
            input_source_count=len(sources),
            input_evidence_count=len(ranked_evidence),
            input_ranked_evidence_count=len(ranked_evidence),
            input_claim_count=len(claims),
            conditions_evaluated=len(condition_results),
            conditions_passed=n_pass,
            conditions_failed=n_fail,
            conditions_indeterminate=n_indeterminate,
            conditions_unavailable=n_unavailable,
            gaps_emitted=len(sorted_gaps),
            gaps_by_category=_to_proxy(dict(by_category)),
            gaps_by_severity=_to_proxy(dict(by_severity)),
            configuration_fingerprint=config.fingerprint,
            analyzer=_ANALYZER_NAME,
            analyzer_version=config.analyzer_version,
            metadata=EMPTY_METADATA,
        )

        # Recommended status — conservative: any gap → PARTIAL
        if sorted_gaps or not ranked_evidence:
            recommended_status = ResearchStatus.PARTIAL
        else:
            recommended_status = ResearchStatus.COMPLETE

        return GapAnalysisResult(
            gaps=tuple(sorted_gaps),
            quality_diagnostics=quality_diagnostics,
            gap_analysis_diagnostics=gap_analysis_diagnostics,
            recommended_status=recommended_status,
            is_complete=recommended_status == ResearchStatus.COMPLETE,
            metadata=EMPTY_METADATA,
        )
