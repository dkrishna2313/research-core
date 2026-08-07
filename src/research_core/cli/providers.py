"""
CLI-internal provider module — thin compatibility re-export.

The fixture engine implementation lives in the public package:
    research_core.fixtures

External consumers should import from there::

    from research_core.fixtures import build_fixture_engine

This module re-exports build_fixture_engine so existing CLI internals and
tests that import from research_core.cli.providers continue to work.
The implementation itself does NOT live here.
"""

from __future__ import annotations

from research_core.fixtures.engine import (
    FIXTURE_CLOCK_TS,
    FIXTURE_PROFILE_IDS,
    build_fixture_engine,
)

__all__ = ["build_fixture_engine", "FIXTURE_CLOCK_TS", "FIXTURE_PROFILE_IDS"]
