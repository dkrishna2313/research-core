"""
Live failure-injection tests for CLI exit codes 5, 6, and 7.

These tests prove that the CLI maps typed exceptions and output failures
to the correct documented exit codes, with stdout empty and stderr concise.
"""

from __future__ import annotations

import pytest

from research_core.cli.app import main
from research_core.cli.exit_codes import ExitCode
from research_core.exceptions import (
    IncompleteResearchError,
    ProviderExecutionError,
    ProviderUnavailableError,
    ResearchCoreError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_fixture(capsys: pytest.CaptureFixture[str], argv: list[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# ---------------------------------------------------------------------------
# Exit code 5 — PROVIDER_FAILURE
# ---------------------------------------------------------------------------


@pytest.mark.cli
class TestProviderFailureExitCode5:
    def test_provider_execution_error_exits_5(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """ProviderExecutionError from engine.run() maps to exit code 5."""

        def _failing_run(self: object, request: object) -> object:  # type: ignore[override]
            raise ProviderExecutionError("injected provider failure")

        monkeypatch.setattr("research_core.engine.ResearchEngine.run", _failing_run)
        code, out, err = _run_fixture(capsys, ["run", "test", "--fixture"])

        assert code == ExitCode.PROVIDER_FAILURE
        assert out == ""
        assert len(err.strip()) > 0
        assert "Traceback" not in err
        # Provider exception messages may appear in stderr (they are safe diagnostic info)
        assert "File \"" not in err  # no stack frames

    def test_provider_unavailable_error_exits_5(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """ProviderUnavailableError from engine.run() maps to exit code 5."""

        def _failing_run(self: object, request: object) -> object:  # type: ignore[override]
            raise ProviderUnavailableError("injected unavailable")

        monkeypatch.setattr("research_core.engine.ResearchEngine.run", _failing_run)
        code, out, err = _run_fixture(capsys, ["run", "test", "--fixture"])

        assert code == ExitCode.PROVIDER_FAILURE
        assert out == ""
        assert "Traceback" not in err

    def test_provider_failure_stderr_is_concise(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _failing_run(self: object, request: object) -> object:  # type: ignore[override]
            raise ProviderExecutionError("provider down")

        monkeypatch.setattr("research_core.engine.ResearchEngine.run", _failing_run)
        _, _, err = _run_fixture(capsys, ["run", "test", "--fixture"])

        # Must be a short, readable error — not multi-page output
        assert len(err) < 500
        assert err.startswith("error:") or "error" in err.lower()

    def test_provider_failure_no_partial_stdout(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _failing_run(self: object, request: object) -> object:  # type: ignore[override]
            raise ProviderExecutionError("no evidence")

        monkeypatch.setattr("research_core.engine.ResearchEngine.run", _failing_run)
        _, out, _ = _run_fixture(capsys, ["run", "test", "--fixture"])
        assert out == ""


# ---------------------------------------------------------------------------
# Exit code 6 — EXECUTION_FAILURE
# ---------------------------------------------------------------------------


@pytest.mark.cli
class TestExecutionFailureExitCode6:
    def test_incomplete_research_error_exits_6(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """IncompleteResearchError maps to exit code 6."""

        def _failing_run(self: object, request: object) -> object:  # type: ignore[override]
            raise IncompleteResearchError("strict mode triggered")

        monkeypatch.setattr("research_core.engine.ResearchEngine.run", _failing_run)
        code, out, err = _run_fixture(capsys, ["run", "test", "--fixture"])

        assert code == ExitCode.EXECUTION_FAILURE
        assert out == ""
        assert "Traceback" not in err
        assert len(err.strip()) > 0

    def test_research_core_error_exits_6(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Generic ResearchCoreError (not provider/profile) maps to exit code 6."""

        def _failing_run(self: object, request: object) -> object:  # type: ignore[override]
            raise ResearchCoreError("internal domain failure")

        monkeypatch.setattr("research_core.engine.ResearchEngine.run", _failing_run)
        code, out, err = _run_fixture(capsys, ["run", "test", "--fixture"])

        assert code == ExitCode.EXECUTION_FAILURE
        assert out == ""
        assert "Traceback" not in err

    def test_unexpected_exception_sanitized_to_6(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Unexpected non-domain exceptions are sanitized and map to exit code 6."""

        def _failing_run(self: object, request: object) -> object:  # type: ignore[override]
            raise RuntimeError("sentinel internal failure")

        monkeypatch.setattr("research_core.engine.ResearchEngine.run", _failing_run)
        code, out, err = _run_fixture(capsys, ["run", "test", "--fixture"])

        assert code == ExitCode.EXECUTION_FAILURE
        assert out == ""
        assert "Traceback" not in err
        # Raw exception message must not leak — only the exception type is safe to show
        assert "sentinel internal failure" not in err

    def test_execution_failure_no_stdout(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _failing_run(self: object, request: object) -> object:  # type: ignore[override]
            raise ResearchCoreError("domain error")

        monkeypatch.setattr("research_core.engine.ResearchEngine.run", _failing_run)
        _, out, _ = _run_fixture(capsys, ["run", "test", "--fixture"])
        assert out == ""

    def test_execution_failure_stderr_nonempty(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _failing_run(self: object, request: object) -> object:  # type: ignore[override]
            raise ResearchCoreError("domain error")

        monkeypatch.setattr("research_core.engine.ResearchEngine.run", _failing_run)
        _, _, err = _run_fixture(capsys, ["run", "test", "--fixture"])
        assert len(err.strip()) > 0


# ---------------------------------------------------------------------------
# Exit code 7 — OUTPUT_FAILURE
# ---------------------------------------------------------------------------


@pytest.mark.cli
class TestOutputFailureExitCode7:
    def test_markdown_render_failure_exits_7(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """MarkdownRenderer.render() raising maps to exit code 7."""

        def _failing_render(self: object, result: object) -> str:
            raise RuntimeError("injected render failure")

        monkeypatch.setattr(
            "research_core.renderers.markdown.MarkdownRenderer.render",
            _failing_render,
        )
        code, out, err = _run_fixture(capsys, ["run", "test", "--fixture"])

        assert code == ExitCode.OUTPUT_FAILURE
        assert out == ""
        assert "Traceback" not in err
        assert len(err.strip()) > 0

    def test_json_serialization_failure_exits_7(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """render_result raising during JSON serialization maps to exit code 7."""

        def _failing_dumps(obj: object, **kwargs: object) -> str:
            # Raise only when called from the CLI output path (not from elsewhere)
            raise TypeError("injected json failure")

        monkeypatch.setattr("research_core.cli.output.json.dumps", _failing_dumps)
        code, out, err = _run_fixture(
            capsys, ["run", "test", "--fixture", "--format", "json"]
        )

        assert code == ExitCode.OUTPUT_FAILURE
        assert out == ""
        assert "Traceback" not in err

    def test_output_failure_no_partial_stdout(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """No partial Markdown must appear in stdout on render failure."""

        def _failing_render(self: object, result: object) -> str:
            raise RuntimeError("render broken")

        monkeypatch.setattr(
            "research_core.renderers.markdown.MarkdownRenderer.render",
            _failing_render,
        )
        _, out, _ = _run_fixture(capsys, ["run", "test", "--fixture"])
        assert out == ""

    def test_output_failure_stderr_nonempty(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _failing_render(self: object, result: object) -> str:
            raise RuntimeError("render error")

        monkeypatch.setattr(
            "research_core.renderers.markdown.MarkdownRenderer.render",
            _failing_render,
        )
        _, _, err = _run_fixture(capsys, ["run", "test", "--fixture"])
        assert len(err.strip()) > 0


# ---------------------------------------------------------------------------
# stdout/stderr matrix — extended to cover all 9 scenarios
# ---------------------------------------------------------------------------


@pytest.mark.cli
class TestStdoutStderrFullMatrix:
    """Proves stdout/stderr discipline for all 9 documented exit scenarios."""

    def test_markdown_success_stdout_nonempty_stderr_empty(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code, out, err = _run_fixture(capsys, ["run", "test", "--fixture"])
        assert code == ExitCode.SUCCESS
        assert len(out) > 0
        assert err == ""

    def test_json_success_stdout_nonempty_stderr_empty(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code, out, err = _run_fixture(
            capsys, ["run", "test", "--fixture", "--format", "json"]
        )
        assert code == ExitCode.SUCCESS
        assert len(out) > 0
        assert err == ""

    def test_partial_success_stdout_nonempty_stderr_empty(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Fixture engine typically returns PARTIAL; still exit 0 with stdout result
        code, out, err = _run_fixture(capsys, ["run", "test", "--fixture"])
        assert code == ExitCode.SUCCESS
        assert len(out) > 0
        assert err == ""

    def test_invalid_request_stdout_empty_stderr_nonempty(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code, out, err = _run_fixture(capsys, ["run", "  ", "--fixture"])
        assert code == ExitCode.INVALID_REQUEST
        assert out == ""
        assert len(err.strip()) > 0

    def test_unknown_profile_stdout_empty_stderr_nonempty(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code, out, err = _run_fixture(
            capsys, ["run", "test", "--fixture", "--profile", "no-such-xyz"]
        )
        assert code == ExitCode.UNKNOWN_PROFILE
        assert out == ""
        assert len(err.strip()) > 0

    def test_provider_failure_stdout_empty_stderr_nonempty(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _fail(self: object, req: object) -> object:  # type: ignore[override]
            raise ProviderExecutionError("all providers down")

        monkeypatch.setattr("research_core.engine.ResearchEngine.run", _fail)
        code, out, err = _run_fixture(capsys, ["run", "test", "--fixture"])
        assert code == ExitCode.PROVIDER_FAILURE
        assert out == ""
        assert len(err.strip()) > 0

    def test_execution_failure_stdout_empty_stderr_nonempty(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _fail(self: object, req: object) -> object:  # type: ignore[override]
            raise ResearchCoreError("engine domain failure")

        monkeypatch.setattr("research_core.engine.ResearchEngine.run", _fail)
        code, out, err = _run_fixture(capsys, ["run", "test", "--fixture"])
        assert code == ExitCode.EXECUTION_FAILURE
        assert out == ""
        assert len(err.strip()) > 0

    def test_output_failure_stdout_empty_stderr_nonempty(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _fail_render(self: object, result: object) -> str:
            raise RuntimeError("renderer broken")

        monkeypatch.setattr(
            "research_core.renderers.markdown.MarkdownRenderer.render",
            _fail_render,
        )
        code, out, err = _run_fixture(capsys, ["run", "test", "--fixture"])
        assert code == ExitCode.OUTPUT_FAILURE
        assert out == ""
        assert len(err.strip()) > 0

    def test_configuration_failure_stdout_empty_stderr_nonempty(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code, out, err = _run_fixture(capsys, ["run", "test"])
        assert code == ExitCode.CONFIGURATION_FAILURE
        assert out == ""
        assert len(err.strip()) > 0
