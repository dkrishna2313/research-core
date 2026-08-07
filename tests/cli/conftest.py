"""
Shared fixtures for CLI tests.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from research_core.cli.app import main

FIXED_TS = datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)


@pytest.fixture
def fixed_clock():
    return lambda: FIXED_TS


@pytest.fixture
def cli_main():
    return main
