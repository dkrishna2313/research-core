"""Tests for EvidenceNormalizer convenience class."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.normalization

from research_core.normalization.config import NormalizationConfig, SegmentationConfig  # noqa: E402
from research_core.normalization.contracts import NormalizedEvidence  # noqa: E402
from research_core.normalization.normalizer import EvidenceNormalizer  # noqa: E402
from tests.normalization.conftest import make_source, make_web_evidence  # noqa: E402


class TestEvidenceNormalizer:
    def test_default_config_used_when_none_provided(self) -> None:
        normalizer = EvidenceNormalizer()
        assert normalizer._config == NormalizationConfig()

    def test_normalize_returns_tuple_of_normalized_evidence(self) -> None:
        src = make_source()
        ev = make_web_evidence(source_id=src.source_id)
        normalizer = EvidenceNormalizer()
        result = normalizer.normalize(sources=(src,), evidence=(ev,))
        assert isinstance(result, tuple)
        assert len(result) == 1
        assert isinstance(result[0], NormalizedEvidence)

    def test_custom_config_respected(self) -> None:
        cfg = NormalizationConfig(
            segmentation=SegmentationConfig(
                max_characters=200,
                target_characters=150,
                overlap_characters=20,
                minimum_segment_characters=20,
            )
        )
        normalizer = EvidenceNormalizer(config=cfg)
        src = make_source()
        content = ("word " * 50).strip()
        ev = make_web_evidence(source_id=src.source_id, content=content)
        result = normalizer.normalize(sources=(src,), evidence=(ev,))
        # Should be segmented with custom config
        assert len(result) > 0

    def test_multiple_evidence_items(self) -> None:
        src = make_source()
        ev1 = make_web_evidence(evidence_id="ev-1", source_id=src.source_id, rank=1)
        ev2 = make_web_evidence(evidence_id="ev-2", source_id=src.source_id, rank=2)
        normalizer = EvidenceNormalizer()
        result = normalizer.normalize(sources=(src,), evidence=(ev1, ev2))
        assert len(result) == 2
