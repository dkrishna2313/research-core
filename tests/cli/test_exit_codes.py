"""Tests for exit codes covering all documented values."""

from __future__ import annotations

import pytest

from research_core.cli.app import main
from research_core.cli.exit_codes import ExitCode


@pytest.mark.cli
class TestExitCodeValues:
    def test_success_is_zero(self):
        assert ExitCode.SUCCESS == 0

    def test_usage_error_is_2(self):
        assert ExitCode.USAGE_ERROR == 2

    def test_invalid_request_is_3(self):
        assert ExitCode.INVALID_REQUEST == 3

    def test_unknown_profile_is_4(self):
        assert ExitCode.UNKNOWN_PROFILE == 4

    def test_provider_failure_is_5(self):
        assert ExitCode.PROVIDER_FAILURE == 5

    def test_execution_failure_is_6(self):
        assert ExitCode.EXECUTION_FAILURE == 6

    def test_output_failure_is_7(self):
        assert ExitCode.OUTPUT_FAILURE == 7

    def test_configuration_failure_is_8(self):
        assert ExitCode.CONFIGURATION_FAILURE == 8


@pytest.mark.cli
class TestExitCodeBehavior:
    def test_fixture_run_exits_zero(self, capsys):
        code = main(["run", "test question", "--fixture"])
        assert code == ExitCode.SUCCESS

    def test_missing_subcommand_exits_2(self, capsys):
        code = main([])
        assert code == ExitCode.USAGE_ERROR

    def test_blank_question_exits_3(self, capsys):
        code = main(["run", "   ", "--fixture"])
        assert code == ExitCode.INVALID_REQUEST
        err = capsys.readouterr().err
        assert "blank" in err.lower() or "empty" in err.lower() or "error" in err.lower()

    def test_empty_question_exits_3(self, capsys):
        code = main(["run", "", "--fixture"])
        assert code == ExitCode.INVALID_REQUEST

    def test_unknown_profile_exits_4(self, capsys):
        code = main(["run", "test", "--fixture", "--profile", "nonexistent-profile-xyz"])
        assert code == ExitCode.UNKNOWN_PROFILE
        err = capsys.readouterr().err
        assert "nonexistent-profile-xyz" in err

    def test_no_providers_exits_8(self, capsys):
        # Without --fixture, no providers are configured
        code = main(["run", "test question"])
        assert code == ExitCode.CONFIGURATION_FAILURE
        err = capsys.readouterr().err
        assert "--fixture" in err

    def test_configuration_failure_no_stdout(self, capsys):
        main(["run", "test question"])
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_unknown_profile_no_stdout(self, capsys):
        main(["run", "test", "--fixture", "--profile", "xyz-unknown"])
        assert capsys.readouterr().out == ""

    def test_partial_result_is_success(self, capsys):
        # Fixture with RC6 typically produces PARTIAL; still exit 0
        code = main(["run", "test", "--fixture"])
        assert code == ExitCode.SUCCESS

    def test_invalid_format_exits_2(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["run", "test", "--fixture", "--format", "yaml"])
        assert exc.value.code == 2
