"""
CLI argument parser for research-core.

Build the argparse parser. Does not execute any logic.
"""

from __future__ import annotations

import argparse

import research_core


def build_parser() -> argparse.ArgumentParser:
    """Return the fully configured root argument parser."""
    parser = argparse.ArgumentParser(
        prog="research-core",
        description=(
            "research-core: domain-neutral research pipeline. "
            "Run research questions through the evidence pipeline and render results."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"research-core {research_core.__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # --- run subcommand ---
    run_parser = subparsers.add_parser(
        "run",
        help="Run the research pipeline for a question.",
        description=(
            "Run the research pipeline for QUESTION and write the result to stdout.\n\n"
            "Default output format is Markdown. Use --format json for machine-readable output.\n"
            "Use --fixture to run with deterministic in-memory providers (no network required)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    run_parser.add_argument(
        "question",
        metavar="QUESTION",
        help="The research question (non-empty string).",
    )
    run_parser.add_argument(
        "--profile",
        metavar="PROFILE_ID",
        dest="profile",
        default=None,
        help=(
            "Profile identifier to pass to the configured ProfileProvider. "
            "In fixture mode, 'fixture' is always recognized."
        ),
    )
    run_parser.add_argument(
        "--web",
        action="store_true",
        default=False,
        help="Enable web retrieval (requires a configured WebSearchProvider or --fixture).",
    )
    run_parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        dest="output_format",
        metavar="{markdown,json}",
        help=(
            "Output format: 'markdown' (default, human-readable) or "
            "'json' (machine-readable, full result graph)."
        ),
    )
    run_parser.add_argument(
        "--fixture",
        action="store_true",
        default=False,
        help=(
            "Use deterministic in-memory fixture providers. "
            "No network access or Knowledge Layer runtime required. "
            "Suitable for testing, demos, and offline use."
        ),
    )
    run_parser.add_argument(
        "--strict",
        action="store_true",
        default=False,
        help=(
            "Raise an error instead of returning a partial result. "
            "Exit code 6 (EXECUTION_FAILURE) when the pipeline would be partial."
        ),
    )

    return parser
