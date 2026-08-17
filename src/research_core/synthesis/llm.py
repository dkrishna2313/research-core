"""
LLMSynthesizer — Claude-backed synthesis that answers the research question directly.

Delegates structural assembly (gaps, quality, citations) to DeterministicSynthesizer,
then replaces two sections with LLM-generated content in a single API call:

  Summary — 2-5 sentence prose answer grounded in the evidence.
  Evidence-Derived Claims — rewritten as a coherent bullet list tied to the question
                            (raw verbatim extracts replaced with synthesized findings).

Requires the ``anthropic`` package and ``ANTHROPIC_API_KEY`` in the environment.
If either is absent, ProviderUnavailableError is raised before synthesis begins.
"""

from __future__ import annotations

import dataclasses
import re
from typing import TYPE_CHECKING

from research_core.exceptions import ProviderExecutionError, ProviderUnavailableError
from research_core.protocols.synthesis import SynthesisInput
from research_core.synthesis.contracts import SynthesisConfig
from research_core.synthesis.deterministic import DeterministicSynthesizer

if TYPE_CHECKING:
    import anthropic as _anthropic_t
    from research_core.contracts.result import SynthesisResult

_DEFAULT_MODEL = "claude-sonnet-5"
_MAX_EVIDENCE_ITEMS = 10
_MAX_EVIDENCE_CHARS = 500
_MAX_CLAIMS = 20
_MAX_TOKENS = 1024

_SYSTEM_PROMPT = (
    "You are a research synthesis assistant. "
    "Your sole task is to synthesize evidence into a direct answer to a research question. "
    "Stay strictly within what the evidence supports — do not speculate or add outside knowledge."
)

_USER_PROMPT_TEMPLATE = """\
Research Question: {question}

Evidence (ranked by relevance):
{evidence_block}

Raw claims extracted from the evidence:
{claims_block}

Produce exactly two XML sections and nothing else:

<summary>
Write 2–5 sentences directly answering the research question. Be specific: cite \
numbers, dates, or names where the evidence supports them. If the evidence is \
insufficient to fully answer the question, say so briefly.
</summary>

<findings>
Rewrite the raw claims above as a coherent bullet list tied to the research question. \
Each bullet should be a complete, standalone finding. Merge closely related claims. \
Preserve specific facts (numbers, dates, names). Keep each bullet concise (1–2 sentences). \
Use "- " to begin each bullet.
</findings>\
"""

# Matches content between <tag> ... </tag>, stripping surrounding whitespace.
_TAG_RE = re.compile(r"<(\w+)>\s*(.*?)\s*</\1>", re.DOTALL)


def _extract_tag(text: str, tag: str) -> str | None:
    """Return the content of the first <tag>…</tag> block, or None if absent."""
    for m in _TAG_RE.finditer(text):
        if m.group(1) == tag:
            return m.group(2).strip()
    return None


