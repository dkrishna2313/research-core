"""
RC0 foundation tests.

These tests verify structural properties of the repository that are checkable
without any engine implementation. They do not mock or stub a nonexistent engine.
"""

import importlib
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SRC_ROOT = REPO_ROOT / "src" / "research_core"
DOCS_ROOT = REPO_ROOT / "docs"

REQUIRED_DOCS = [
    DOCS_ROOT / "product" / "PRODUCT_BRIEF.md",
    DOCS_ROOT / "architecture" / "ARCHITECTURE.md",
    DOCS_ROOT / "architecture" / "DEPENDENCY_RULES.md",
    DOCS_ROOT / "architecture" / "ROADMAP.md",
]

# Strings that must appear somewhere in the documentation set.
REQUIRED_ARCHITECTURAL_STATEMENTS = [
    # Canonical structured result
    "ResearchResult",
    # Pipeline stages
    "ResearchRequest",
    # Evidence model
    "EvidenceItem",
    "Claim",
    "Contradiction",
    "ResearchGap",
    # Dependency direction
    "knowledge-layer",
    # Renderer separation
    "Markdown",
    # No silent fallback
    "silent",
    # Quality model
    "quality_diagnostics",
]

PROHIBITED_RUNTIME_IMPORTS = [
    "functional_agents",
    "strategy",
    "editorial",
    "deliverables",
    "recommendations",
    "decision_models",
    "research_agent.cli",
]

# Modules that must NOT exist in the source package (premature implementation).
# research_core.contracts and research_core.protocols are intentional RC1 deliverables.
# research_core.engine, synthesis, and renderers are intentional RC7 deliverables.
# Only modules from future phases remain in this list.
PREMATURE_IMPLEMENTATION_MODULES = [
    "research_core.providers",
    "research_core.cli",
]

# Modules that MUST exist as of RC1.
RC1_REQUIRED_MODULES = [
    "research_core.contracts",
    "research_core.protocols",
    "research_core.exceptions",
]


class TestPackageImport:
    def test_package_imports_cleanly(self) -> None:
        """research_core must be importable without any side effects."""
        if "research_core" in sys.modules:
            del sys.modules["research_core"]
        mod = importlib.import_module("research_core")
        assert mod is not None

    def test_version_attribute_exists(self) -> None:
        import research_core

        assert hasattr(research_core, "__version__")
        assert isinstance(research_core.__version__, str)

    def test_import_does_not_trigger_filesystem_access(self) -> None:
        """Verify __init__.py contains no open() or pathlib calls.

        We check the source rather than the import side effects to keep this test
        deterministic and fast.
        """
        init_path = SRC_ROOT / "__init__.py"
        source = init_path.read_text()
        assert "open(" not in source, "__init__.py must not call open()"
        assert "Path(" not in source, "__init__.py must not use pathlib.Path"

    def test_import_does_not_contain_network_calls(self) -> None:
        init_path = SRC_ROOT / "__init__.py"
        source = init_path.read_text()
        assert "requests" not in source
        assert "urllib" not in source
        assert "httpx" not in source

    def test_import_does_not_contain_env_reads(self) -> None:
        init_path = SRC_ROOT / "__init__.py"
        source = init_path.read_text()
        assert "os.environ" not in source
        assert "os.getenv" not in source


class TestRequiredDocumentationExists:
    def test_product_brief_exists(self) -> None:
        assert (DOCS_ROOT / "product" / "PRODUCT_BRIEF.md").exists()

    def test_architecture_doc_exists(self) -> None:
        assert (DOCS_ROOT / "architecture" / "ARCHITECTURE.md").exists()

    def test_dependency_rules_exist(self) -> None:
        assert (DOCS_ROOT / "architecture" / "DEPENDENCY_RULES.md").exists()

    def test_roadmap_exists(self) -> None:
        assert (DOCS_ROOT / "architecture" / "ROADMAP.md").exists()

    def test_readme_exists(self) -> None:
        assert (REPO_ROOT / "README.md").exists()

    def test_pyproject_toml_exists(self) -> None:
        assert (REPO_ROOT / "pyproject.toml").exists()


