"""
CLI configuration types.

OutputFormat controls how the ResearchResult is written to stdout.
"""

from __future__ import annotations

from enum import StrEnum


class OutputFormat(StrEnum):
    """Output format for the run command.

    MARKDOWN — human-readable Markdown (default).
    JSON     — machine-readable JSON; full ResearchResult serialized.
    """

    MARKDOWN = "markdown"
    JSON = "json"
