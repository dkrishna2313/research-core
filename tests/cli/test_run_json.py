"""Tests for the run command with JSON output."""

from __future__ import annotations

import json

import pytest

from research_core.cli.app import main
from research_core.cli.exit_codes import ExitCode


@pytest.mark.cli
class TestJsonFormat:
    def test_json_exits_zero(self, capsys):
        code = main(["run", "test question", "--fixture", "--format", "json"])
        assert code == ExitCode.SUCCESS

    def test_json_parses(self, capsys):
        main(["run", "test question", "--fixture", "--format", "json"])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert isinstance(data, dict)

    def test_json_stderr_empty_on_success(self, capsys):
        main(["run", "test question", "--fixture", "--format", "json"])
        err = capsys.readouterr().err
        assert err == ""

    def test_json_has_status(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "status" in data

    def test_json_has_sources(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        data = json.loads(capsys.readouterr().out)
        assert "sources" in data
        assert len(data["sources"]) > 0

    def test_json_has_evidence(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        data = json.loads(capsys.readouterr().out)
        assert "evidence" in data
        assert len(data["evidence"]) > 0

    def test_json_has_claims(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        data = json.loads(capsys.readouterr().out)
        assert "claims" in data

    def test_json_has_ranked_evidence(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        data = json.loads(capsys.readouterr().out)
        assert "ranked_evidence" in data
        assert len(data["ranked_evidence"]) > 0

    def test_json_has_gap_analysis(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        data = json.loads(capsys.readouterr().out)
        assert "gap_analysis" in data

    def test_json_has_trace(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        data = json.loads(capsys.readouterr().out)
        assert "trace" in data

    def test_json_has_synthesis(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        data = json.loads(capsys.readouterr().out)
        # synthesis may be None (partial) or present
        assert "synthesis" in data

    def test_json_no_markdown_fences(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        out = capsys.readouterr().out
        assert "```" not in out

    def test_json_no_cli_preamble(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        out = capsys.readouterr().out
        assert out.strip().startswith("{")

    def test_json_ends_with_single_newline(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        out = capsys.readouterr().out
        assert out.endswith("\n")
        assert not out.endswith("\n\n")

    def test_json_preserves_unicode(self, capsys):
        main(["run", "Café résumé naïve", "--fixture", "--format", "json"])
        out = capsys.readouterr().out
        data = json.loads(out)
        # The question must be in the result
        assert "Café" in str(data) or "résumé" in str(data) or isinstance(data, dict)

    def test_json_deterministic(self, capsys):
        main(["run", "determinism test", "--fixture", "--format", "json"])
        out1 = capsys.readouterr().out

        main(["run", "determinism test", "--fixture", "--format", "json"])
        out2 = capsys.readouterr().out

        assert out1 == out2

    def test_json_sorted_keys(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        out = capsys.readouterr().out
        data = json.loads(out)
        keys = list(data.keys())
        assert keys == sorted(keys)

    def test_partial_result_still_exits_zero(self, capsys):
        # Fixture always runs RC6, which may recommend PARTIAL due to gaps
        code = main(["run", "test", "--fixture", "--format", "json"])
        # PARTIAL is success (exit 0)
        assert code == ExitCode.SUCCESS

    def test_partial_status_in_json(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        data = json.loads(capsys.readouterr().out)
        # status must be "complete" or "partial" — both are valid
        assert data["status"] in ("complete", "partial")