class LLMSynthesizer:
    """Synthesizer that rewrites Summary and Evidence-Derived Claims using Claude.

    A single Claude API call produces both sections. All other sections
    (Quality and Coverage, Research Gaps, Limitations, Citations) are
    produced deterministically and are unchanged.

    Parameters
    ----------
    client:
        Optional pre-constructed ``anthropic.Anthropic`` client. When omitted,
        one is constructed at synthesis time (reads ``ANTHROPIC_API_KEY`` from env).
    model:
        Claude model ID. Defaults to ``claude-sonnet-5``.
    """

    def __init__(
        self,
        client: _anthropic_t.Anthropic | None = None,
        *,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        self._client = client
        self._model = model
        self._det = DeterministicSynthesizer()

    def synthesize(
        self,
        inputs: SynthesisInput,
        *,
        config: SynthesisConfig | None = None,
    ) -> SynthesisResult:
        """Synthesize evidence and claims with LLM-generated summary and findings.

        Raises
        ------
        ProviderUnavailableError
            If the ``anthropic`` package is not installed, ``ANTHROPIC_API_KEY``
            is not set, or the Claude API is not reachable.
        ProviderExecutionError
            If the API call reaches Claude but returns unusable content.
        """
        # 1. Full deterministic result — all sections, citations, diagnostics
        det_result = self._det.synthesize(inputs, config=config)

        # 2. Nothing to synthesize — return deterministic result as-is
        if not inputs.sources and not inputs.claims:
            return det_result

        # 3. Single Claude call for both Summary and Evidence-Derived Claims
        llm_summary, llm_findings = self._generate_answer(inputs)

        # 4. Replace matched sections; leave all others untouched
        new_sections = tuple(
            dataclasses.replace(sec, body=llm_summary)
            if sec.title == "Summary"
            else dataclasses.replace(sec, body=llm_findings)
            if sec.title == "Evidence-Derived Claims"
            else sec
            for sec in det_result.sections
        )

        # 5. Return updated result (narrative is the backward-compat summary field)
        return dataclasses.replace(
            det_result,
            narrative=llm_summary,
            sections=new_sections,
            synthesis_model=f"LLMSynthesizer/{self._model}",
        )

    # ---------------------------------------------------------------------- #
    # Internal helpers
    # ---------------------------------------------------------------------- #

    def _get_client(self) -> _anthropic_t.Anthropic:
        if self._client is not None:
            return self._client
        try:
            import anthropic
        except ImportError as exc:
            raise ProviderUnavailableError(
                "LLMSynthesizer requires the 'anthropic' package. "
                "Install it with: pip install anthropic"
            ) from exc
        return anthropic.Anthropic()

    def _build_prompt_blocks(self, inputs: SynthesisInput) -> tuple[str, str]:
        """Return (evidence_block, claims_block) strings for the prompt."""
        ev_items = inputs.evidence[:_MAX_EVIDENCE_ITEMS]
        if ev_items:
            ev_lines = []
            for i, ranked in enumerate(ev_items, 1):
                content = ranked.normalized_evidence.evidence.content
                if len(content) > _MAX_EVIDENCE_CHARS:
                    content = content[:_MAX_EVIDENCE_CHARS] + "…"
                ev_lines.append(f"{i}. {content}")
            evidence_block = "\n".join(ev_lines)
        else:
            evidence_block = "(no ranked evidence available)"

        claims = inputs.claims[:_MAX_CLAIMS]
        if claims:
            claims_block = "\n".join(
                f"{i}. {c.claim_text}" for i, c in enumerate(claims, 1)
            )
        else:
            claims_block = "(no claims extracted)"

        return evidence_block, claims_block

    def _call_api(self, prompt: str) -> str:
        """Call the Claude API and return the raw response text."""
        client = self._get_client()
        try:
            message = client.messages.create(
                model=self._model,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            exc_type = type(exc).__name__
            if any(
                t in exc_type
                for t in ("AuthenticationError", "ConnectionError", "RateLimitError", "TimeoutError")
            ):
                raise ProviderUnavailableError(
                    f"Claude API not reachable during synthesis: {exc}"
                ) from exc
            raise ProviderExecutionError(
                f"Claude API call failed during synthesis: {exc}"
            ) from exc

        for block in message.content:
            if block.type == "text" and block.text.strip():
                return block.text.strip()

        raise ProviderExecutionError(
            "Claude API returned no text content in synthesis response."
        )

    def _generate_answer(self, inputs: SynthesisInput) -> tuple[str, str]:
        """Return (summary_prose, findings_body) from a single Claude call.

        Falls back gracefully if one tag is missing: the missing section
        gets the full response text (summary) or an empty string (findings).
        """
        evidence_block, claims_block = self._build_prompt_blocks(inputs)
        prompt = _USER_PROMPT_TEMPLATE.format(
            question=inputs.request_text,
            evidence_block=evidence_block,
            claims_block=claims_block,
        )
        raw = self._call_api(prompt)

        summary = _extract_tag(raw, "summary") or raw
        findings = _extract_tag(raw, "findings") or ""
        return summary, findings
