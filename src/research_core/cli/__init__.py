"""
research_core.cli — standalone command-line interface (RC8).

The console entry point is:
    research-core run QUESTION [--fixture] [--format markdown|json]

The module entry point is:
    python -m research_core.cli

Public exports:
    main        — callable entry point; returns int exit code
    OutputFormat — output format enum (MARKDOWN, JSON)
    ExitCode    — documented exit code enum
"""

from __future__ import annotations

from research_core.cli.app import main
from research_core.cli.config import OutputFormat
from research_core.cli.exit_codes import ExitCode

__all__ = ["main", "OutputFormat", "ExitCode"]
