"""Tests verifying lazy import and optional dependency behavior.

These tests do NOT use pytest.importorskip — they must run regardless of
whether ddgs, requests, or trafilatura are installed.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.web


class TestAdapterModuleImport:
    def test_adapter_module_importable_always(self) -> None:
        import research_core.adapters.web

        assert research_core.adapters.web is not None

    def test_web_search_adapter_importable_always(self) -> None:
        from research_core.adapters.web import WebSearchAdapter

        assert WebSearchAdapter is not None

    def test_adapters_package_importable_always(self) -> None:
        import research_core.adapters

        assert research_core.adapters is not None

    def test_construction_does_not_require_ddgs(self) -> None:
        from research_core.adapters.web import WebSearchAdapter

        with patch.dict(
            sys.modules,
            {
                "ddgs": None,  # type: ignore[dict-item]
                "duckduckgo_search": None,  # type: ignore[dict-item]
                "requests": None,  # type: ignore[dict-item]
                "trafilatura": None,  # type: ignore[dict-item]
            },
        ):
            adapter = WebSearchAdapter()
        assert adapter is not None

    def test_is_available_reflects_installation(self) -> None:
        from research_core.adapters.web import WebSearchAdapter

        expected: bool
        try:
            import ddgs  # noqa: F401

            expected = True
        except ImportError:
            try:
                import duckduckgo_search  # noqa: F401

                expected = True
            except ImportError:
                expected = False

        assert WebSearchAdapter.is_available() == expected

    def test_is_available_false_when_ddgs_absent(self) -> None:
        from research_core.adapters.web import WebSearchAdapter

        with patch.dict(
            sys.modules,
            {"ddgs": None, "duckduckgo_search": None},  # type: ignore[dict-item]
        ):
            result = WebSearchAdapter.is_available()
        assert result is False

    def test_research_core_does_not_expose_adapter(self) -> None:
        import research_core

        assert not hasattr(research_core, "WebSearchAdapter"), (
            "WebSearchAdapter must not be exposed from the top-level research_core namespace "
            "— it is an optional adapter, not a core contract"
        )

    def test_cache_importable_without_external_deps(self) -> None:
        from research_core.adapters.web.cache import WebCache

        assert WebCache is not None

    def test_models_importable_without_external_deps(self) -> None:
        from research_core.adapters.web.models import ExtractionResult, FetchedResource, SearchHit

        assert SearchHit is not None
        assert FetchedResource is not None
        assert ExtractionResult is not None
