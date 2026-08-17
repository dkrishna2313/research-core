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

from research_core.cli.config import (
    HISTORY_DB_ENV,
    OutputFormat,
    get_history_db_path,
    resolve_knowledge_store,
    validate_knowledge_store,
)
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
    answer_only: bool = getattr(args, "answer_only", False)
    answer_plus: bool = getattr(args, "answer_plus", False)
    no_history: bool = getattr(args, "no_history", False)
    profile: str | None = getattr(args, "profile", None)
    knowledge_store_arg: str | None = getattr(args, "knowledge_store", None)

    # 3. Resolve knowledge store path (CLI arg wins over env var)
    knowledge_store_path = resolve_knowledge_store(knowledge_store_arg)

    # 3a. Fail fast if history is required but not configured
    if not no_history and get_history_db_path() is None:
        return (
            ExitCode.HISTORY_FAILURE,
            "",
            f"error: {HISTORY_DB_ENV} is not set.\n"
            "Set it to the path for your history database before running queries:\n"
            f"  export {HISTORY_DB_ENV}=~/.research_core/history.db\n"
            "Or pass --no-history to skip recording this query.\n",
        )

    # 4. Conflict detection
    if answer_only and answer_plus:
        return (
            ExitCode.CONFIGURATION_FAILURE,
            "",
            "error: --answer-only and --answer-plus are mutually exclusive.\n",
        )

    if (answer_only or answer_plus) and fmt == OutputFormat.JSON:
        flag = "--answer-only" if answer_only else "--answer-plus"
        return (
            ExitCode.CONFIGURATION_FAILURE,
            "",
            f"error: {flag} is only supported with Markdown output.\n",
        )

    if fixture_mode and knowledge_store_path is not None:
        return (
            ExitCode.CONFIGURATION_FAILURE,
            "",
            (
                "error: --fixture and --knowledge-store are mutually exclusive.\n"
                "Use --fixture for deterministic in-memory providers or\n"
                "--knowledge-store PATH for live Knowledge Layer execution.\n"
            ),
        )

    if knowledge_store_path is not None and use_web:
        return (
            ExitCode.CONFIGURATION_FAILURE,
            "",
            (
                "error: --web is not supported in live knowledge mode.\n"
                "Remove --web, or use --fixture --web for fixture-based web retrieval.\n"
            ),
        )

    # 5. Build engine
    if fixture_mode:
        from research_core.cli.providers import build_fixture_engine

        engine = build_fixture_engine(use_web=use_web, clock=clock)

    elif knowledge_store_path is not None:
        err = validate_knowledge_store(knowledge_store_path)
        if err is not None:
            return ExitCode.CONFIGURATION_FAILURE, "", f"error: {err}\n"

        from research_core.cli.providers import build_live_knowledge_engine

        engine = build_live_knowledge_engine(knowledge_store_path, clock=clock)

    else:
        return (
            ExitCode.CONFIGURATION_FAILURE,
            "",
            (
                "error: no provider configuration available.\n"
                "Use --fixture to run with deterministic in-memory providers:\n"
                "  research-core run QUESTION --fixture\n"
                "Or use --knowledge-store PATH to run against a Knowledge Layer store:\n"
                "  research-core run QUESTION --knowledge-store /path/to/knowledge_store\n"
            ),
        )

    # 6. Build request
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

    # 7. Run engine
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

    # 8. Render output
    try:
        output = render_result(result, fmt, answer_only=answer_only, answer_plus=answer_plus)
    except Exception as exc:  # noqa: BLE001
        return (
            ExitCode.OUTPUT_FAILURE,
            "",
            f"error: failed to render result — {type(exc).__name__}: {exc}\n",
        )

    # 9. Save to history (non-fatal on failure)
    history_warning = ""
    if not no_history:
        history_db_path = get_history_db_path()
        if history_db_path is not None:
            try:
                from research_core.history.store import HistoryStore
                HistoryStore(history_db_path).save(result)
            except Exception as exc:  # noqa: BLE001
                history_warning = f"warning: failed to save query to history — {exc}\n"

    return ExitCode.SUCCESS, output, history_warning


def history_command(args: argparse.Namespace) -> tuple[int, str, str]:
    """Execute the 'history' subcommand.

    Returns (exit_code, stdout_content, stderr_content).
    """
    from research_core.cli.config import HISTORY_DB_ENV, get_history_db_path
    from research_core.history.store import HistoryStore, format_history_table

    db_path = get_history_db_path()
    if db_path is None:
        return (
            ExitCode.HISTORY_FAILURE,
            "",
            f"error: {HISTORY_DB_ENV} is not set.\n"
            "Set it to the path of your history database:\n"
            f"  export {HISTORY_DB_ENV}=~/.research_core/history.db\n",
        )

    try:
        store = HistoryStore(db_path)
    except Exception as exc:  # noqa: BLE001
        return (
            ExitCode.HISTORY_FAILURE,
            "",
            f"error: could not open history database at {db_path} — {exc}\n",
        )

    delete_id: str | None = getattr(args, "delete_id", None)
    if delete_id is not None:
        ok, detail = store.delete(delete_id)
        if not ok:
            return ExitCode.USAGE_ERROR, "", f"error: {detail}\n"
        return ExitCode.SUCCESS, f"Deleted history entry {detail[:8]}.\n", ""

    limit: int = getattr(args, "limit", 20)
    profile: str | None = getattr(args, "profile", None)

    records = store.list_queries(limit=limit, profile=profile)
    if not records:
        msg = "No history entries found"
        if profile:
            msg += f" for profile {profile!r}"
        return ExitCode.SUCCESS, msg + ".\n", ""

    return ExitCode.SUCCESS, format_history_table(records), ""
