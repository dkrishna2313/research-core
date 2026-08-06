"""
Command implementations for the research-core CLI.

run_command() orchestrates provider construction, engine execution, and output
rendering for the 'run' subcommand. It returns (exit_code, stdout, stderr)
so that app.py controls actual I/O — this function is easier to unit-test.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import datetime

from research_core.cli.config import OutputFormat
from research_core.cli.exit_codes import ExitCode
from research_core.cli.output import render_result


def run_command(
    args: argparse.Namespace,
    *,
    clock: Callable[[], datetime] | None = None,
) -> tuple[int, str, str]:
    """Execute the 'run' subcommand.

    Returns (exit_code, stdout_content, stderr_content).
    All error messages go to stderr; the result payload goes to stdout.
    PARTIAL results are exit code 0 — they are valid research artifacts.
    """
    # 1. Validate question
    question = args.question.strip()
    if not question:
        return (
            ExitCode.INVALID_REQUEST,
            "",
            "error: research question must not be blank\n",
        )

    # 2. Determine output format
    fmt_str: str = getattr(args, "output_format", "markdown")
    try:
        fmt = OutputFormat(fmt_str)
    except ValueError:
        return (
            ExitCode.USAGE_ERROR,
            "",
            f"error: unsupported output format {fmt_str!r}; "
            "use 'markdown' or 'json'\n",
        )

    use_web: bool = getattr(args, "web", False)
    fixture_mode: bool = getattr(args, "fixture", False)
    strict_mode: bool = getattr(args, "strict", False)
    profile: str | None = getattr(args, "profile", None)

    # 3. Build engine
    if fixture_mode:
        from research_core.cli.providers import build_fixture_engine

        engine = build_fixture_engine(use_web=use_web, clock=clock)
    else:
        # Without --fixture and without external configuration, the CLI cannot
        # construct production providers. Instruct the user to use --fixture.
        return (
            ExitCode.CONFIGURATION_FAILURE,
            "",
            (
                "error: no provider configuration available.\n"
                "Use --fixture to run with deterministic in-memory providers:\n"
                "  research-core run QUESTION --fixture\n"
            ),
        )

    # 4. Build request
    from research_core.contracts.request import ResearchRequest
    from research_core.exceptions import InvalidResearchRequestError

    profiles_tuple: tuple[str, ...] = (profile,) if profile is not None else ()
    try:
        request = ResearchRequest(
            question=question,
            profiles=profiles_tuple,
            use_web=use_web,
            strict=strict_mode,
        )
    except InvalidResearchRequestError as exc:
        return ExitCode.INVALID_REQUEST, "", f"error: {exc}\n"

    # 5. Run engine
    from research_core.exceptions import (
        IncompleteResearchError,
        ProviderExecutionError,
        ProviderUnavailableError,
        ResearchCoreError,
        UnknownProfileError,
    )

    try:
        result = engine.run(request)
    except UnknownProfileError as exc:
        return (
            ExitCode.UNKNOWN_PROFILE,
            "",
            f"error: unknown profile {exc.profile_id!r}\n",
        )
    except (ProviderExecutionError, ProviderUnavailableError) as exc:
        return ExitCode.PROVIDER_FAILURE, "", f"error: provider failure — {exc}\n"
    except IncompleteResearchError as exc:
        return ExitCode.EXECUTION_FAILURE, "", f"error: research incomplete — {exc}\n"
    except ResearchCoreError as exc:
        return ExitCode.EXECUTION_FAILURE, "", f"error: research failed — {exc}\n"
    except Exception as exc:  # noqa: BLE001
        return (
            ExitCode.EXECUTION_FAILURE,
            "",
            f"error: unexpected failure during research execution — {type(exc).__name__}\n",
        )

    # 6. Render output
    try:
        output = render_result(result, fmt)
    except Exception as exc:  # noqa: BLE001
        return (
            ExitCode.OUTPUT_FAILURE,
            "",
            f"error: failed to render result — {type(exc).__name__}: {exc}\n",
        )

    return ExitCode.SUCCESS, output, ""
