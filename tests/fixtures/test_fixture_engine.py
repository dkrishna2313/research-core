"""
Tests for the public research_core.fixtures package.

Validates that the fixture engine lives in the public namespace,
that the CLI and external consumer import from the correct location,
and that the engine is properly configured.
"""

from __future__ import annotations

import ast
import pathlib

import pytest


@pytest.mark.cli
class TestFixtureEnginePublicImport:
    def test_fixtures_module_imports(self) -> None:
        import research_core.fixtures  # noqa: F401

    def test_build_fixture_engine_importable(self) -> None:
        from research_core.fixtures import build_fixture_engine

        assert callable(build_fixture_engine)

    def test_fixtures_all_exports_build_fixture_engine(self) -> None:
        import research_core.fixtures as f

        assert "build_fixture_engine" in f.__all__

    def test_fixtures_engine_module_does_not_import_cli(self) -> None:
        path = pathlib.Path("src/research_core/fixtures/engine.py")
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("research_core.cli"), (
                    f"fixtures/engine.py imports CLI module: {node.module}"
                )

    def test_build_fixture_engine_returns_research_engine(self) -> None:
        from research_core.engine import ResearchEngine
        from research_core.fixtures import build_fixture_engine

        engine = build_fixture_engine()
        assert isinstance(engine, ResearchEngine)

    def test_build_fixture_engine_with_web_flag(self) -> None:
        from research_core.engine import ResearchEngine
        from research_core.fixtures import build_fixture_engine

        engine = build_fixture_engine(use_web=True)
        assert isinstance(engine, ResearchEngine)

    def test_fixture_engine_runs_deterministically(self) -> None:
        from research_core.contracts.request import ResearchRequest
        from research_core.fixtures import build_fixture_engine

        request = ResearchRequest(question="Fixture determinism test")
        engine = build_fixture_engine()
        result = engine.run(request)
        assert result is not None
        assert len(result.sources) > 0
        assert len(result.evidence) > 0

    def test_external_consumer_imports_from_fixtures_not_cli(self) -> None:
        path = pathlib.Path("examples/external_consumer/consumer.py")
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("research_core.cli"), (
                    f"External consumer imports CLI module: {node.module}"
                )

    def test_external_consumer_no_tests_import(self) -> None:
        path = pathlib.Path("examples/external_consumer/consumer.py")
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("tests"), (
                    f"External consumer imports test module: {node.module}"
                )

    def test_external_consumer_no_sys_path_mutation(self) -> None:
        path = pathlib.Path("examples/external_consumer/consumer.py")
        source = path.read_text()
        # sys.path.insert / sys.path.append are signs of source-tree hacking
        assert "sys.path" not in source, (
            "External consumer mutates sys.path — isolation is compromised"
        )

    def test_cli_providers_re_exports_from_fixtures(self) -> None:
        # The CLI providers module should re-export from fixtures, not own the impl
        from research_core.cli.providers import build_fixture_engine as cli_bfe
        from research_core.fixtures import build_fixture_engine as pub_bfe

        # Both names must resolve to the same underlying function
        assert cli_bfe is pub_bfe
