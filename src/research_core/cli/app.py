"""
research-core CLI entry point.

main() is the console-script target registered in pyproject.toml:
    research-core = "research_core.cli.app:main"

It is also reachable as a module entry point:
    python -m research_core.cli
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from research_core.cli.exit_codes import ExitCode
from research_core.cli.parser import build_parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse *argv* (defaults to sys.argv[1:]) and dispatch to the appropriate command.

    Returns an integer exit code. Never raises except KeyboardInterrupt.
    Writes result payload to stdout; error messages to stderr.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help(sys.stderr)
        return ExitCode.USAGE_ERROR

    if args.command == "run":
        from research_core.cli.commands import run_command

        exit_code, stdout_content, stderr_content = run_command(args)
        if stdout_content:
            sys.stdout.write(stdout_content)
        if stderr_content:
            sys.stderr.write(stderr_content)
        return exit_code

    if args.command == "history":
        from research_core.cli.commands import history_command

        exit_code, stdout_content, stderr_content = history_command(args)
        if stdout_content:
            sys.stdout.write(stdout_content)
        if stderr_content:
            sys.stderr.write(stderr_content)
        return exit_code

    # Unknown subcommand (should not happen with argparse, but be defensive)
    sys.stderr.write(f"error: unknown command {args.command!r}\n")
    return ExitCode.USAGE_ERROR
