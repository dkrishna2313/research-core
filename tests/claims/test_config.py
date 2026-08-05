"""Tests for ClaimExtractionConfig — validation, fingerprint stability."""

from __future__ import annotations

import pytest

from research_core.claims.config import ClaimExtractionConfig
from research_core.exceptions import ContractValidationError

pytestmark = pytest.mark.claims


def test_default_config_is_valid() -> None:
    cfg = ClaimExtractionConfig()
    assert cfg.minimum_claim_characters == 10
    assert cfg.maximum_claim_characters == 2000
    assert cfg.split_clauses is True
    assert cfg.deduplicate_exact is True


def test_config_frozen() -> None:
    import dataclasses

    cfg = ClaimExtractionConfig()
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.minimum_claim_characters = 5  # type: ignore[misc]


def test_min_greater_than_max_rejected() -> None:
    with pytest.raises(ContractValidationError):
        ClaimExtractionConfig(minimum_claim_characters=100, maximum_claim_characters=50)


def test_zero_minimum_rejected() -> None:
    with pytest.raises(ContractValidationError):
        ClaimExtractionConfig(minimum_claim_characters=0)


def test_zero_maximum_rejected() -> None:
    with pytest.raises(ContractValidationError):
        ClaimExtractionConfig(maximum_claim_characters=0)


def test_empty_normalization_version_rejected() -> None:
    with pytest.raises(ContractValidationError):
        ClaimExtractionConfig(normalization_version="")


def test_empty_extractor_version_rejected() -> None:
    with pytest.raises(ContractValidationError):
        ClaimExtractionConfig(extractor_version="")


def test_fingerprint_is_stable_across_calls() -> None:
    cfg = ClaimExtractionConfig()
    assert cfg.fingerprint == cfg.fingerprint


def test_fingerprint_changes_when_config_changes() -> None:
    cfg1 = ClaimExtractionConfig()
    cfg2 = ClaimExtractionConfig(minimum_claim_characters=20)
    assert cfg1.fingerprint != cfg2.fingerprint


def test_fingerprint_changes_with_version() -> None:
    cfg1 = ClaimExtractionConfig(extractor_version="1")
    cfg2 = ClaimExtractionConfig(extractor_version="2")
    assert cfg1.fingerprint != cfg2.fingerprint


def test_fingerprint_is_hex_string() -> None:
    cfg = ClaimExtractionConfig()
    fp = cfg.fingerprint
    assert isinstance(fp, str)
    assert len(fp) == 16
    int(fp, 16)  # must be valid hex


def test_equal_configs_have_equal_fingerprints() -> None:
    cfg1 = ClaimExtractionConfig(minimum_claim_characters=15)
    cfg2 = ClaimExtractionConfig(minimum_claim_characters=15)
    assert cfg1.fingerprint == cfg2.fingerprint
