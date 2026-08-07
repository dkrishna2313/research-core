"""Tests for profile handling in CLI."""

from __future__ import annotations

import pytest

from research_core.cli.app import main
from research_core.cli.exit_codes import ExitCode
from research_core.cli.providers import FIXTURE_PROFILE_IDS


@pytest.mark.cli
class TestFixtureProfileIds:
    def test_fixture_profile_recognized(self, capsys):
        code = main(["run", "test", "--fixture", "--profile", "fixture"])
        assert code == ExitCode.SUCCESS

    def test_default_profile_recognized(self, capsys):
        code = main(["run", "test", "--fixture", "--profile", "default"])
        assert code == ExitCode.SUCCESS

    def test_demo_profile_recognized(self, capsys):
        code = main(["run", "test", "--fixture", "--profile", "demo"])
        assert code == ExitCode.SUCCESS

    def test_fixture_profile_ids_set(self):
        assert "fixture" in FIXTURE_PROFILE_IDS
        assert "default" in FIXTURE_PROFILE_IDS
        assert "demo" in FIXTURE_PROFILE_IDS

    def test_fixture_profile_ids_is_frozenset(self):
        assert isinstance(FIXTURE_PROFILE_IDS, frozenset)


@pytest.mark.cli
class TestUnknownProfile:
    def test_unknown_profile_exits_4(self, capsys):
        code = main(["run", "test", "--fixture", "--profile", "nonexistent-xyz"])
        assert code == ExitCode.UNKNOWN_PROFILE

    def test_unknown_profile_stderr_contains_id(self, capsys):
        main(["run", "test", "--fixture", "--profile", "my-unknown-profile"])
        err = capsys.readouterr().err
        assert "my-unknown-profile" in err

    def test_unknown_profile_no_stdout(self, capsys):
        main(["run", "test", "--fixture", "--profile", "nonexistent-xyz"])
        assert capsys.readouterr().out == ""

    def test_unknown_profile_no_traceback(self, capsys):
        main(["run", "test", "--fixture", "--profile", "nonexistent-xyz"])
        err = capsys.readouterr().err
        assert "Traceback" not in err
        assert "traceback" not in err.lower()


@pytest.mark.cli
class TestDefaultProfile:
    def test_no_profile_flag_uses_default(self, capsys):
        code = main(["run", "test", "--fixture"])
        assert code == ExitCode.SUCCESS

    def test_no_profile_produces_valid_output(self, capsys):
        code = main(["run", "What is climate?", "--fixture"])
        out = capsys.readouterr().out
        assert code == 0
        assert out.startswith("#")

    def test_explicit_default_profile_produces_valid_output(self, capsys):
        code = main(["run", "What is climate?", "--fixture", "--profile", "default"])
        out = capsys.readouterr().out
        assert code == 0
        assert out.startswith("#")