class TestArchitecturalStatements:
    """Verify that required architectural concepts appear in the documentation."""

    def _all_docs_text(self) -> str:
        texts = []
        for path in REQUIRED_DOCS:
            if path.exists():
                texts.append(path.read_text())
        return "\n".join(texts)

    def test_required_concepts_documented(self) -> None:
        docs_text = self._all_docs_text()
        missing = [s for s in REQUIRED_ARCHITECTURAL_STATEMENTS if s not in docs_text]
        assert missing == [], f"Missing architectural statements in documentation: {missing}"

    def test_roadmap_covers_rc0_through_rc9(self) -> None:
        roadmap = (DOCS_ROOT / "architecture" / "ROADMAP.md").read_text()
        for phase in [f"RC{i}" for i in range(10)]:
            assert phase in roadmap, f"Roadmap does not mention {phase}"

    def test_roadmap_has_acceptance_criteria(self) -> None:
        roadmap = (DOCS_ROOT / "architecture" / "ROADMAP.md").read_text()
        assert "Acceptance Criteria" in roadmap

    def test_roadmap_has_exit_criteria(self) -> None:
        roadmap = (DOCS_ROOT / "architecture" / "ROADMAP.md").read_text()
        assert "Exit Criteria" in roadmap

    def test_no_silent_profile_fallback_documented(self) -> None:
        dep_rules = (DOCS_ROOT / "architecture" / "DEPENDENCY_RULES.md").read_text()
        arch = (DOCS_ROOT / "architecture" / "ARCHITECTURE.md").read_text()
        combined = dep_rules + arch
        assert "profile" in combined.lower()
        assert "fallback" in combined.lower() or "silent" in combined.lower()

    def test_markdown_described_as_renderer(self) -> None:
        arch = (DOCS_ROOT / "architecture" / "ARCHITECTURE.md").read_text()
        assert "renderer" in arch.lower()
        assert "Markdown" in arch

    def test_contradiction_types_documented(self) -> None:
        arch = (DOCS_ROOT / "architecture" / "ARCHITECTURE.md").read_text()
        for concept in ["numeric", "temporal", "definition", "scope", "methodology"]:
            assert concept in arch.lower(), f"Contradiction type '{concept}' not documented"

    def test_quality_model_is_multidimensional(self) -> None:
        brief = (DOCS_ROOT / "product" / "PRODUCT_BRIEF.md").read_text()
        for dimension in ["relevance", "authority", "recency", "corroboration", "coverage"]:
            assert dimension in brief.lower(), (
                f"Quality dimension '{dimension}' not in product brief"
            )


class TestProhibitedImports:
    """Verify that prohibited modules are not imported by the package."""

    def _get_research_core_module(self) -> types.ModuleType:
        return importlib.import_module("research_core")

    def test_prohibited_modules_not_in_research_core_namespace(self) -> None:
        mod = self._get_research_core_module()
        for prohibited in PROHIBITED_RUNTIME_IMPORTS:
            top_level = prohibited.split(".")[0]
            assert not hasattr(mod, top_level), (
                f"research_core namespace exposes prohibited module: {top_level}"
            )

    def test_prohibited_modules_not_in_init_source(self) -> None:
        init_path = SRC_ROOT / "__init__.py"
        source = init_path.read_text()
        for prohibited in PROHIBITED_RUNTIME_IMPORTS:
            top_level = prohibited.split(".")[0]
            assert f"import {top_level}" not in source, (
                f"__init__.py imports prohibited module: {top_level}"
            )
            assert f"from {top_level}" not in source, (
                f"__init__.py imports from prohibited module: {top_level}"
            )


class TestNoPrematureImplementation:
    """Verify that no premature engine implementation modules exist."""

    def test_premature_modules_do_not_exist(self) -> None:
        for module_name in PREMATURE_IMPLEMENTATION_MODULES:
            # Convert dotted name to path
            relative = module_name.replace(".", "/")
            as_package = SRC_ROOT.parent / (relative + "/__init__.py")
            as_module = SRC_ROOT.parent / (relative + ".py")
            assert not as_package.exists(), (
                f"Premature implementation found: {as_package}"
            )
            assert not as_module.exists(), (
                f"Premature implementation found: {as_module}"
            )

    def test_rc1_required_modules_exist(self) -> None:
        """RC1 deliverables — contracts, protocols, exceptions — must be present."""
        for module_name in RC1_REQUIRED_MODULES:
            relative = module_name.replace(".", "/")
            as_package = SRC_ROOT.parent / (relative + "/__init__.py")
            as_module = SRC_ROOT.parent / (relative + ".py")
            assert as_package.exists() or as_module.exists(), (
                f"Required RC1 module missing: {module_name}"
            )
