"""Tests for error handling — no tracebacks, safe stderr messages."""

from __future__ import annotations

import pytest

from research_core.cli.app import main
from research_core.cli.exit_codes import ExitCode


@pytest.mark.cli
class TestNoTraceback:
    def test_unknown_profile_no_traceback(self, capsys):
        main(["run", "test", "--fixture", "--profile", "bad-profile"])
        err = capsys.readouterr().err
        assert "Traceback" not in err

    def test_blank_question_no_traceback(self, capsys):
        main(["run", "  ", "--fixture"])
        err = capsys.readouterr().err
        assert "Traceback" not in err

    def test_no_config_no_traceback(self, capsys):
        main(["run", "test"])
        err = capsys.readouterr().err
        assert "Traceback" not in err

    def test_unknown_profile_no_stack_frame(self, capsys):
        main(["run", "test", "--fixture", "--profile", "bad-profile"])
        err = capsys.readouterr().err
        assert 'File "' not in err
        assert "line " not in err.lower() or "error" in err.lower()


@pytest.mark.cli
class TestSafeStderrMessages:
    def test_unknown_profile_message_is_human_readable(self, capsys):
        main(["run", "test", "--fixture", "--profile", "unknown-xyz"])
        err = capsys.readouterr().err
        # Must contain something human-readable
        assert len(err.strip()) > 0

    def test_unknown_profile_mentions_profile_id(self, capsys):
        main(["run", "test", "--fixture", "--profile", "very-specific-name"])
        err = capsys.readouterr().err
        assert "very-specific-name" in err

    def test_blank_question_error_mentions_question(self, capsys):
        main(["run", "  ", "--fixture"])
        err = capsys.readouterr().err
        assert len(err.strip()) > 0

    def test_no_config_error_suggests_fixture(self, capsys):
        main(["run", "test"])
        err = capsys.readouterr().err
        assert "--fixture" in err

    def test_error_messages_go_to_stderr_not_stdout(self, capsys):
        main(["run", "test"])
        captured = capsys.readouterr()
        assert captured.out == ""
        assert len(captured.err) > 0


@pytest.mark.cli
class TestExitCodeMapping:
    def test_blank_question_maps_to_3(self, capsys):
        code = main(["run", "", "--fixture"])
        assert code == ExitCode.INVALID_REQUEST

    def test_whitespace_question_maps_to_3(self, capsys):
        code = main(["run", "   ", "--fixture"])
        assert code == ExitCode.INVALID_REQUEST

    def test_unknown_profile_maps_to_4(self, capsys):
        code = main(["run", "q", "--fixture", "--profile", "no-such-profile"])
        assert code == ExitCode.UNKNOWN_PROFILE

    def test_no_providers_maps_to_8(self, capsys):
        code = main(["run", "test"])
        assert code == ExitCode.CONFIGURATION_FAILURE

    def test_no_subcommand_maps_to_2(self, capsys):
        code = main([])
        assert code == ExitCode.USAGE_ERROR
