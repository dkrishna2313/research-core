# Synthesis Contracts

## Synthesizer protocol

`research_core.protocols.synthesis.Synthesizer` (runtime-checkable Protocol):

```python
class Synthesizer(Protocol):
    def synthesize(
        self,
        request: ResearchRequest,
        evidence: tuple[EvidenceItem, ...],
        claims: tuple[Claim, ...],
        contradictions: tuple[Contradiction, ...],
        gaps: tuple[ResearchGap, ...],
        open_questions: tuple[OpenQuestion, ...],
    ) -> SynthesisResult: ...
```

Any class that implements `synthesize` with this signature satisfies the protocol
structurally — no inheritance required.

## SynthesisResult contract

Defined in `research_core.contracts.result`:

- `narrative: str` — must be non-empty.
- `key_findings: tuple[str, ...]` — may be empty.
- `synthesis_model: str | None` — identifies the synthesizer.
- `synthesized_at: datetime | None` — UTC timestamp or None.
- `confidence: float | None` — scalar in [0.0, 1.0] or None.
- `metadata: Metadata` — immutable MappingProxyType.

## Engine integration

The engine calls `synthesizer.synthesize(...)` at stage 7. If `synthesize`
raises any exception, the engine catches it, emits a FAILED trace event,
sets `synthesis=None`, and sets `status=PARTIAL`. This is the
**mandatory partial-result semantic** — synthesis failure never propagates
as an exception to the caller (unless `request.strict=True`).

## DeterministicSynthesizer

`research_core.synthesis.DeterministicSynthesizer`:

- Satisfies `Synthesizer` protocol.
- Returns `synthesized_at=None` and `confidence=None`.
- `synthesis_model = "DeterministicSynthesizer/1.0"`.
- Does not call any LLM, read any file, or make any network request.
- Import boundary: must not import from `research_core.adapters` or any
  optional vendor SDK.
