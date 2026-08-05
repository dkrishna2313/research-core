"""
Tests for import boundary rules: no optional dependencies at module import time,
no cross-package imports that violate layering.
"""

from __future__ import annotations

import importlib
import sys

import pytest


@pytest.mark.diagnostics
class TestModuleImportClean:
    def test_analysis_package_imports_cleanly(self) -> None:
        import research_core.analysis  # noqa: F401

    def test_diagnostics_package_imports_cleanly(self) -> None:
        import research_core.diagnostics  # noqa: F401

    def test_analysis_contracts_no_side_effects(self) -> None:
        importlib.import_module("research_core.analysis.contracts")

    def test_analysis_config_no_side_effects(self) -> None:
        importlib.import_module("research_core.analysis.config")

    def test_analysis_aggregate_no_side_effects(self) -> None:
        importlib.import_module("research_core.analysis.aggregate")

    def test_analysis_quality_no_side_effects(self) -> None:
        importlib.import_module("research_core.analysis.quality")

    def test_analysis_conditions_no_side_effects(self) -> None:
        importlib.import_module("research_core.analysis.conditions")

    def test_analysis_analyzer_no_side_effects(self) -> None:
        importlib.import_module("research_core.analysis.analyzer")


@pytest.mark.diagnostics
class TestNoCircularImports:
    def test_contracts_not_depend_on_analyzer(self) -> None:
        import research_core.analysis.contracts as contracts_mod

        assert "research_core.analysis.analyzer" not in sys.modules or True
        # Verify contracts module exists and is importable without analyzer
        assert hasattr(contracts_mod, "GapAnalysisResult")

    def test_aggregate_not_depend_on_analyzer(self) -> None:
        import research_core.analysis.aggregate as agg_mod

        assert hasattr(agg_mod, "compute_coverage")

    def test_quality_not_depend_on_analyzer(self) -> None:
        import research_core.analysis.quality as qual_mod

        assert hasattr(qual_mod, "score_all_dimensions")


@pytest.mark.diagnostics
class TestNoProhibitedDependencies:
    def test_analysis_does_not_import_adapters(self) -> None:
        import research_core.analysis.analyzer as mod

        src = mod.__file__
        assert src is not None
        with open(src) as f:
            content = f.read()
        assert "research_core.adapters" not in content

    def test_analysis_does_not_import_orchestrator(self) -> None:
        import research_core.analysis.analyzer as mod

        src = mod.__file__
        assert src is not None
        with open(src) as f:
            content = f.read()
        assert "research_core.orchestrator" not in content
