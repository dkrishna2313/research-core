"""
Tests for MarkdownRenderer.render_answer_only() (RC8.1.1).

Covers: synthesis content present, report sections absent, citations,
no-synthesis fallback, trailing newline, trailing whitespace, determinism,
full render unchanged.
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
    def test_citations_present_when_synthesis_has_them(self):
        result = _make_result()
        if result.synthesis and result.synthesis.citations:
            out = MarkdownRenderer().render_answer_only(result)
            assert "## Citations" in out
            first_cit = result.synthesis.citations[0]
            assert first_cit.claim_id in out


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
        # Call render_answer_only to ensure it has no side effects
        renderer.render_answer_only(result)
        out2 = renderer.render(result)
        assert out1 == out2
