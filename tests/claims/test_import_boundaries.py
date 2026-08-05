"""AST-based scan to ensure the claims package has no banned external dependencies."""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.claims

CLAIMS_PKG = Path(__file__).parents[2] / "src" / "research_core" / "claims"

BANNED = {
    "requests",
    "httpx",
    "aiohttp",
    "ddgs",
    "duckduckgo_search",
    "trafilatura",
    "pypdf",
    "docx",
    "python_docx",
    "docx2txt",
    "knowledge",
    "openai",
    "anthropic",
    "langchain",
    "transformers",
    "spacy",
    "nltk",
    "sklearn",
    "torch",
    "tensorflow",
    "numpy",
    "pandas",
    "scipy",
}


def _collect_imports(source: str) -> list[str]:
    """Return all top-level module names imported in the given source."""
    tree = ast.parse(source)
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module.split(".")[0])
    return names


def _scan_package() -> dict[str, list[str]]:
    """Return {filename: [banned_module, ...]} for all .py files in claims package."""
    violations: dict[str, list[str]] = {}
    for dirpath, _, filenames in os.walk(CLAIMS_PKG):
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            fpath = Path(dirpath) / fname
            source = fpath.read_text(encoding="utf-8")
            imports = _collect_imports(source)
            bad = [m for m in imports if m in BANNED]
            if bad:
                rel = str(fpath.relative_to(CLAIMS_PKG.parent.parent.parent.parent))
                violations[rel] = bad
    return violations


def test_no_banned_imports_in_claims_package() -> None:
    violations = _scan_package()
    if violations:
        lines = []
        for path, modules in violations.items():
            lines.append(f"  {path}: {', '.join(modules)}")
        msg = "Banned imports found in claims package:\n" + "\n".join(lines)
        pytest.fail(msg)


def test_no_network_imports() -> None:
    network_banned = {"requests", "httpx", "aiohttp", "urllib3", "ddgs", "duckduckgo_search"}
    for dirpath, _, filenames in os.walk(CLAIMS_PKG):
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            fpath = Path(dirpath) / fname
            source = fpath.read_text(encoding="utf-8")
            imports = _collect_imports(source)
            for m in imports:
                if m in network_banned:
                    rel = str(fpath.relative_to(CLAIMS_PKG))
                    pytest.fail(f"Network import '{m}' found in claims/{rel}")


def test_no_llm_imports() -> None:
    llm_banned = {"openai", "anthropic", "langchain", "litellm", "cohere"}
    for dirpath, _, filenames in os.walk(CLAIMS_PKG):
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            fpath = Path(dirpath) / fname
            source = fpath.read_text(encoding="utf-8")
            imports = _collect_imports(source)
            for m in imports:
                if m in llm_banned:
                    rel = str(fpath.relative_to(CLAIMS_PKG))
                    pytest.fail(f"LLM import '{m}' found in claims/{rel}")


def test_no_nlp_library_imports() -> None:
    nlp_banned = {"spacy", "nltk", "transformers", "stanza", "flair"}
    for dirpath, _, filenames in os.walk(CLAIMS_PKG):
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            fpath = Path(dirpath) / fname
            source = fpath.read_text(encoding="utf-8")
            imports = _collect_imports(source)
            for m in imports:
                if m in nlp_banned:
                    rel = str(fpath.relative_to(CLAIMS_PKG))
                    pytest.fail(f"NLP library import '{m}' found in claims/{rel}")


def test_claims_package_files_exist() -> None:
    expected_files = [
        "__init__.py",
        "contracts.py",
        "config.py",
        "extractor.py",
        "_candidate.py",
        "_classify.py",
        "_deduplicate.py",
    ]
    for fname in expected_files:
        assert (CLAIMS_PKG / fname).exists(), f"Expected {fname} missing from claims package"
