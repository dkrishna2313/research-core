# Evidence Deduplication

## Overview

`detect_duplicates()` removes exact and near-duplicate evidence items before ranking. It returns the canonical items, plus `DuplicateEvidence` and `ExcludedEvidence` records for auditability.

## Exact Deduplication

Content is normalized with Unicode NFC normalization before hashing:

```
hash = sha256(unicodedata.normalize("NFC", content).encode()).hexdigest()
```

All items with the same hash are grouped. The canonical item is selected by the priority rule below; all others are recorded as exact duplicates with `similarity=1.0`.

## Near-Duplicate Detection

Near-duplicate detection applies only to items with `content_length >= 200` characters.

**Tokenization:** `frozenset(re.findall(r'\b\w+\b', content.lower()))`. Numeric tokens are included so that texts differing only in numeric values (e.g. `$10 million` vs `$100 million`, `2024` vs `2025`, `20%` vs `25%`) produce distinct token sets and are not incorrectly collapsed as near-duplicates.

**Jaccard similarity:** `|A ∩ B| / |A ∪ B|`

If Jaccard ≥ `RankingConfig.near_duplicate_threshold`, the lower-priority item is recorded as a near-duplicate.

**Comparison budget:** Total comparisons are bounded by `max_near_duplicate_comparisons` to avoid O(n²) cost at scale.

## Canonical Selection

Given a group of duplicates, the canonical item is the one with:

1. **Best provenance completeness** (most non-None fields among: `provider`, `retrieval_query`, `retrieval_rank`, `retrieval_score`, `extraction_method`, `extraction_confidence`, `content_hash`, `url`, `document_id`)
2. **Lowest provider_rank** (None treated as infinity)
3. **source_id** ascending (lexicographic)
4. **evidence_id** ascending (lexicographic)

## Configuration

| Field | Default | Description |
|-------|---------|-------------|
| `near_duplicate_threshold` | 0.90 | Jaccard threshold for near-dup detection (0,1] |
| `max_near_duplicate_comparisons` | 1000 | Maximum pairwise comparisons |

## Usage

```python
from research_core.normalization import detect_duplicates, RankingConfig

cfg = RankingConfig(near_duplicate_threshold=0.85)
kept, duplicates, excluded = detect_duplicates(items, cfg)

print(f"Kept {len(kept)}, excluded {len(excluded)}")
for dup in duplicates:
    print(f"{dup.evidence_id} is {dup.method} of {dup.canonical_id} (sim={dup.similarity:.3f})")
```
