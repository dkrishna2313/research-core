"""
Shared fixtures for CLI tests.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest

from research_core.cli.app import main

FIXED_TS = datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def history_db_env(tmp_path):
    """Point RESEARCH_CORE_HISTORY_DB at a per-test temp file for all CLI tests.

    This satisfies the env-var requirement without coupling individual tests
    to the history feature.
    """
    db_path = tmp_path / "test_history.db"
    old = os.environ.get("RESEARCH_CORE_HISTORY_DB")
    os.environ["RESEARCH_CORE_HISTORY_DB"] = str(db_path)
    yield db_path
    if old is None:
        os.environ.pop("RESEARCH_CORE_HISTORY_DB", None)
    else:
        os.environ["RESEARCH_CORE_HISTORY_DB"] = old


@pytest.fixture
def fixed_clock():
    return lambda: FIXED_TS


@pytest.fixture
def cli_main():
    return main
