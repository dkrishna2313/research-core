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

The narrative is assembled by joining these parts:

1. A count sentence: _"The research produced P claim(s) from N evidence item(s) across M source(s). Q research gap(s) were identified."_
2. If critical or high-severity gaps exist: _"Notable gap(s): X critical, Y high-severity gap(s) require attention."_
3. If contradictions exist: _"Z contradiction(s) were detected in the evidence. Contradictions are not resolved by this synthesizer."_
4. A limitations disclaimer: _"This synthesis was produced deterministically from extracted claims and evidence. It does not imply verification, truth, consensus, or corroboration. Claim wording is preserved as extracted. Conflicting claims are not resolved."_

## Claim ordering

Key findings follow evidence order then claim_id lexicographic order for stability:

1. Claims supported by evidence item at index 0 appear first.
2. Among claims with the same lowest evidence index, sort by `claim_id`.
3. Claims with no supporting evidence appear at the end, sorted by `claim_id`.

## Empty evidence

When no evidence was retrieved, the narrative states:
_"No evidence was retrieved. This synthesis cannot derive claims from the available input. Research gaps indicate missing coverage."_
followed by the standard limitations disclaimer.

## Usage

```python
from research_core.synthesis import DeterministicSynthesizer

synth = DeterministicSynthesizer()
result = synth.synthesize(request, evidence, claims, contradictions, gaps, open_questions)
print(result.narrative)
print(result.key_findings)
```
