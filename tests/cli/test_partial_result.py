"""Tests for PARTIAL result exit code behavior."""

from __future__ import annotations

import json

import pytest

from research_core.cli.app import main
from research_core.cli.exit_codes import ExitCode


@pytest.mark.cli
class TestPartialResultExitCode:
    def test_fixture_result_exits_zero(self, capsys):
        # Fixture may produce PARTIAL or COMPLETE — both should exit 0
        code = main(["run", "test", "--fixture"])
        assert code == ExitCode.SUCCESS

    def test_fixture_json_status_is_valid(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        data = json.loads(capsys.readouterr().out)
        assert data["status"] in ("complete", "partial")

    def test_fixture_partial_has_sources(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        data = json.loads(capsys.readouterr().out)
        # Even for partial results, sources should be present
        assert "sources" in data

    def test_fixture_partial_has_evidence(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        data = json.loads(capsys.readouterr().out)
        assert "evidence" in data

    def test_fixture_partial_has_trace(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        data = json.loads(capsys.readouterr().out)
        assert "trace" in data
        assert data["trace"] is not None

    def test_fixture_partial_markdown_renders(self, capsys):
        main(["run", "test", "--fixture"])
        out = capsys.readouterr().out
        # Partial result must still render a usable document
        assert len(out) > 0
        assert out.startswith("#")

    def test_fixture_partial_no_stderr(self, capsys):
        main(["run", "test", "--fixture"])
        err = capsys.readouterr().err
        # A PARTIAL result is valid — no error should be written to stderr
        assert err == ""
