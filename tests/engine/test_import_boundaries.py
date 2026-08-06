"""
Import boundary tests for the engine module.

The engine must not import any LLM SDK, vendor adapter, or rendering library.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_ENGINE_SRC = (
    Path(__file__).parent.parent.parent
    / "src"
    / "research_core"
    / "engine.py"
)

_PROHIBITED = [
    "openai",
    "anthropic",
    "google.generativeai",
    "boto3",
    "langchain",
    "llama_index",
    "haystack",
    "transformers",
    "sentence_transformers",
    "numpy",
    "pandas",
    "jinja2",
    "markdown",
    "mistune",
    "rich",
]


@pytest.mark.engine
class TestEngineImportBoundaries:
    def test_engine_imports_no_llm_sdk(self) -> None:
        source = _ENGINE_SRC.read_text()
        tree = ast.parse(source)
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        for prohibited in _PROHIBITED:
            assert not any(
                imp.startswith(prohibited) for imp in imported
            ), f"engine.py must not import {prohibited!r}"

    def test_engine_imports_no_adapters(self) -> None:
        source = _ENGINE_SRC.read_text()
        assert "research_core.adapters" not in source

    def test_engine_importable_without_optional_deps(self) -> None:
        import research_core.engine  # noqa: F401 — must not raise

    def test_research_engine_class_exists(self) -> None:
        from research_core.engine import ResearchEngine

        assert ResearchEngine is not None
