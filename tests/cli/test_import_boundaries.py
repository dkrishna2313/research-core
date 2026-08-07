"""Tests for import boundaries — no vendor SDKs, no heavy CLI libraries."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


def _collect_imports(source: str) -> set[str]:
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    return imports


def _cli_sources() -> list[Path]:
    cli_dir = Path(__file__).parent.parent.parent / "src" / "research_core" / "cli"
    return list(cli_dir.glob("*.py"))


BANNED_PACKAGES = {"click", "typer", "rich", "fire", "openai", "anthropic", "boto3", "httpx"}


@pytest.mark.cli
class TestNoBannedImports:
    def test_no_click(self):
        for path in _cli_sources():
            imports = _collect_imports(path.read_text())
            assert "click" not in imports, f"click imported in {path.name}"

    def test_no_typer(self):
        for path in _cli_sources():
            imports = _collect_imports(path.read_text())
            assert "typer" not in imports, f"typer imported in {path.name}"

    def test_no_rich(self):
        for path in _cli_sources():
            imports = _collect_imports(path.read_text())
            assert "rich" not in imports, f"rich imported in {path.name}"

    def test_no_fire(self):
        for path in _cli_sources():
            imports = _collect_imports(path.read_text())
            assert "fire" not in imports, f"fire imported in {path.name}"

    def test_no_llm_sdk(self):
        for path in _cli_sources():
            imports = _collect_imports(path.read_text())
            assert "openai" not in imports, f"openai imported in {path.name}"
            assert "anthropic" not in imports, f"anthropic imported in {path.name}"

    def test_no_banned_packages(self):
        for path in _cli_sources():
            imports = _collect_imports(path.read_text())
            found = imports & BANNED_PACKAGES
            assert not found, f"Banned imports {found} found in {path.name}"


@pytest.mark.cli
class TestArgparseOnly:
    def test_cli_uses_argparse(self):
        parser_path = (
            Path(__file__).parent.parent.parent / "src" / "research_core" / "cli" / "parser.py"
        )
        source = parser_path.read_text()
        assert "argparse" in source

    def test_argparse_not_swapped_out(self):
        import research_core.cli.parser as parser_mod

        assert hasattr(parser_mod, "build_parser")
        p = parser_mod.build_parser()
        assert p is not None


@pytest.mark.cli
class TestPackageImports:
    def test_cli_package_importable(self):
        import research_core.cli  # noqa: F401

    def test_main_importable(self):
        from research_core.cli.app import main  # noqa: F401

    def test_exit_code_importable(self):
        from research_core.cli.exit_codes import ExitCode  # noqa: F401

    def test_output_format_importable(self):
        from research_core.cli.config import OutputFormat  # noqa: F401

    def test_build_fixture_engine_importable(self):
        from research_core.cli.providers import build_fixture_engine  # noqa: F401

    def test_cli_init_exports(self):
        from research_core.cli import ExitCode, OutputFormat, main  # noqa: F401
