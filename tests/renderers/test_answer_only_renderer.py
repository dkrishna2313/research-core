"""
Tests for MarkdownRenderer.render_answer_only() and render_answer_plus() (RC8.1.1).

render_answer_only: pure answer — no diagnostics, no citations.
render_answer_plus: answer + brief diagnostics (2 lines each) + source-titled citations.
"""

from __future__ import annotations

import pytest

from research_core.renderers.markdown import MarkdownRenderer


def _make_result():
    """Return a fixture ResearchResult via the fixture engine."""
    from research_core.contracts.request import ResearchRequest
    from research_core.fixtures import build_fixture_engine

    engine = build_fixture_engine()
    return engine.run(ResearchRequest(question="What does the fixture evidence say?"))


@pytest.mark.renderers
class TestRenderAnswerOnlyFormat:
    def test_ends_with_single_newline(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_only(result)
        assert out.endswith("\n")
        assert not out.endswith("\n\n")

    def test_no_trailing_whitespace_on_any_line(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_only(result)
        for ln in out.splitlines():
            assert ln == ln.rstrip(), f"trailing whitespace: {ln!r}"

    def test_starts_with_heading(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_only(result)
        assert out.startswith("#")

    def test_is_deterministic(self):
        result = _make_result()
        renderer = MarkdownRenderer()
        assert renderer.render_answer_only(result) == renderer.render_answer_only(result)


@pytest.mark.renderers
class TestRenderAnswerOnlyContent:
    def test_contains_synthesis_body_text(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_only(result)
        assert result.synthesis is not None
        assert result.synthesis.sections
        first_section = min(result.synthesis.sections, key=lambda s: s.order)
        assert first_section.body in out

    def test_contains_research_question(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_only(result)
        assert result.request.question in out

    def test_excludes_status(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_only(result)
        assert "## Status" not in out
        assert "**Is Complete:**" not in out

    def test_excludes_sources_section(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_only(result)
        assert "## Sources" not in out

    def test_excludes_evidence_section(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_only(result)
        # "## Evidence\n" is the report section heading; "## Evidence-Derived Claims" is synthesis
        assert "## Evidence\n" not in out

    def test_excludes_claims_section(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_only(result)
        assert "## Claims" not in out

    def test_excludes_quality_diagnostics_section(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_only(result)
        assert "## Quality Diagnostics" not in out

    def test_excludes_execution_trace(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_only(result)
        assert "## Execution Trace" not in out
        assert "KNOWLEDGE_RETRIEVAL" not in out

    def test_excludes_limitations_boilerplate_section(self):
        """The renderer's own Limitations section must not appear; synthesis may have one."""
        result = _make_result()
        out = MarkdownRenderer().render_answer_only(result)
        # The renderer boilerplate references pipeline signals and quality scores
        assert "Evidence-derived claims are not automatically verified" not in out


@pytest.mark.renderers
class TestRenderAnswerOnlyCitations:
    def test_answer_only_has_no_citations_section(self):
        """answer-only hides citations entirely."""
        result = _make_result()
        out = MarkdownRenderer().render_answer_only(result)
        assert "## Citations" not in out

    def test_answer_only_has_no_diagnostic_sections(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_only(result)
        assert "## Quality and Coverage" not in out
        assert "## Research Gaps" not in out
        assert "## Limitations" not in out


@pytest.mark.renderers
class TestRenderAnswerOnlyNoSynthesis:
    def test_no_synthesis_renders_fallback_message(self):
        """When synthesis is None, render a clear fallback rather than empty output."""
        import dataclasses

        result = _make_result()
        result_no_synth = dataclasses.replace(result, synthesis=None)

        out = MarkdownRenderer().render_answer_only(result_no_synth)
        assert out.endswith("\n")
        assert len(out.strip()) > 0
        assert "not available" in out.lower() or "synthesis" in out.lower()


@pytest.mark.renderers
class TestRenderAnswerOnlyVsFullRender:
    def test_answer_only_shorter_than_full(self):
        result = _make_result()
        renderer = MarkdownRenderer()
        assert len(renderer.render_answer_only(result)) < len(renderer.render(result))

    def test_full_render_unchanged(self):
        """render() must be byte-for-byte identical regardless of render_answer_only existing."""
        result = _make_result()
        renderer = MarkdownRenderer()
        out1 = renderer.render(result)
        renderer.render_answer_only(result)
        out2 = renderer.render(result)
        assert out1 == out2


@pytest.mark.renderers
class TestRenderAnswerPlusFormat:
    def test_ends_with_single_newline(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_plus(result)
        assert out.endswith("\n")
        assert not out.endswith("\n\n")

    def test_no_trailing_whitespace_on_any_line(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_plus(result)
        for ln in out.splitlines():
            assert ln == ln.rstrip(), f"trailing whitespace: {ln!r}"

    def test_is_deterministic(self):
        result = _make_result()
        renderer = MarkdownRenderer()
        assert renderer.render_answer_plus(result) == renderer.render_answer_plus(result)


@pytest.mark.renderers
class TestRenderAnswerPlusContent:
    def test_contains_evidence_derived_claims(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_plus(result)
        assert "## Evidence-Derived Claims" in out

    def test_contains_quality_and_coverage(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_plus(result)
        assert "## Quality and Coverage" in out

    def test_contains_research_gaps(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_plus(result)
        assert "## Research Gaps" in out

    def test_contains_limitations(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_plus(result)
        assert "## Limitations" in out

    def test_contains_citations_with_source_title(self):
        result = _make_result()
        if result.synthesis and result.synthesis.citations and result.sources:
            out = MarkdownRenderer().render_answer_plus(result)
            assert "## Citations" in out
            src = result.sources[0]
            if src.title:
                assert src.title in out
            assert f"source:`{src.source_id}`" not in out

    def test_excludes_report_machinery(self):
        result = _make_result()
        out = MarkdownRenderer().render_answer_plus(result)
        assert "## Status" not in out
        assert "## Sources" not in out
        assert "## Execution Trace" not in out

    def test_research_gaps_condensed_to_two_lines(self):
        """Research Gaps body is truncated to at most 2 non-empty lines."""
        result = _make_result()
        out = MarkdownRenderer().render_answer_plus(result)
        # Extract lines between ## Research Gaps and the next ## heading
        in_gaps = False
        gap_body_lines = []
        for ln in out.splitlines():
            if ln == "## Research Gaps":
                in_gaps = True
                continue
            if in_gaps:
                if ln.startswith("## "):
                    break
                if ln.strip():
                    gap_body_lines.append(ln)
        assert len(gap_body_lines) <= 2


@pytest.mark.renderers
class TestRenderAnswerSizing:
    def test_answer_only_shorter_than_answer_plus(self):
        result = _make_result()
        renderer = MarkdownRenderer()
        assert len(renderer.render_answer_only(result)) < len(renderer.render_answer_plus(result))

    def test_answer_plus_shorter_than_full(self):
        result = _make_result()
        renderer = MarkdownRenderer()
        assert len(renderer.render_answer_plus(result)) < len(renderer.render(result))
