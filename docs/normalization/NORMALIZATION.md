# Evidence Normalization and Ranking

The `research_core.normalization` package provides a provider-neutral layer for normalizing, deduplicating, and ranking evidence items gathered from the Knowledge and Web adapters.

## Overview

Raw evidence from adapters differs in structure: Knowledge items carry a retrieval score; Web items carry a rank position but no score. Long documents from either adapter may contain more content than a downstream consumer can efficiently process. The normalization layer resolves these differences into a uniform `NormalizedEvidence` representation, removes duplicate content, and produces a deterministically ranked result.

## Architecture

```
KnowledgeAdapter    WebSearchAdapter
       |                  |
       +-----+------------+
             |
    normalize_evidence()
             |
    NormalizedEvidence[]
             |
    detect_duplicates()
             |
    rank_evidence()
             |
    EvidenceRankingResult
```

The three stages can be invoked individually or through the `EvidenceNormalizer` / `EvidenceRanker` convenience wrappers.

## Segmentation

Long evidence items (content exceeding `SegmentationConfig.max_characters`) are split into overlapping segments before normalization. See [SEGMENTATION.md](SEGMENTATION.md) for details.

## Deduplication

Exact duplicates are detected by SHA-256 of NFC-normalized content. Near-duplicates are detected by Jaccard similarity on lowercased token sets. See [DEDUPLICATION.md](DEDUPLICATION.md) for details.

## Ranking

A multi-component scoring function with six dimensions produces a composite score in [0, 1] for each item. Missing dimensions are handled by proportional reweighting. See [RANKING.md](RANKING.md) for details.

## Capability Reporting

```python
from research_core.normalization import capability_report_for_knowledge, capability_report_for_web

report = capability_report_for_web(adapter)
for cap in report.capabilities:
    print(f"{cap.name}: {cap.status}")
```

Neither function performs network calls or opens the knowledge store.

## Usage Examples

### Full pipeline

```python
from research_core.normalization import EvidenceNormalizer, EvidenceRanker

normalizer = EvidenceNormalizer()
ranker = EvidenceRanker()

normalized = normalizer.normalize(sources=sources, evidence=evidence)
result = ranker.rank(normalized)

for ranked in result.ranked:
    print(f"#{ranked.rank}  score={ranked.score:.4f}  {ranked.normalized_evidence.evidence.evidence_id}")
```

### Custom configuration

```python
from research_core.normalization import (
    EvidenceNormalizer, EvidenceRanker,
    NormalizationConfig, SegmentationConfig, RankingConfig, RankingWeights,
)

config = NormalizationConfig(
    segmentation=SegmentationConfig(max_characters=4000, target_characters=3000),
    ranking=RankingConfig(
        weights=RankingWeights(retrieval=0.5, relevance=0.3, authority=0.2,
                               recency=0.0, extraction_confidence=0.0,
                               provenance_completeness=0.0),
        near_duplicate_threshold=0.85,
    ),
)

normalizer = EvidenceNormalizer(config=config)
ranker = EvidenceRanker(config=config.ranking)
```

### Explainability

Every `RankedEvidence` carries a `components` tuple exposing per-dimension scores:

```python
for ranked in result.ranked:
    for comp in ranked.components:
        if comp.normalized_value is not None:
            print(f"  {comp.name}: {comp.normalized_value:.3f} (weight {comp.weight_used:.3f})")
        else:
            print(f"  {comp.name}: MISSING")
```

## Configuration Reference

### SegmentationConfig

| Field | Default | Description |
|-------|---------|-------------|
| `max_characters` | 6000 | Hard upper bound per segment |
| `target_characters` | 4500 | Preferred segment size |
| `overlap_characters` | 300 | Characters of overlap between segments |
| `minimum_segment_characters` | 200 | Minimum viable segment size |
| `preserve_paragraphs` | True | Prefer paragraph boundary splits |
| `version` | "1" | Incorporated into segment ID hashes |

### RankingWeights (defaults)

| Component | Default | Signal source |
|-----------|---------|---------------|
| `retrieval` | 0.35 | `normalized_retrieval_signal` |
| `relevance` | 0.25 | `quality.relevance` |
| `authority` | 0.15 | `quality.authority` |
| `recency` | 0.10 | `quality.recency` |
| `extraction_confidence` | 0.05 | `provenance.extraction_confidence` |
| `provenance_completeness` | 0.10 | Computed from provenance fields |

Weights sum to 1.0. Missing values are excluded from the denominator (proportional reweighting).
