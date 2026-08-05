"""
Tests for the public API exposed via research_core.diagnostics.
"""

from __future__ import annotations

import pytest


@pytest.mark.diagnostics
class TestDiagnosticsPublicApi:
    def test_import_gap_analyzer(self) -> None:
        from research_core.diagnostics import GapAnalyzer

        assert GapAnalyzer is not None

    def test_import_deterministic_gap_analyzer(self) -> None:
        from research_core.diagnostics import DeterministicGapAnalyzer

        assert DeterministicGapAnalyzer is not None

    def test_import_gap_analysis_config(self) -> None:
        from research_core.diagnostics import GapAnalysisConfig

        assert GapAnalysisConfig is not None

    def test_import_gap_analysis_result(self) -> None:
        from research_core.diagnostics import GapAnalysisResult

        assert GapAnalysisResult is not None

    def test_import_quality_diagnostics_result(self) -> None:
        from research_core.diagnostics import QualityDiagnosticsResult

        assert QualityDiagnosticsResult is not None

    def test_import_gap_analysis_diagnostics(self) -> None:
        from research_core.diagnostics import GapAnalysisDiagnostics

        assert GapAnalysisDiagnostics is not None

    def test_import_diagnostic_status(self) -> None:
        from research_core.diagnostics import DiagnosticStatus

        assert DiagnosticStatus is not None

    def test_import_quality_dimension_summary(self) -> None:
        from research_core.diagnostics import QualityDimensionSummary

        assert QualityDimensionSummary is not None

    def test_import_coverage_diagnostics(self) -> None:
        from research_core.diagnostics import CoverageDiagnostics

        assert CoverageDiagnostics is not None

    def test_import_distribution_diagnostics(self) -> None:
        from research_core.diagnostics import DistributionDiagnostics

        assert DistributionDiagnostics is not None

    def test_import_evidence_condition_diagnostics(self) -> None:
        from research_core.diagnostics import EvidenceConditionDiagnostics

        assert EvidenceConditionDiagnostics is not None


@pytest.mark.diagnostics
class TestAnalysisPublicApi:
    def test_all_names_in_analysis_all(self) -> None:
        import research_core.analysis as analysis_mod

        expected = {
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
        }
        missing = expected - set(analysis_mod.__all__)
        assert not missing, f"Missing from __all__: {missing}"

    def test_diagnostics_all_matches_analysis_all(self) -> None:
        import research_core.analysis as analysis_mod
        import research_core.diagnostics as diag_mod

        assert set(analysis_mod.__all__) == set(diag_mod.__all__)

    def test_diagnostics_names_are_same_objects(self) -> None:
        from research_core.analysis import DeterministicGapAnalyzer as a
        from research_core.diagnostics import DeterministicGapAnalyzer as d

        assert a is d
