"""Tests for the run command with Markdown output."""

from __future__ import annotations

import pytest

from research_core.cli.app import main
from research_core.cli.exit_codes import ExitCode


@pytest.mark.cli
class TestDefaultFormat:
    def test_default_format_is_markdown(self, capsys):
        code = main(["run", "What does the fixture evidence say?", "--fixture"])
        assert code == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert captured.out.startswith("#")
        assert captured.err == ""

    def test_default_equals_explicit_markdown(self, capsys):
        code1 = main(["run", "What does the fixture say?", "--fixture"])
        out1 = capsys.readouterr().out

        code2 = main(
            ["run", "What does the fixture say?", "--fixture", "--format", "markdown"]
        )
        out2 = capsys.readouterr().out

        assert code1 == code2 == ExitCode.SUCCESS
        assert out1 == out2

    def test_markdown_output_not_json(self, capsys):
        main(["run", "test question", "--fixture"])
        out = capsys.readouterr().out
        assert not out.strip().startswith("{")

    def test_markdown_ends_with_newline(self, capsys):
        main(["run", "test question", "--fixture"])
        out = capsys.readouterr().out
        assert out.endswith("\n")

    def test_markdown_no_trailing_whitespace_lines(self, capsys):
        main(["run", "test question", "--fixture"])
        out = capsys.readouterr().out
        for line in out.splitlines():
            assert line == line.rstrip(), f"trailing whitespace on line: {line!r}"


@pytest.mark.cli
class TestMarkdownContent:
    def test_markdown_contains_status(self, capsys):
        main(["run", "test", "--fixture"])
        out = capsys.readouterr().out
        assert "Status" in out or "status" in out

    def test_markdown_contains_sources_section(self, capsys):
        main(["run", "test", "--fixture"])
        out = capsys.readouterr().out
        assert "Sources" in out or "sources" in out

    def test_markdown_contains_evidence(self, capsys):
        main(["run", "test", "--fixture"])
        out = capsys.readouterr().out
        assert "Evidence" in out or "evidence" in out

    def test_unicode_question_renders(self, capsys):
        code = main(["run", "What is the résumé of climate science?", "--fixture"])
        assert code == ExitCode.SUCCESS
        out = capsys.readouterr().out
        assert "résumé" in out or out.startswith("#")


@pytest.mark.cli
class TestMarkdownDeterminism:
    def test_repeated_markdown_identical(self, capsys):
        main(["run", "determinism test question", "--fixture"])
        out1 = capsys.readouterr().out

        main(["run", "determinism test question", "--fixture"])
        out2 = capsys.readouterr().out

        assert out1 == out2
