"""
Evidence segmentation — split long EvidenceItem content into overlapping chunks.

Segments are deterministic: same input → same segment IDs and boundaries.
Segment IDs are SHA256-based and stable across pipeline runs.
"""

from __future__ import annotations

import hashlib

from research_core.contracts.evidence import EvidenceItem
from research_core.normalization.config import SegmentationConfig

_DEFAULT_CONFIG = SegmentationConfig()


def segment_evidence(
    item: EvidenceItem,
    config: SegmentationConfig | None = None,
) -> tuple[EvidenceItem, ...]:
    """Split a long EvidenceItem into overlapping segments.

    Returns (item,) unchanged if content fits within max_characters.
    Segments preserve the parent's provenance, quality, source_id, and claim_links.
    Each segment gets a deterministic stable ID and locator annotation.
    """
    cfg = config or _DEFAULT_CONFIG
    content = item.content

    if len(content) <= cfg.max_characters:
        return (item,)

    chunks = _split_content(content, cfg)
    if not chunks:
        return (item,)

    total = len(chunks)
    segments: list[EvidenceItem] = []

    for idx, chunk_text in enumerate(chunks):
        seg_id = _segment_id(item.evidence_id, item.source_id, idx, cfg.version)

        if item.locator:
            locator = f"{item.locator} (segment {idx + 1}/{total})"
        else:
            locator = f"segment {idx + 1}/{total}"

        seg_metadata: dict[str, object] = {
            "segment_index": idx,
            "segment_count": total,
            "parent_evidence_id": item.evidence_id,
        }

        segments.append(
            EvidenceItem(
                evidence_id=seg_id,
                content=chunk_text,
                source_id=item.source_id,
                provenance=item.provenance,
                quality=item.quality,
                claim_links=item.claim_links,
                locator=locator,
                observed_at=item.observed_at,
                metadata=seg_metadata,
            )
        )

    return tuple(segments)


def _segment_id(parent_id: str, source_id: str, idx: int, version: str) -> str:
    key = f"{parent_id}\x00{source_id}\x00{idx}\x00{version}"
    return "seg-" + hashlib.sha256(key.encode()).hexdigest()[:16]


def _split_content(content: str, cfg: SegmentationConfig) -> list[str]:
    """Split content into chunks respecting paragraph boundaries when possible."""
    if cfg.preserve_paragraphs:
        chunks = _split_at_paragraphs(content, cfg)
    else:
        chunks = _split_by_chars(content, cfg.target_characters, cfg.overlap_characters)

    # Drop too-short trailing segments by merging into the previous one
    if len(chunks) > 1:
        last = chunks[-1]
        if len(last) < cfg.minimum_segment_characters:
            chunks = chunks[:-1]
            if chunks:
                chunks[-1] = chunks[-1] + last

    return chunks


def _split_at_paragraphs(content: str, cfg: SegmentationConfig) -> list[str]:
    """Split preferring paragraph boundaries (\n\n or \n)."""
    paragraphs = content.split("\n\n")

    # Flatten paragraphs that are themselves too long
    expanded: list[str] = []
    for para in paragraphs:
        if len(para) > cfg.target_characters:
            sub = _split_by_chars(para, cfg.target_characters, 0)
            expanded.extend(sub)
        else:
            expanded.append(para)

    # Merge small paragraphs into chunks up to target_characters
    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for para in expanded:
        para_len = len(para)
        # +2 for the \n\n separator when joining
        if current_len > 0 and current_len + 2 + para_len > cfg.target_characters:
            chunk = "\n\n".join(current_parts)
            chunks.append(chunk)
            # Start overlap: take end of previous chunk
            overlap_text = chunk[-cfg.overlap_characters :] if cfg.overlap_characters > 0 else ""
            current_parts = [overlap_text, para] if overlap_text else [para]
            current_len = len(overlap_text) + (2 if overlap_text else 0) + para_len
        else:
            current_parts.append(para)
            current_len += (2 if current_len > 0 else 0) + para_len

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return [c for c in chunks if c.strip()] or [content]


def _split_by_chars(content: str, target: int, overlap: int) -> list[str]:
    """Plain character-based splitting with overlap."""
    if len(content) <= target:
        return [content]

    chunks: list[str] = []
    start = 0
    while start < len(content):
        end = min(start + target, len(content))
        chunks.append(content[start:end])
        if end >= len(content):
            break
        start = end - overlap if overlap > 0 else end

    return chunks
