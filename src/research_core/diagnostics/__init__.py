"""
research_core.diagnostics — public re-export of research_core.analysis (RC6).

This thin module exists so users can import from the more intuitive path:

    from research_core.diagnostics import DeterministicGapAnalyzer, GapAnalysisConfig

All names are re-exported from research_core.analysis without alteration.
"""

from research_core.analysis import (  # noqa: F401
    CoverageDiagnostics,
    DeterministicGapAnalyzer,
    DiagnosticStatus,
    DistributionDiagnostics,
    EvidenceConditionDiagnostics,
    GapAnalysisConfig,
    GapAnalysisDiagnostics,
    GapAnalysisResult,
    GapAnalyzer,
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
