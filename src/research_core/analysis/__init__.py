"""
research_core.analysis — gap analysis and quality diagnostics (RC6).

Public API
----------
GapAnalyzer           — structural Protocol for gap analyzers
DeterministicGapAnalyzer — pure, deterministic implementation
GapAnalysisConfig     — immutable configuration
GapAnalysisResult     — immutable result
QualityDiagnosticsResult — rich quality breakdown
GapAnalysisDiagnostics  — execution diagnostics with condition counts
DiagnosticStatus       — PASS / FAIL / INDETERMINATE / UNAVAILABLE / NOT_APPLICABLE
QualityDimensionSummary — per-dimension quality summary
CoverageDiagnostics    — structural coverage (evidence, claims, sources)
DistributionDiagnostics — source and provider distribution
EvidenceConditionDiagnostics — low-level evidence state
"""

from research_core.analysis.analyzer import DeterministicGapAnalyzer, GapAnalyzer
from research_core.analysis.config import GapAnalysisConfig
from research_core.analysis.contracts import (
    CoverageDiagnostics,
    DiagnosticStatus,
    DistributionDiagnostics,
    EvidenceConditionDiagnostics,
    GapAnalysisDiagnostics,
    GapAnalysisResult,
    QualityDiagnosticsResult,
    QualityDimensionSummary,
)

__all__ = [
    "GapAnalyzer",
    "DeterministicGapAnalyzer",
    "GapAnalysisConfig",
    "GapAnalysisResult",
    "QualityDiagnosticsResult",
    "GapAnalysisDiagnostics",
    "DiagnosticStatus",
    "QualityDimensionSummary",
    "CoverageDiagnostics",
    "DistributionDiagnostics",
    "EvidenceConditionDiagnostics",
]
