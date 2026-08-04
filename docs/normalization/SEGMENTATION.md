# Evidence Segmentation

## Overview

The segmenter splits `EvidenceItem` objects whose content exceeds `SegmentationConfig.max_characters` into overlapping segments. Short items are returned unchanged.

## Algorithm

1. If `len(content) <= max_characters`: return `(item,)` unchanged.
2. If `preserve_paragraphs=True`: attempt to split at `\n\n` paragraph boundaries.
   - Paragraphs longer than `target_characters` are sub-split by character count.
   - Adjacent paragraphs are merged until the next addition would exceed `target_characters`.
   - Each merged block becomes a segment; the next block begins with `overlap_characters` of overlap from the end of the previous block.
3. If `preserve_paragraphs=False`: plain character-based splitting with overlap.
4. Trailing segments shorter than `minimum_segment_characters` are merged into the preceding segment (unless it is the only segment).

## Segment IDs

Each segment receives a stable, deterministic ID:

```
"seg-" + sha256(parent_id + "\x00" + source_id + "\x00" + str(idx) + "\x00" + version)[:16]
```

Incrementing `SegmentationConfig.version` invalidates all existing segment IDs. This is intentional — if segmentation logic changes, downstream consumers using segment IDs as cache keys will correctly cache-miss.

## Configuration

| Field | Default | Description |
|-------|---------|-------------|
| `max_characters` | 6000 | Items up to this length are returned unchanged |
| `target_characters` | 4500 | Preferred segment length (must be ≤ max_characters) |
| `overlap_characters` | 300 | Characters copied from end of previous segment |
| `minimum_segment_characters` | 200 | Minimum viable segment; shorter ones are merged |
| `preserve_paragraphs` | True | Prefer `\n\n` boundaries over mid-paragraph splits |
| `version` | "1" | Part of the segment ID hash |

## Usage

```python
from research_core.normalization import segment_evidence, SegmentationConfig

cfg = SegmentationConfig(max_characters=3000, target_characters=2500)
segments = segment_evidence(item, cfg)

for seg in segments:
    print(seg.evidence_id, seg.metadata["segment_index"], "/", seg.metadata["segment_count"])
```

## Segment Metadata

Each segment's `metadata` contains:

| Key | Type | Description |
|-----|------|-------------|
| `segment_index` | int | 0-based index within the parent item |
| `segment_count` | int | Total number of segments for this parent |
| `parent_evidence_id` | str | `evidence_id` of the unsegmented parent |

The `NormalizedEvidence` wrapper elevates these into first-class fields (`segment_index`, `segment_count`, `parent_evidence_id`).
