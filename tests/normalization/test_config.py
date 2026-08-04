"""Tests for normalization config dataclasses."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.normalization

from research_core.exceptions import ContractValidationError  # noqa: E402
from research_core.normalization.config import (  # noqa: E402
    NormalizationConfig,
    RankingConfig,
    RankingWeights,
    SegmentationConfig,
)


class TestSegmentationConfig:
    def test_defaults_are_sensible(self) -> None:
        cfg = SegmentationConfig()
        assert cfg.max_characters == 6000
        assert cfg.target_characters == 4500
        assert cfg.overlap_characters == 300
        assert cfg.minimum_segment_characters == 200
        assert cfg.preserve_paragraphs is True
        assert cfg.version == "1"

    def test_target_exceeds_max_raises(self) -> None:
        with pytest.raises(ContractValidationError, match="target_characters"):
            SegmentationConfig(max_characters=1000, target_characters=2000)

    def test_overlap_exceeds_target_raises(self) -> None:
        with pytest.raises(ContractValidationError, match="overlap_characters"):
            SegmentationConfig(target_characters=300, overlap_characters=300)

    def test_custom_values(self) -> None:
        cfg = SegmentationConfig(
            max_characters=10000, target_characters=8000, overlap_characters=100
        )
        assert cfg.max_characters == 10000


class TestRankingWeights:
    def test_defaults_sum_to_one(self) -> None:
        w = RankingWeights()
        total = (
            w.retrieval + w.relevance + w.authority
            + w.recency + w.extraction_confidence + w.provenance_completeness
        )
        assert abs(total - 1.0) < 1e-9

    def test_out_of_range_raises(self) -> None:
        with pytest.raises(ContractValidationError, match="retrieval"):
            RankingWeights(retrieval=1.5)

    def test_negative_raises(self) -> None:
        with pytest.raises(ContractValidationError, match="relevance"):
            RankingWeights(relevance=-0.1)

    def test_all_zero_raises(self) -> None:
        with pytest.raises(ContractValidationError):
            RankingWeights(
                retrieval=0.0,
                relevance=0.0,
                authority=0.0,
                recency=0.0,
                extraction_confidence=0.0,
                provenance_completeness=0.0,
            )


class TestRankingConfig:
    def test_defaults(self) -> None:
        cfg = RankingConfig()
        assert cfg.near_duplicate_threshold == 0.90
        assert cfg.missing_value_policy == "proportional"
        assert cfg.max_near_duplicate_comparisons == 1000

    def test_fingerprint_is_hex_string(self) -> None:
        fp = RankingConfig().fingerprint
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)

    def test_fingerprint_changes_with_weights(self) -> None:
        cfg1 = RankingConfig()
        cfg2 = RankingConfig(weights=RankingWeights(retrieval=0.5, relevance=0.1, authority=0.1,
                                                     recency=0.1, extraction_confidence=0.1,
                                                     provenance_completeness=0.1))
        assert cfg1.fingerprint != cfg2.fingerprint

    def test_fingerprint_is_stable(self) -> None:
        cfg = RankingConfig()
        assert cfg.fingerprint == cfg.fingerprint

    def test_invalid_threshold_raises(self) -> None:
        with pytest.raises(ContractValidationError, match="near_duplicate_threshold"):
            RankingConfig(near_duplicate_threshold=0.0)

    def test_unsupported_policy_raises(self) -> None:
        with pytest.raises(ContractValidationError, match="missing_value_policy"):
            RankingConfig(missing_value_policy="zero")


class TestNormalizationConfig:
    def test_defaults(self) -> None:
        cfg = NormalizationConfig()
        assert isinstance(cfg.segmentation, SegmentationConfig)
        assert isinstance(cfg.ranking, RankingConfig)
