"""
Tests for GapAnalysisConfig validation and fingerprint stability.
"""

from __future__ import annotations

import pytest

from research_core.analysis.config import GapAnalysisConfig
from research_core.exceptions import ContractValidationError


@pytest.mark.diagnostics
class TestGapAnalysisConfigDefaults:
    def test_default_construction(self) -> None:
        cfg = GapAnalysisConfig()
        assert cfg.minimum_evidence_count == 2
        assert cfg.minimum_source_count == 1
        assert cfg.analyzer_version == "1"

    def test_frozen(self) -> None:
        cfg = GapAnalysisConfig()
        with pytest.raises((AttributeError, TypeError)):
            cfg.minimum_evidence_count = 99  # type: ignore[misc]


@pytest.mark.diagnostics
class TestGapAnalysisConfigValidation:
    def test_negative_evidence_count_rejected(self) -> None:
        with pytest.raises(ContractValidationError, match="minimum_evidence_count"):
            GapAnalysisConfig(minimum_evidence_count=-1)

    def test_negative_source_count_rejected(self) -> None:
        with pytest.raises(ContractValidationError, match="minimum_source_count"):
            GapAnalysisConfig(minimum_source_count=-1)

    def test_ratio_above_one_rejected(self) -> None:
        with pytest.raises(ContractValidationError, match="minimum_claim_coverage_ratio"):
            GapAnalysisConfig(minimum_claim_coverage_ratio=1.5)

    def test_ratio_below_zero_rejected(self) -> None:
        with pytest.raises(ContractValidationError, match="minimum_relevance_score"):
            GapAnalysisConfig(minimum_relevance_score=-0.1)

    def test_empty_analyzer_version_rejected(self) -> None:
        with pytest.raises(ContractValidationError, match="analyzer_version"):
            GapAnalysisConfig(analyzer_version="   ")

    def test_nan_ratio_rejected(self) -> None:
        import math

        with pytest.raises(ContractValidationError):
            GapAnalysisConfig(minimum_relevance_score=math.nan)

    def test_inf_ratio_rejected(self) -> None:
        import math

        with pytest.raises(ContractValidationError):
            GapAnalysisConfig(minimum_authority_score=math.inf)

    def test_zero_thresholds_valid(self) -> None:
        cfg = GapAnalysisConfig(
            minimum_evidence_count=0,
            minimum_source_count=0,
            minimum_relevance_score=0.0,
        )
        assert cfg.minimum_evidence_count == 0

    def test_boundary_ratios_valid(self) -> None:
        cfg = GapAnalysisConfig(
            minimum_claim_coverage_ratio=0.0,
            maximum_single_source_share=1.0,
        )
        assert cfg.minimum_claim_coverage_ratio == 0.0


@pytest.mark.diagnostics
class TestGapAnalysisConfigFingerprint:
    def test_fingerprint_is_string(self) -> None:
        cfg = GapAnalysisConfig()
        assert isinstance(cfg.fingerprint, str)

    def test_fingerprint_length(self) -> None:
        cfg = GapAnalysisConfig()
        assert len(cfg.fingerprint) == 16

    def test_same_config_same_fingerprint(self) -> None:
        a = GapAnalysisConfig()
        b = GapAnalysisConfig()
        assert a.fingerprint == b.fingerprint

    def test_different_config_different_fingerprint(self) -> None:
        a = GapAnalysisConfig(minimum_evidence_count=2)
        b = GapAnalysisConfig(minimum_evidence_count=5)
        assert a.fingerprint != b.fingerprint

    def test_fingerprint_excludes_include_passed_conditions(self) -> None:
        a = GapAnalysisConfig(include_passed_conditions=False)
        b = GapAnalysisConfig(include_passed_conditions=True)
        # include_passed_conditions is behavioral only, not semantic
        assert a.fingerprint == b.fingerprint

    def test_fingerprint_stable_across_instances(self) -> None:
        fp1 = GapAnalysisConfig(minimum_relevance_score=0.4).fingerprint
        fp2 = GapAnalysisConfig(minimum_relevance_score=0.4).fingerprint
        assert fp1 == fp2
