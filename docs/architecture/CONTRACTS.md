# Contracts Reference — RC1

`research_core.contracts` defines the typed domain model. These are the objects that flow
through the pipeline and are returned to callers. No engine logic lives here.

---

## Design Principles

**Frozen dataclasses.** Every contract type is `@dataclass(frozen=True)`. Mutation is
prevented at the Python level. Normalization (e.g. stripping whitespace, deduplicating profiles)
happens in `__post_init__` via `object.__setattr__`.

**Immutable metadata.** All `metadata` fields are stored as `types.MappingProxyType`. Any dict
passed in is wrapped at construction time. The `EMPTY_METADATA` sentinel is reused for no-metadata
fields.

**None ≠ zero.** Optional score fields (`float | None`) use `None` to mean "not assessed." Code
that treats `None` as `0.0` is semantically wrong. This is enforced by tests.

**Tuples over lists.** All repeated fields use `tuple`, not `list`. This prevents mutation through
caller references and makes the immutability contract visible in the type signature.

**StrEnum for all enumerations.** All enum types inherit from `enum.StrEnum` (Python 3.11+). This
ensures that enum values serialize cleanly to strings without special handling and that
`str(member) == member.value`.

---

## Type Aliases

```python
ClaimId = str
EvidenceId = str
SourceId = str
DocumentId = str
ContradictionId = str
ResearchGapId = str
TraceEventId = str
ProfileId = str

Metadata = Mapping[str, Any]
EMPTY_METADATA: Metadata  # singleton empty MappingProxyType
```

All identifiers are non-empty strings by convention (validated where they appear as required fields).

---

## Contract Dependency Graph

```
ResearchRequest
    └── (input, no dependencies)

Source
    └── SourceType

Provenance
    └── SourceType

EvidenceQuality
    └── (standalone)

EvidenceItem
    ├── EvidenceClaimLink → ClaimId
    ├── Provenance
    ├── EvidenceQuality
    └── SourceId → Source

Claim
    ├── ClaimType, ClaimStatus
    ├── supporting_evidence_ids → EvidenceId
    └── conflicting_evidence_ids → EvidenceId

Contradiction
    ├── ContradictionType, ContradictionSeverity, ContradictionResolutionStatus
    ├── claim_ids → ClaimId
    └── evidence_ids → EvidenceId

ResearchGap
    ├── GapType, GapSeverity, GapStatus
    ├── related_claim_ids → ClaimId
    └── related_evidence_ids → EvidenceId

OpenQuestion
    ├── QuestionPriority
    ├── related_claim_ids → ClaimId
    └── related_gap_ids → ResearchGapId

QualityDimension
    └── (standalone, score: float | None)

QualityDiagnostics
    └── 12 × QualityDimension + optional composite

TraceEvent
    └── TraceStage, TraceEventStatus

ResearchTrace
    └── tuple[TraceEvent, ...]

SynthesisResult
    └── (standalone)

ResearchResult
    ├── ResearchRequest
    ├── ResearchStatus
    ├── tuple[Source, ...]
    ├── tuple[EvidenceItem, ...]
    ├── tuple[Claim, ...]
    ├── tuple[Contradiction, ...]
    ├── tuple[ResearchGap, ...]
    ├── tuple[OpenQuestion, ...]
    ├── SynthesisResult | None
    ├── QualityDiagnostics | None
    └── ResearchTrace | None
```

---

## ResearchResult Graph Validation

`ResearchResult.__post_init__` validates full graph consistency:

| Check | What it enforces |
|---|---|
| Unique source IDs | No two `Source` objects share a `source_id` |
| Unique evidence IDs | No two `EvidenceItem` objects share an `evidence_id` |
| Unique claim IDs | No two `Claim` objects share a `claim_id` |
| Unique contradiction IDs | No two `Contradiction` objects share a `contradiction_id` |
| Unique gap IDs | No two `ResearchGap` objects share a `gap_id` |
| Evidence → Source | Every `EvidenceItem.source_id` resolves to a `Source` |
| EvidenceClaimLink → Claim | Every link's `claim_id` resolves to a `Claim` |
| Claim → Evidence | Every ID in `supporting/conflicting_evidence_ids` resolves to an `EvidenceItem` |
| Contradiction → Claim/Evidence | All `claim_ids` and `evidence_ids` resolve |
| Gap → Claim/Evidence | All `related_claim_ids` and `related_evidence_ids` resolve |
| OpenQuestion → Claim/Gap | All `related_claim_ids` and `related_gap_ids` resolve |

Violations raise `ContractValidationError` at construction time.

---

## ResearchStatus

```python
class ResearchStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL  = "partial"
```

There is no `FAILED` status. A `ResearchResult` object only exists when the pipeline produced
useful evidence. Failures before any useful output raise typed exceptions
(`ProviderUnavailableError`, `ProviderExecutionError`, etc.).

A `PARTIAL` result has `status=ResearchStatus.PARTIAL`. The caller receives the partial result
instead of an exception. Gaps and quality diagnostics describe what is missing.

---

## Quality Model

`QualityDiagnostics` provides 12 independently-accessible named dimensions:

| Dimension | Direction | Meaning |
|---|---|---|
| `relevance` | ↑ better | Evidence relevance to the question |
| `authority` | ↑ better | Source authority and credibility |
| `recency` | ↑ better | How current the evidence is |
| `corroboration` | ↑ better | Degree of independent confirmation |
| `independence` | ↑ better | Source independence (no circular refs) |
| `coverage` | ↑ better | Breadth of question coverage |
| `extraction_confidence` | ↑ better | Confidence in evidence extraction |
| `contradiction_severity` | ↑ worse | Severity of unresolved contradictions |
| `uncertainty` | ↑ worse | Degree of claim uncertainty |
| `completeness` | ↑ better | Completeness of the research |
| `provenance_completeness` | ↑ better | Completeness of retrieval lineage |
| `reproducibility` | ↑ better | Reproducibility of the research run |

A `None` score means the dimension was not assessed. Consumers must not treat `None` as `0.0`.
A `composite` score may be provided as a convenience but does not replace component scores.

---

## Serialization

`serialize(obj)` converts any contract dataclass to a plain Python structure safe for
`json.dumps()`. Conversion rules:

- `dataclass` → `dict` of field name to serialized value
- `StrEnum` → `.value` (string)
- `datetime` → ISO 8601 string with timezone offset
- `date` → ISO 8601 date string
- `MappingProxyType` / `dict` → `dict`
- `tuple` / `list` → `list`
- `None`, `bool`, `int`, `float`, `str` → unchanged

```python
from research_core.contracts import serialize, ResearchResult

result: ResearchResult = ...
payload = serialize(result)
json_str = json.dumps(payload)
```

---

## Exception Hierarchy

```
ResearchCoreError
├── ContractValidationError      — invariant violated in a contract dataclass
├── InvalidResearchRequestError  — ResearchRequest field validation failure
├── UnknownProfileError          — ProfileProvider cannot resolve a profile_id
├── UnsupportedConfigurationError — configuration not supported by a provider
├── ProviderUnavailableError     — provider cannot be reached
├── ProviderExecutionError       — provider reached but execution failed
└── IncompleteResearchError      — raised when strict=True and result is PARTIAL
```

---

*This document covers the RC1 contract layer. See `ARCHITECTURE.md` for the full system
design and `ROADMAP.md` for the release schedule.*
