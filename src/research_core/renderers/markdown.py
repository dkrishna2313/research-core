"""
MarkdownRenderer — pure Markdown presentation of a ResearchResult.

Escaping policy:
- IDs are rendered in backtick code spans to prevent Markdown interpretation.
- User-supplied text (claim statements, evidence content, narrative, source titles)
  is rendered as-is; escaping would alter meaning.
- Structural headings use only hardcoded strings; no user content appears in headings.

Missing-vs-zero policy:
- None → "Unavailable" (dimension was not measured)
- 0.0 → "0.000" (dimension was measured and scored at minimum)

Output format:
- Ends with exactly one newline.
- No trailing whitespace on any line.
- Repeated calls on the same result produce identical output.
- The renderer never mutates the result.
"""

from __future__ import annotations

from research_core.contracts.result import ResearchResult, ResearchStatus


def _score_str(value: float | None) -> str:
    """Format a quality score. None → 'Unavailable'; 0.0 → '0.000'."""
    if value is None:
        return "Unavailable"
    return f"{value:.3f}"


def _status_label(status: ResearchStatus) -> str:
    return status.value.upper()


class MarkdownRenderer:
    """Converts a ResearchResult to a Markdown string.

    This renderer is pure — it does not mutate the input, run providers,
    make network calls, or write any files. Output is deterministic for
    identical input.

    Usage::

        renderer = MarkdownRenderer()
        md = renderer.render(result)
        md_answer = renderer.render_answer_only(result)
        md_plus   = renderer.render_answer_plus(result)
    """

    # Diagnostic synthesis sections condensed to 2 lines in answer-plus mode.
    _BRIEF_SECTIONS = frozenset({"Quality and Coverage", "Research Gaps", "Limitations"})

    @staticmethod
    def _brief_body(body: str, max_lines: int = 2) -> str:
        """Return at most max_lines non-empty lines from body."""
        non_empty = [ln for ln in body.splitlines() if ln.strip()]
        return "\n".join(non_empty[:max_lines])

    @staticmethod
    def _source_labels(result: ResearchResult) -> dict[str, str]:
        """Build source_id → "Title [Publisher]" lookup for citations."""
        labels: dict[str, str] = {}
        for src in result.sources:
            if src.title:
                lbl = f"{src.title} [{src.publisher}]" if src.publisher else src.title
            else:
                lbl = src.source_id
            labels[src.source_id] = lbl
        return labels

    def render_answer_only(self, result: ResearchResult) -> str:
        """Render only the pure synthesized answer sections.

        Shows Summary and Evidence-Derived Claims. Hides all report machinery
        and all diagnostic synthesis sections (Quality and Coverage, Research
        Gaps, Limitations, Citations). The full ResearchResult is unchanged.

        Returns a non-empty string ending with exactly one newline.
        No trailing whitespace on any line.
        """
        return self._render_answer_view(
            result,
            include_brief_sections=False,
            include_citations=False,
        )

    def render_answer_plus(self, result: ResearchResult) -> str:
        """Render the synthesized answer with brief diagnostic context.

        Shows Summary and Evidence-Derived Claims at full length, followed by
        Quality and Coverage, Research Gaps, and Limitations condensed to 2
        lines each, and a Citations block with source titles. Hides all other
        report machinery. The full ResearchResult is unchanged.

        Returns a non-empty string ending with exactly one newline.
        No trailing whitespace on any line.
        """
        return self._render_answer_view(
            result,
            include_brief_sections=True,
            include_citations=True,
        )

    def _render_answer_view(
        self,
        result: ResearchResult,
        *,
        include_brief_sections: bool,
        include_citations: bool,
    ) -> str:
        lines: list[str] = []

        def blank() -> None:
            lines.append("")

        def line(text: str) -> None:
            lines.append(text)

        source_label = self._source_labels(result) if include_citations else {}

        lines.append(f"# {result.request.question}")
        blank()

        syn = result.synthesis
        if syn is None:
            line("*Synthesis not available — the research pipeline did not produce a result.*")
            blank()
        elif syn.sections:
            for sec in sorted(syn.sections, key=lambda s: s.order):
                is_brief = sec.title in self._BRIEF_SECTIONS
                if is_brief and not include_brief_sections:
                    continue
                lines.append(f"## {sec.title}")
                blank()
                if sec.body:
                    line(self._brief_body(sec.body) if is_brief else sec.body)
                blank()
            if include_citations and syn.citations:
                lines.append("## Citations")
                blank()
                for cit in syn.citations:
                    label = cit.label or cit.citation_id
                    src_name = source_label.get(cit.source_id, cit.source_id)
                    line(f"{label} {src_name}")
                blank()
        else:
            # Legacy synthesis without structured sections
            if syn.narrative:
                line(syn.narrative)
                blank()
            if syn.key_findings:
                lines.append("## Key Findings")
                blank()
                for finding in syn.key_findings:
                    line(f"- {finding}")
                blank()
            if not syn.narrative and not syn.key_findings:
                line("*No synthesized content available.*")
                blank()

        cleaned = [ln.rstrip() for ln in lines]
        while cleaned and cleaned[-1] == "":
            cleaned.pop()
        return "\n".join(cleaned) + "\n"

    def render(self, result: ResearchResult) -> str:
        """Render *result* to a Markdown string.

        Returns a non-empty string ending with exactly one newline.
        No trailing whitespace on any line.
        """
        lines: list[str] = []

        def section(heading: str, level: int = 2) -> None:
            prefix = "#" * level
            lines.append(f"{prefix} {heading}")
            lines.append("")

        def blank() -> None:
            lines.append("")

        def line(text: str) -> None:
            lines.append(text)

        # ------------------------------------------------------------------ #
        # Title
        # ------------------------------------------------------------------ #
        lines.append("# Research Result")
        blank()

        # ------------------------------------------------------------------ #
        # Status
        # ------------------------------------------------------------------ #
        section("Status")
        line(f"**Status:** {result.status.value}")
        line(f"**Is Complete:** {result.is_complete}")
        if result.completed_at is not None:
            line(f"**Completed At:** {result.completed_at.isoformat()}")
        if result.status == ResearchStatus.PARTIAL:
            line("")
            line("> **Notice:** This result is partial. Some pipeline stages did not complete.")
        blank()

        # ------------------------------------------------------------------ #
        # Research Question
        # ------------------------------------------------------------------ #
        section("Research Question")
        line(result.request.question)
        blank()

        # ------------------------------------------------------------------ #
        # Executive Summary
        # ------------------------------------------------------------------ #
        section("Executive Summary")
        if result.synthesis is not None:
            syn = result.synthesis
            if syn.sections:
                # Structured synthesis: render summary section body
                summary_secs = [s for s in syn.sections if s.title == "Summary"]
                if summary_secs:
                    line(summary_secs[0].body)
                else:
                    line(syn.narrative)
            else:
                line(syn.narrative)
        else:
            line("*Not available — synthesis was not performed or did not complete.*")
        blank()

        # ------------------------------------------------------------------ #
        # Sources
        # ------------------------------------------------------------------ #
        section("Sources")
        if result.sources:
            for src in result.sources:
                title_part = f" — {src.title}" if src.title else ""
                url_part = f" ({src.url})" if src.url else ""
                publisher_part = f" [{src.publisher}]" if src.publisher else ""
                line(
                    f"- `{src.source_id}`{title_part}"
                    f" ({src.source_type.value}){url_part}{publisher_part}"
                )
        else:
            line("*No sources.*")
        blank()

        # ------------------------------------------------------------------ #
        # Evidence
        # ------------------------------------------------------------------ #
        section("Evidence")
        if result.evidence:
            for i, ev in enumerate(result.evidence, 1):
                q = ev.quality
                rel = _score_str(q.relevance)
                auth = _score_str(q.authority)
                line(f"{i}. `{ev.evidence_id}` (source: `{ev.source_id}`)")
                line(f"   relevance={rel}, authority={auth}")
                line(f"   > {ev.content}")
                blank()
        else:
            line("*No evidence.*")
            blank()

        # ------------------------------------------------------------------ #
        # Claims
        # ------------------------------------------------------------------ #
        section("Claims")
        if result.claims:
            for i, cl in enumerate(result.claims, 1):
                ev_refs = (
                    ", ".join(f"`{eid}`" for eid in cl.supporting_evidence_ids)
                    if cl.supporting_evidence_ids
                    else "none"
                )
                line(f"{i}. `{cl.claim_id}` ({cl.claim_type.value})")
                line(f"   {cl.statement}")
                line(f"   Supporting evidence: {ev_refs}")
                blank()
        else:
            line("*No claims.*")
            blank()

        # ------------------------------------------------------------------ #
        # Quality Diagnostics
        # ------------------------------------------------------------------ #
        section("Quality Diagnostics")
        if result.gap_analysis is not None:
            # RC6 rich quality diagnostics
            qd = result.gap_analysis.quality_diagnostics
            line(f"**Overall Status:** {qd.overall_status.value}")
            if qd.overall_score is not None:
                line(f"**Overall Score:** {_score_str(qd.overall_score)}")
            blank()
            cov = qd.coverage
            line(f"**Coverage:** {cov.source_count} source(s), "
                 f"{cov.evidence_count} evidence item(s), "
                 f"{cov.claim_count} claim(s).")
            if cov.evidence_utilization_ratio is not None:
                line(f"**Evidence Utilization:** {cov.evidence_utilization_ratio:.1%}")
            blank()
            if qd.dimensions:
                line("| Dimension | Status | Score |")
                line("|-----------|--------|-------|")
                for dim in qd.dimensions:
                    score_s = _score_str(dim.mean)
                    line(f"| {dim.dimension} | {dim.status.value} | {score_s} |")
                blank()
        elif result.quality is not None:
            qual = result.quality
            if qual.composite is not None:
                line(f"**Composite Score:** {_score_str(qual.composite)}")
                blank()

            line("| Dimension | Score |")
            line("|-----------|-------|")
            for dim_name, leg_dim in qual.dimensions().items():
                line(f"| {dim_name} | {_score_str(leg_dim.score)} |")
            blank()
        else:
            line("*Quality diagnostics unavailable.*")
            blank()

        # ------------------------------------------------------------------ #
        # Research Gaps
        # ------------------------------------------------------------------ #
        section("Research Gaps")
        if result.gaps:
            for i, gap in enumerate(result.gaps, 1):
                related_claims = (
                    ", ".join(f"`{cid}`" for cid in gap.related_claim_ids)
                    if gap.related_claim_ids
                    else "none"
                )
                related_ev = (
                    ", ".join(f"`{eid}`" for eid in gap.related_evidence_ids)
                    if gap.related_evidence_ids
                    else "none"
                )
                cond = f" (condition: `{gap.condition}`)" if gap.condition else ""
                line(
                    f"{i}. [{gap.severity.upper()}] `{gap.gap_id}`{cond}"
                )
                line(f"   Type: {gap.gap_type.value} | Status: {gap.status.value}")
                line(f"   {gap.description}")
                if gap.recommended_action:
                    line(f"   Recommended action: {gap.recommended_action}")
                line(f"   Related claims: {related_claims}")
                line(f"   Related evidence: {related_ev}")
                blank()
        else:
            line("*No research gaps identified.*")
            blank()

        # ------------------------------------------------------------------ #
        # Synthesis
        # ------------------------------------------------------------------ #
        section("Synthesis")
        if result.synthesis is not None:
            syn = result.synthesis
            if syn.synthesis_model:
                line(f"**Model:** {syn.synthesis_model}")
                blank()
            if syn.synthesized_at is not None:
                line(f"**Synthesized At:** {syn.synthesized_at.isoformat()}")
                blank()
            if syn.confidence is not None:
                line(f"**Confidence:** {syn.confidence:.3f}")
                blank()
            if syn.sections:
                # Structured synthesis: render non-Summary sections
                non_summary = [s for s in syn.sections if s.title != "Summary"]
                for sec in sorted(non_summary, key=lambda s: s.order):
                    section(sec.title, level=3)
                    if sec.body:
                        line(sec.body)
                    blank()
                if syn.citations:
                    section("Citations", level=3)
                    for cit in syn.citations:
                        label = cit.label or cit.citation_id
                        line(
                            f"{label} claim:`{cit.claim_id}` "
                            f"evidence:`{cit.evidence_id}` "
                            f"source:`{cit.source_id}`"
                        )
                    blank()
            else:
                # Legacy synthesis: render narrative + key_findings
                line(syn.narrative)
                blank()
                if syn.key_findings:
                    line("**Key Findings:**")
                    blank()
                    for finding in syn.key_findings:
                        line(f"- {finding}")
                    blank()
        else:
            line("*Synthesis not available.*")
            blank()

        # ------------------------------------------------------------------ #
        # Contradictions
        # ------------------------------------------------------------------ #
        if result.contradictions:
            section("Contradictions")
            for i, con in enumerate(result.contradictions, 1):
                claim_refs = (
                    ", ".join(f"`{cid}`" for cid in con.claim_ids)
                    if con.claim_ids
                    else "none"
                )
                ev_refs = (
                    ", ".join(f"`{eid}`" for eid in con.evidence_ids)
                    if con.evidence_ids
                    else "none"
                )
                line(f"{i}. `{con.contradiction_id}` [{con.severity.upper()}]")
                line(f"   Type: {con.contradiction_type.value}")
                line(f"   {con.description}")
                line(f"   Claims: {claim_refs} | Evidence: {ev_refs}")
                blank()

        # ------------------------------------------------------------------ #
        # Open Questions
        # ------------------------------------------------------------------ #
        if result.open_questions:
            section("Open Questions")
            for i, oq in enumerate(result.open_questions, 1):
                line(f"{i}. [{oq.priority.value.upper()}] {oq.question}")
                if oq.reason:
                    line(f"   Reason: {oq.reason}")
                blank()

        # ------------------------------------------------------------------ #
        # Execution Trace
        # ------------------------------------------------------------------ #
        section("Execution Trace")
        if result.trace is not None and result.trace.events:
            for i, evt in enumerate(result.trace.events, 1):
                line(
                    f"{i}. [{evt.stage.value}] {evt.status.value.upper()}"
                    f" — {evt.message}"
                )
            blank()
        else:
            line("*No trace events.*")
            blank()

        # ------------------------------------------------------------------ #
        # Limitations
        # ------------------------------------------------------------------ #
        section("Limitations")
        line(
            "This result was produced by a deterministic research pipeline. "
            "Evidence-derived claims are not automatically verified, corroborated, "
            "or assigned authority. Quality scores reflect pipeline signals, not "
            "factual reliability. Research gaps indicate incomplete coverage; "
            "they do not indicate that the research question has no answer."
        )
        blank()

        # ------------------------------------------------------------------ #
        # Assemble and normalise
        # ------------------------------------------------------------------ #
        # Strip trailing whitespace from each line, then join.
        cleaned = [ln.rstrip() for ln in lines]
        # Remove any trailing blank lines, then add exactly one newline.
        while cleaned and cleaned[-1] == "":
            cleaned.pop()
        return "\n".join(cleaned) + "\n"
