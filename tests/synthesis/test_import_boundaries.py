"""
Import boundary tests for the synthesis package.

Synthesis must not import any LLM SDK, network library, or adapter.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_SYNTHESIS_DIR = (
    Path(__file__).parent.parent.parent
    / "src"
    / "research_core"
    / "synthesis"
)

_PROHIBITED = [
    "openai",
    "anthropic",
    "google.generativeai",
    "boto3",
    "langchain",
    "llama_index",
    "requests",
    "ddgs",
    "trafilatura",
    "numpy",
    "pandas",
    "jinja2",
    "markdown",
    "mistune",
    "rich",
]


def _collect_imports(path: Path) -> list[str]:
    source = path.read_text()
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return imported


@pytest.mark.synthesis
class TestSynthesisImportBoundaries:
    def test_synthesis_imports_no_llm_sdk(self) -> None:
        # llm.py is intentionally an LLM integration — skip it here.
        # Its anthropic import is TYPE_CHECKING-only; the actual import
        # is lazy inside _get_client() so the module is usable without anthropic installed.
        for py_file in _SYNTHESIS_DIR.glob("*.py"):
            if py_file.name == "llm.py":
                continue
            imports = _collect_imports(py_file)
            for prohibited in _PROHIBITED:
                assert not any(
                    imp.startswith(prohibited) for imp in imports
                ), f"{py_file.name} must not import {prohibited!r}"

    def test_synthesis_imports_no_adapters(self) -> None:
        for py_file in _SYNTHESIS_DIR.glob("*.py"):
            source = py_file.read_text()
            assert "research_core.adapters" not in source

    def test_synthesis_importable_without_optional_deps(self) -> None:
        import research_core.synthesis as s  # noqa: F401

    def test_deterministic_synthesizer_importable(self) -> None:
        from research_core.synthesis import DeterministicSynthesizer

        assert DeterministicSynthesizer is not None

    def test_llm_synthesizer_importable(self) -> None:
        from research_core.synthesis import LLMSynthesizer

        assert LLMSynthesizer is not None
