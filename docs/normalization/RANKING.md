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
| `provenance_completeness` | 0.10 | Computed: fraction of non-None provenance fields |

`provenance_completeness` is always computable (never `None`) since it is derived from counting. The other five components may be `None` if the adapter did not produce that signal.

## Missing Value Policy ("proportional")

Components with a `None` value are excluded from both the numerator and denominator of the score. Available component weights are renormalized to sum to 1.0 among themselves.

```
available = [(name, value, base_weight) for each component if value is not None]
total_weight = sum(base_weight for _, _, base_weight in available)
score = sum(value * base_weight / total_weight for _, value, base_weight in available)
```

Real `0.0` values **are** included — only `None` is treated as missing.

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
