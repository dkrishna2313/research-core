# Evidence Ranking

## Overview

`rank_evidence()` assigns a composite score and final rank to each `NormalizedEvidence` item. Scores are deterministic and fully explainable — every `RankedEvidence` carries a `components` tuple exposing per-dimension values, weights, and statuses.

**The score is a ranking signal, not a probability or truth score.** It is calibrated for relative ordering only.

## Scoring Components

| Component | Default weight | Source |
|-----------|---------------|--------|
| `retrieval` | 0.35 | `normalized_retrieval_signal` |
| `relevance` | 0.25 | `evidence.quality.relevance` |
| `authority` | 0.15 | `evidence.quality.authority` |
| `recency` | 0.10 | `evidence.quality.recency` |
| `extraction_confidence` | 0.05 | `evidence.provenance.extraction_confidence` |
| `provenance_completeness` | 0.10 | Computed: fraction of applicable provenance fields present |

`provenance_completeness` is always computable (never `None`) since it is derived from counting. The other five components may be `None` if the adapter did not produce that signal.

### Provenance Completeness — Provider-Aware Formula

`provenance_completeness` is a **structural completeness** signal. It is not authority, credibility, trustworthiness, or factual confidence. It measures whether the provenance record contains the fields expected for its provider type.

Each provider type has its own applicable field set so that naturally absent fields are not penalised:

**Common fields** (all providers):

| Field | Notes |
|-------|-------|
| `provider` | Provider identity string |
| `retrieval_query` | Query that retrieved this evidence |
| `content_hash` | SHA-256 of extracted content |

**Web-specific fields** (`SourceType.WEB`):

| Field | Notes |
|-------|-------|
| `url` | Source URL — expected for Web results |
| `retrieval_rank` | DuckDuckGo result position |
| `extraction_method` | e.g. `trafilatura`, `pypdf` |

**Knowledge-specific fields** (`SourceType.KNOWLEDGE`):

| Field | Notes |
|-------|-------|
| `retrieval_rank` | Rank within knowledge store results |
| `retrieval_score` | Similarity score from the knowledge store |
| `extraction_method` | e.g. `text` |

**Fallback fields** (unknown source types):

| Field | Notes |
|-------|-------|
| `retrieval_rank` | Conservative minimal set |

**Field presence semantics:**

| Value | Treated as |
|-------|-----------|
| `None` | Missing |
| `""` or `"   "` (empty/whitespace string) | Missing |
| `0` or `0.0` (numeric zero) | **Present** |
| `False` | Present |
| Any non-empty string | Present |
| Any non-None non-string | Present |

Numeric zero is explicitly present — a `retrieval_score=0.0` or `retrieval_rank=0` is a real value, not an absence.

**Formula:**

```
applicable = provider_specific_field_set
present = count(field for field in applicable if _field_is_present(provenance[field]))
completeness = present / len(applicable)
```

Score range: `[0.0, 1.0]`. A structurally complete Web item without `retrieval_score` (which DDGS does not provide) scores `1.0`. A structurally complete Knowledge item without a URL scores `1.0`. Both provider types use 6 applicable fields.

## Missing Value Policy ("proportional")

Components with a `None` value are excluded from both the numerator and denominator of the score. Available component weights are renormalized to sum to 1.0 among themselves.

```
available = [(name, value, base_weight) for each component if value is not None]
total_weight = sum(base_weight for _, _, base_weight in available)
score = sum(value * base_weight / total_weight for _, value, base_weight in available)
```

Real `0.0` values **are** included — only `None` is treated as missing at the component level. Note that provenance-completeness field presence uses different semantics (see below): empty and whitespace-only strings also count as missing at the field level, while numeric zero remains present.

If all components are `None` (impossible in practice since `provenance_completeness` is always computed): `score = 0.0`.

## Tie-Breaking

Items with equal scores are ordered deterministically by (all comparisons):

1. `score` descending
2. `normalized_retrieval_signal` descending (`None` = −∞)
3. `provider_rank` ascending (`None` = +∞)
4. `source_id` ascending (lexicographic)
5. `evidence_id` ascending (lexicographic)
6. `segment_index` ascending (`None` = −1)

## Explainability

```python
for ranked in result.ranked:
    print(f"#{ranked.rank}  score={ranked.score:.4f}")
    for comp in ranked.components:
        status = comp.status.value
        if comp.normalized_value is not None:
            print(f"  {comp.name}: {comp.normalized_value:.3f} (weight={comp.weight_used:.3f}) [{status}]")
        else:
            print(f"  {comp.name}: MISSING")
```

## Diagnostics

`EvidenceRankingResult.diagnostics` includes:

| Field | Description |
|-------|-------------|
| `total_input` | Items ranked + items excluded (for accounting) |
| `total_ranked` | Items in `ranked` tuple |
| `total_excluded` | Items in `excluded` tuple (duplicates) |
| `total_duplicates` | Duplicate records in `duplicates` tuple |
| `config_fingerprint` | SHA-256 (16 chars) of the config — use for cache keying |

## Configuration

```python
from research_core.normalization import RankingConfig, RankingWeights

cfg = RankingConfig(
    weights=RankingWeights(
        retrieval=0.50,
        relevance=0.30,
        authority=0.20,
        recency=0.00,
        extraction_confidence=0.00,
        provenance_completeness=0.00,
    ),
    near_duplicate_threshold=0.90,
    missing_value_policy="proportional",
    max_near_duplicate_comparisons=1000,
)
```

Weights do not need to sum to 1.0 — proportional reweighting normalizes them at scoring time. However, all weights must be in [0, 1] and their sum must be > 0.
