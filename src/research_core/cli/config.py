"""
CLI configuration types and knowledge-store utilities.

OutputFormat controls how the ResearchResult is written to stdout.
resolve_knowledge_store() and validate_knowledge_store() manage the live
knowledge store path from CLI arg or environment variable.
"""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path

KNOWLEDGE_STORE_ENV = "RESEARCH_CORE_KNOWLEDGE_STORE"
"""Environment variable that sets the knowledge store path when --knowledge-store is omitted."""

HISTORY_DB_ENV = "RESEARCH_CORE_HISTORY_DB"
"""Environment variable that sets the path to the SQLite history database.

Must be set when running 'research-core run' unless --no-history is passed.
Example: export RESEARCH_CORE_HISTORY_DB=~/.research_core/history.db
"""


def get_history_db_path() -> Path | None:
    """Return the history DB path from the environment variable, or None if unset."""
    val = os.environ.get(HISTORY_DB_ENV, "").strip()
    return Path(val) if val else None


class OutputFormat(StrEnum):
    """Output format for the run command.

    MARKDOWN — human-readable Markdown (default).
    JSON     — machine-readable JSON; full ResearchResult serialized.
    """

    MARKDOWN = "markdown"
    JSON = "json"


def resolve_knowledge_store(cli_path: str | None) -> Path | None:
    """Return the knowledge store Path from the CLI arg or env var, or None if neither is set.

    CLI arg takes priority over the environment variable.
    """
    if cli_path is not None:
        return Path(cli_path)
    env_val = os.environ.get(KNOWLEDGE_STORE_ENV)
    if env_val is not None:
        return Path(env_val)
    return None


def validate_knowledge_store(path: Path) -> str | None:
    """Return an error message string if *path* is not a valid knowledge store directory.

    Returns None when the path is valid (exists and is a directory).
    """
    if not path.exists():
        return f"knowledge store path does not exist: {path}"
    if not path.is_dir():
        return f"knowledge store path is not a directory: {path}"
    return None
