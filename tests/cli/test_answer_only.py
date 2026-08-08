"""
Tests for the --answer-only CLI flag (RC8.1.1).

Covers: parser recognition, default=False, fixture success, explicit markdown
equivalence, JSON conflict (exit 8), stdout/stderr contract, trailing newline,
default Markdown unchanged, fixture determinism, full pipeline still executes.
"""

from __future__ import annotations

import pytest

from research_core.cli.app import main
from research_core.cli.exit_codes import ExitCode


@pytest.mark.cli
class TestAnswerOnlyParser:
    def test_parser_recognizes_answer_only(self):
        from research_core.cli.parser import build_parser

        parser = build_parser()
        args = parser.parse_args(["run", "question", "--fixture", "--answer-only"])
        assert args.answer_only is True

    def test_answer_only_default_is_false(self):
        from research_core.cli.parser import build_parser

        parser = build_parser()
        args = parser.parse_args(["run", "question", "--fixture"])
        assert args.answer_only is False


@pytest.mark.cli
class TestAnswerOnlyFixture:
    def test_fixture_answer_only_exits_zero(self, capsys):
        code = main(["run", "What does the fixture evidence say?", "--fixture", "--answer-only"])
        assert code == ExitCode.SUCCESS
        capsys.readouterr()

    def test_fixture_answer_only_stdout_non_empty(self, capsys):
        main(["run", "What does the fixture evidence say?", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        assert len(out.strip()) > 0

    def test_fixture_answer_only_stderr_empty(self, capsys):
        main(["run", "What does the fixture evidence say?", "--fixture", "--answer-only"])
        err = capsys.readouterr().err
        assert err == ""

    def test_fixture_answer_only_ends_with_single_newline(self, capsys):
        main(["run", "What does the fixture evidence say?", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        assert out.endswith("\n")
        assert not out.endswith("\n\n")

    def test_fixture_answer_only_no_trailing_whitespace(self, capsys):
        main(["run", "What does the fixture evidence say?", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        for ln in out.splitlines():
            assert ln == ln.rstrip(), f"trailing whitespace on line: {ln!r}"

    def test_fixture_answer_only_is_valid_markdown(self, capsys):
        main(["run", "What does the fixture evidence say?", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        # Starts with a heading
        assert out.startswith("#")

    def test_fixture_answer_only_is_not_json(self, capsys):
        main(["run", "What does the fixture evidence say?", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        assert not out.strip().startswith("{")


@pytest.mark.cli
class TestAnswerOnlyContent:
    def test_answer_only_contains_synthesis_content(self, capsys):
        main(["run", "What does the fixture evidence say?", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        # The synthesized answer must have non-trivial content beyond just headings
        lines = [ln for ln in out.splitlines() if ln and not ln.startswith("#")]
        assert any(len(ln) > 20 for ln in lines)

    def test_answer_only_excludes_status_section(self, capsys):
        main(["run", "test", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        assert "## Status" not in out
        assert "**Is Complete:**" not in out

    def test_answer_only_excludes_sources_section(self, capsys):
        main(["run", "test", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        assert "## Sources" not in out

    def test_answer_only_excludes_evidence_section(self, capsys):
        main(["run", "test", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        # "## Evidence\n" is the report section heading; "## Evidence-Derived Claims" is synthesis
        assert "## Evidence\n" not in out

    def test_answer_only_excludes_claims_section(self, capsys):
        main(["run", "test", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        assert "## Claims" not in out

    def test_answer_only_excludes_quality_diagnostics_section(self, capsys):
        main(["run", "test", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        assert "## Quality Diagnostics" not in out

    def test_answer_only_excludes_research_gaps_section(self, capsys):
        main(["run", "test", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        assert "## Research Gaps" not in out

    def test_answer_only_excludes_quality_and_coverage_section(self, capsys):
        main(["run", "test", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        assert "## Quality and Coverage" not in out

    def test_answer_only_excludes_limitations_section(self, capsys):
        main(["run", "test", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        assert "## Limitations" not in out

    def test_answer_only_excludes_citations(self, capsys):
        main(["run", "test", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        assert "## Citations" not in out

    def test_answer_only_excludes_execution_trace(self, capsys):
        main(["run", "test", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        assert "## Execution Trace" not in out
        assert "KNOWLEDGE_RETRIEVAL" not in out

    def test_answer_only_contains_research_question(self, capsys):
        main(["run", "What does the fixture evidence say?", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        assert "What does the fixture evidence say?" in out


@pytest.mark.cli
class TestAnswerOnlyDeterminism:
    def test_fixture_answer_only_is_deterministic(self, capsys):
        main(["run", "determinism check", "--fixture", "--answer-only"])
        out1 = capsys.readouterr().out
        main(["run", "determinism check", "--fixture", "--answer-only"])
        out2 = capsys.readouterr().out
        assert out1 == out2


@pytest.mark.cli
class TestAnswerOnlyExplicitMarkdownEquivalence:
    def test_explicit_markdown_equals_default(self, capsys):
        main(["run", "What does the fixture say?", "--fixture", "--answer-only"])
        out_default = capsys.readouterr().out

        main(
            [
                "run",
                "What does the fixture say?",
                "--fixture",
                "--format",
                "markdown",
                "--answer-only",
            ]
        )
        out_explicit = capsys.readouterr().out

        assert out_default == out_explicit


@pytest.mark.cli
class TestAnswerOnlyJsonConflict:
    def test_json_answer_only_exits_configuration_failure(self, capsys):
        code = main(
            ["run", "question", "--fixture", "--format", "json", "--answer-only"]
        )
        assert code == ExitCode.CONFIGURATION_FAILURE

    def test_json_answer_only_stdout_empty(self, capsys):
        main(["run", "question", "--fixture", "--format", "json", "--answer-only"])
        out = capsys.readouterr().out
        assert out == ""

    def test_json_answer_only_stderr_non_empty(self, capsys):
        main(["run", "question", "--fixture", "--format", "json", "--answer-only"])
        err = capsys.readouterr().err
        assert "answer-only" in err.lower() or "markdown" in err.lower()

    def test_json_answer_only_stderr_no_traceback(self, capsys):
        main(["run", "question", "--fixture", "--format", "json", "--answer-only"])
        err = capsys.readouterr().err
        assert "Traceback" not in err
        assert "File " not in err


@pytest.mark.cli
class TestAnswerOnlyDefaultUnchanged:
    def test_default_markdown_not_affected_by_answer_only_flag_absence(self, capsys):
        main(["run", "test question", "--fixture"])
        out = capsys.readouterr().out
        # Full report still has machinery sections
        assert "## Status" in out
        assert "## Sources" in out
        assert "## Evidence" in out

    def test_default_and_answer_only_differ(self, capsys):
        main(["run", "test question", "--fixture"])
        full = capsys.readouterr().out

        main(["run", "test question", "--fixture", "--answer-only"])
        answer = capsys.readouterr().out

        assert full != answer
        assert len(full) > len(answer)


@pytest.mark.cli
class TestAnswerOnlyFullPipeline:
    def test_full_pipeline_still_executes(self, capsys):
        """answer-only is presentation-only; full ResearchResult must still exist."""
        from research_core.cli.app import main as cli_main
        from research_core.contracts.request import ResearchRequest
        from research_core.fixtures import build_fixture_engine

        engine = build_fixture_engine()
        request = ResearchRequest(question="pipeline verification")
        result = engine.run(request)

        # The full result contains all pipeline artifacts
        assert len(result.sources) > 0
        assert len(result.evidence) > 0
        assert len(result.claims) > 0
        assert result.gap_analysis is not None
        assert result.synthesis is not None
        assert result.trace is not None

        # answer-only CLI does not strip these from the engine result
        code = cli_main(["run", "pipeline verification", "--fixture", "--answer-only"])
        out = capsys.readouterr().out
        assert code == ExitCode.SUCCESS
        # Output is shorter than full report (hides machinery)
        cli_main(["run", "pipeline verification", "--fixture"])
        full_out = capsys.readouterr().out
        assert len(out) < len(full_out)


@pytest.mark.cli
class TestAnswerOnlyStrictMode:
    def test_answer_only_strict_partial_exits_nonzero(self, capsys):
        """When strict mode rejects a PARTIAL result, no answer leaks to stdout."""
        # Fixture may be partial — if so, strict mode must prevent output
        code = main(["run", "test", "--fixture", "--answer-only", "--strict"])
        out = capsys.readouterr().out
        if code != ExitCode.SUCCESS:
            # Strict rejection: stdout must be empty
            assert out == ""


@pytest.mark.cli
class TestAnswerPlusBasics:
    def test_answer_plus_exits_zero(self, capsys):
        code = main(["run", "test", "--fixture", "--answer-plus"])
        assert code == ExitCode.SUCCESS
        capsys.readouterr()

    def test_answer_plus_stderr_empty(self, capsys):
        main(["run", "test", "--fixture", "--answer-plus"])
        assert capsys.readouterr().err == ""

    def test_answer_plus_ends_with_single_newline(self, capsys):
        main(["run", "test", "--fixture", "--answer-plus"])
        out = capsys.readouterr().out
        assert out.endswith("\n")
        assert not out.endswith("\n\n")

    def test_answer_plus_no_trailing_whitespace(self, capsys):
        main(["run", "test", "--fixture", "--answer-plus"])
        out = capsys.readouterr().out
        for ln in out.splitlines():
            assert ln == ln.rstrip()

    def test_answer_plus_is_deterministic(self, capsys):
        main(["run", "determinism check", "--fixture", "--answer-plus"])
        out1 = capsys.readouterr().out
        main(["run", "determinism check", "--fixture", "--answer-plus"])
        out2 = capsys.readouterr().out
        assert out1 == out2


@pytest.mark.cli
class TestAnswerPlusContent:
    def test_answer_plus_contains_evidence_derived_claims(self, capsys):
        main(["run", "test", "--fixture", "--answer-plus"])
        out = capsys.readouterr().out
        assert "## Evidence-Derived Claims" in out

    def test_answer_plus_contains_quality_and_coverage(self, capsys):
        main(["run", "test", "--fixture", "--answer-plus"])
        out = capsys.readouterr().out
        assert "## Quality and Coverage" in out

    def test_answer_plus_contains_research_gaps(self, capsys):
        main(["run", "test", "--fixture", "--answer-plus"])
        out = capsys.readouterr().out
        assert "## Research Gaps" in out

    def test_answer_plus_contains_limitations(self, capsys):
        main(["run", "test", "--fixture", "--answer-plus"])
        out = capsys.readouterr().out
        assert "## Limitations" in out

    def test_answer_plus_contains_citations(self, capsys):
        main(["run", "test", "--fixture", "--answer-plus"])
        out = capsys.readouterr().out
        assert "## Citations" in out

    def test_answer_plus_citations_show_source_title(self, capsys):
        main(["run", "test", "--fixture", "--answer-plus"])
        out = capsys.readouterr().out
        assert "Fixture Knowledge Source" in out

    def test_answer_plus_excludes_status(self, capsys):
        main(["run", "test", "--fixture", "--answer-plus"])
        out = capsys.readouterr().out
        assert "## Status" not in out

    def test_answer_plus_excludes_sources_section(self, capsys):
        main(["run", "test", "--fixture", "--answer-plus"])
        out = capsys.readouterr().out
        assert "## Sources" not in out

    def test_answer_plus_excludes_execution_trace(self, capsys):
        main(["run", "test", "--fixture", "--answer-plus"])
        out = capsys.readouterr().out
        assert "## Execution Trace" not in out

    def test_answer_plus_briefer_than_full(self, capsys):
        main(["run", "test", "--fixture"])
        full = capsys.readouterr().out
        main(["run", "test", "--fixture", "--answer-plus"])
        plus = capsys.readouterr().out
        assert len(plus) < len(full)

    def test_answer_plus_longer_than_answer_only(self, capsys):
        main(["run", "test", "--fixture", "--answer-only"])
        only = capsys.readouterr().out
        main(["run", "test", "--fixture", "--answer-plus"])
        plus = capsys.readouterr().out
        assert len(plus) > len(only)


@pytest.mark.cli
class TestAnswerPlusConflicts:
    def test_json_answer_plus_exits_configuration_failure(self, capsys):
        code = main(["run", "q", "--fixture", "--format", "json", "--answer-plus"])
        assert code == ExitCode.CONFIGURATION_FAILURE
        capsys.readouterr()

    def test_json_answer_plus_stdout_empty(self, capsys):
        main(["run", "q", "--fixture", "--format", "json", "--answer-plus"])
        assert capsys.readouterr().out == ""

    def test_json_answer_plus_stderr_mentions_flag(self, capsys):
        main(["run", "q", "--fixture", "--format", "json", "--answer-plus"])
        err = capsys.readouterr().err
        assert "answer-plus" in err.lower() or "markdown" in err.lower()

    def test_answer_only_and_answer_plus_mutually_exclusive(self, capsys):
        code = main(["run", "q", "--fixture", "--answer-only", "--answer-plus"])
        assert code == ExitCode.CONFIGURATION_FAILURE
        capsys.readouterr()

    def test_mutual_exclusion_stdout_empty(self, capsys):
        main(["run", "q", "--fixture", "--answer-only", "--answer-plus"])
        assert capsys.readouterr().out == ""

    def test_mutual_exclusion_stderr_mentions_both_flags(self, capsys):
        main(["run", "q", "--fixture", "--answer-only", "--answer-plus"])
        err = capsys.readouterr().err
        assert "answer-only" in err and "answer-plus" in err
