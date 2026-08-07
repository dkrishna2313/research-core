"""Tests for stdout/stderr discipline."""

from __future__ import annotations

import json

import pytest

from research_core.cli.app import main
from research_core.cli.exit_codes import ExitCode


@pytest.mark.cli
class TestStdoutStderr:
    def test_success_stdout_nonempty(self, capsys):
        main(["run", "test", "--fixture"])
        assert capsys.readouterr().out != ""

    def test_success_stderr_empty(self, capsys):
        main(["run", "test", "--fixture"])
        assert capsys.readouterr().err == ""

    def test_success_json_stderr_empty(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        assert capsys.readouterr().err == ""

    def test_unknown_profile_stdout_empty(self, capsys):
        main(["run", "test", "--fixture", "--profile", "no-such-profile"])
        assert capsys.readouterr().out == ""

    def test_unknown_profile_stderr_nonempty(self, capsys):
        main(["run", "test", "--fixture", "--profile", "no-such-profile"])
        assert capsys.readouterr().err != ""

    def test_no_config_stdout_empty(self, capsys):
        main(["run", "test"])
        assert capsys.readouterr().out == ""

    def test_no_config_stderr_nonempty(self, capsys):
        main(["run", "test"])
        assert capsys.readouterr().err != ""

    def test_blank_question_stdout_empty(self, capsys):
        main(["run", "  ", "--fixture"])
        assert capsys.readouterr().out == ""

    def test_blank_question_stderr_nonempty(self, capsys):
        main(["run", "  ", "--fixture"])
        assert capsys.readouterr().err != ""

    def test_json_stdout_is_pure_json(self, capsys):
        code = main(["run", "test", "--fixture", "--format", "json"])
        out = capsys.readouterr().out
        assert code == ExitCode.SUCCESS
        # Must parse as JSON — no preamble, no commentary
        data = json.loads(out)
        assert isinstance(data, dict)

    def test_error_messages_not_in_json_stdout(self, capsys):
        # On success, no error text should appear in stdout at all
        main(["run", "test", "--fixture", "--format", "json"])
        out = capsys.readouterr().out
        assert "error:" not in out.lower()
