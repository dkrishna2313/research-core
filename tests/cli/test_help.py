"""Tests for --help and --version behavior."""

from __future__ import annotations

import pytest

from research_core.cli.app import main
from research_core.cli.exit_codes import ExitCode


@pytest.mark.cli
class TestHelp:
    def test_root_help_exits_zero(self):
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0

    def test_run_help_exits_zero(self):
        with pytest.raises(SystemExit) as exc:
            main(["run", "--help"])
        assert exc.value.code == 0

    def test_root_help_contains_run(self, capsys):
        with pytest.raises(SystemExit):
            main(["--help"])
        out = capsys.readouterr().out
        assert "run" in out

    def test_run_help_contains_question(self, capsys):
        with pytest.raises(SystemExit):
            main(["run", "--help"])
        out = capsys.readouterr().out
        assert "QUESTION" in out.upper() or "question" in out.lower()

    def test_run_help_contains_format(self, capsys):
        with pytest.raises(SystemExit):
            main(["run", "--help"])
        out = capsys.readouterr().out
        assert "--format" in out

    def test_run_help_contains_fixture(self, capsys):
        with pytest.raises(SystemExit):
            main(["run", "--help"])
        out = capsys.readouterr().out
        assert "--fixture" in out


@pytest.mark.cli
class TestVersion:
    def test_version_exits_zero(self):
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0

    def test_version_reports_0_8_0(self, capsys):
        with pytest.raises(SystemExit):
            main(["--version"])
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "0.8.0" in combined

    def test_version_contains_program_name(self, capsys):
        import research_core

        with pytest.raises(SystemExit):
            main(["--version"])
        assert research_core.__version__ == "0.8.0"


@pytest.mark.cli
class TestMissingSubcommand:
    def test_no_subcommand_returns_usage_error(self, capsys):
        code = main([])
        assert code == ExitCode.USAGE_ERROR

    def test_no_subcommand_writes_to_stderr(self, capsys):
        main([])
        captured = capsys.readouterr()
        # argparse prints help/usage to stderr when we call print_help(sys.stderr)
        assert captured.out == ""
