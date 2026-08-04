"""
Web search adapter for research-core.

Provides WebSearchAdapter — a WebSearchProvider backed by DuckDuckGo search
and requests/trafilatura page fetching.

Installation:
    pip install "research-core[web]"

Lazy import contract:
    Importing this package does NOT require ddgs, requests, trafilatura, pypdf,
    or python-docx. Those packages are imported lazily at search() time.
    Missing required packages raise ProviderUnavailableError at runtime.
"""

from __future__ import annotations

from research_core.adapters.web.adapter import WebSearchAdapter

__all__ = ["WebSearchAdapter"]
