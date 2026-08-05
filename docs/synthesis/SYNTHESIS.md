# Synthesis — RC7

Synthesis is the final analytic stage of the research pipeline. It converts
structured evidence, claims, gaps, and open questions into a narrative summary
and an ordered list of key findings.

## Design constraints

- **No LLM.** `DeterministicSynthesizer` does not call any language model. It
  assembles its output from the pipeline's own structured outputs.
- **No truth inference.** The synthesizer never decides whether a claim is true.
  Claims appear in key findings verbatim.
- **No contradiction resolution.** Both sides of a detected contradiction
  appear in key findings unchanged.
- **Deterministic.** Identical inputs produce identical outputs regardless of
  call count or instance.

## Output contract

`SynthesisResult` (from `research_core.contracts.result`):

| Field | Type | Notes |
|---|---|---|
| `narrative` | `str` | Non-empty. Count-based summary plus limitations text. |
| `key_findings` | `tuple[str, ...]` | Claim statements, ordered by evidence position then claim_id. |
| `synthesis_model` | `str \| None` | Identifies the synthesizer variant. |
| `synthesized_at` | `datetime \| None` | `None` — deterministic synthesizer sets no timestamp. |
| `confidence` | `float \| None` | `None` — no confidence is computed. |

## Narrative structure

The narrative is:

1. A count sentence: _"The research retrieved N evidence item(s) from M source(s), yielding P claim(s)."_
2. If gaps exist: _"Q research gap(s) were identified."_
3. A limitations disclaimer: _"This synthesis does not imply verification, corroboration, or truth inference."_

## Claim ordering

Key findings follow evidence order then claim_id lexicographic order for stability:

1. Claims supported by evidence item at index 0 appear first.
2. Among claims with the same lowest evidence index, sort by `claim_id`.
3. Claims with no supporting evidence appear at the end, sorted by `claim_id`.

## Empty evidence

When no evidence was retrieved, the narrative states:
_"No evidence was retrieved. No claims, gaps, or findings were produced."_

## Usage

```python
from research_core.synthesis import DeterministicSynthesizer

synth = DeterministicSynthesizer()
result = synth.synthesize(request, evidence, claims, contradictions, gaps, open_questions)
print(result.narrative)
print(result.key_findings)
```
