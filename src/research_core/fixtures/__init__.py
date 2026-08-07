"""
Public fixture package for research-core.

Provides deterministic in-memory fixture components suitable for demos,
tests, and examples — no network, no Knowledge Layer runtime, no external
configuration required.

Usage::

    from research_core.fixtures import build_fixture_engine

    engine = build_fixture_engine()
    result = engine.run(request)
"""

from __future__ import annotations

from research_core.fixtures.engine import build_fixture_engine

__all__ = ["build_fixture_engine"]
