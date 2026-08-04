"""Tests verifying that the adapter module imports cleanly without the knowledge package.

These tests do NOT use pytest.importorskip — they must run regardless of whether
the knowledge package is installed, because their purpose is to verify the lazy
import contract.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.knowledge


class TestAdapterModuleImport:
    def test_adapter_module_importable_always(self) -> None:
        import research_core.adapters.knowledge

        assert research_core.adapters.knowledge is not None

    def test_knowledge_adapter_class_importable_always(self) -> None:
        from research_core.adapters.knowledge import KnowledgeAdapter

        assert KnowledgeAdapter is not None

    def test_adapter_package_init_importable_always(self) -> None:
        import research_core.adapters

        assert research_core.adapters is not None

    def test_is_available_returns_true_when_knowledge_installed(self) -> None:
        from research_core.adapters.knowledge import KnowledgeAdapter

        try:
            import knowledge  # noqa: F401

            expected = True
        except ImportError:
            expected = False

        assert KnowledgeAdapter.is_available() == expected

    def test_is_available_returns_false_when_knowledge_absent(self) -> None:
        from research_core.adapters.knowledge import KnowledgeAdapter

        with patch.dict(sys.modules, {"knowledge": None}):  # type: ignore[dict-item]
            result = KnowledgeAdapter.is_available()
        assert result is False

    def test_construction_does_not_require_knowledge(self, tmp_path: Path) -> None:
        from research_core.adapters.knowledge import KnowledgeAdapter

        with patch.dict(
            sys.modules,
            {"knowledge": None, "knowledge.retriever": None, "knowledge.store": None},  # type: ignore[dict-item]
        ):
            adapter = KnowledgeAdapter(store_root=tmp_path)
        assert adapter is not None

    def test_research_core_import_does_not_expose_adapter(self) -> None:
        import research_core

        assert not hasattr(research_core, "KnowledgeAdapter"), (
            "KnowledgeAdapter must not be exposed from the top-level research_core namespace "
            "— it is an optional adapter, not a core contract"
        )
