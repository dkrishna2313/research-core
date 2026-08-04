"""Tests for Claim contract."""

from __future__ import annotations

import types

import pytest

from research_core.contracts.claims import ClaimStatus, ClaimType
from research_core.exceptions import ContractValidationError
from tests.conftest import make_claim


class TestClaimConstruction:
    def test_minimal_construction(self) -> None:
        cl = make_claim()
        assert cl.claim_id == "cl-1"
        assert cl.statement == "Test claim statement."

    def test_defaults(self) -> None:
        cl = make_claim()
        assert cl.claim_type == ClaimType.FACTUAL
        assert cl.status == ClaimStatus.UNRESOLVED
        assert cl.confidence == 0.0
        assert cl.qualifiers == ()
        assert cl.supporting_evidence_ids == ()
        assert cl.conflicting_evidence_ids == ()

    def test_empty_claim_id_rejected(self) -> None:
        with pytest.raises(ContractValidationError, match="claim_id"):
            make_claim(claim_id="")

    def test_empty_statement_rejected(self) -> None:
        with pytest.raises(ContractValidationError, match="statement"):
            make_claim(statement="")

    def test_whitespace_statement_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_claim(statement="   ")

    def test_confidence_above_one_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_claim(confidence=1.1)

    def test_confidence_below_zero_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_claim(confidence=-0.1)

    def test_confidence_at_boundaries_accepted(self) -> None:
        cl0 = make_claim(confidence=0.0)
        cl1 = make_claim(confidence=1.0)
        assert cl0.confidence == 0.0
        assert cl1.confidence == 1.0

    def test_metadata_wrapped(self) -> None:
        cl = make_claim(metadata={"k": "v"})
        assert isinstance(cl.metadata, types.MappingProxyType)


class TestClaimImmutability:
    def test_is_frozen(self) -> None:
        cl = make_claim()
        with pytest.raises((AttributeError, TypeError)):
            cl.statement = "other"  # type: ignore[misc]


class TestClaimEnums:
    def test_claim_type_values_are_strings(self) -> None:
        for member in ClaimType:
            assert isinstance(member.value, str)

    def test_claim_status_values_are_strings(self) -> None:
        for member in ClaimStatus:
            assert isinstance(member.value, str)

    def test_expected_claim_types_exist(self) -> None:
        assert ClaimType.FACTUAL
        assert ClaimType.ANALYTICAL
        assert ClaimType.PREDICTIVE
        assert ClaimType.NORMATIVE
        assert ClaimType.DEFINITIONAL
        assert ClaimType.OTHER

    def test_expected_claim_statuses_exist(self) -> None:
        assert ClaimStatus.SUPPORTED
        assert ClaimStatus.PARTIALLY_SUPPORTED
        assert ClaimStatus.CONTESTED
        assert ClaimStatus.UNSUPPORTED
        assert ClaimStatus.UNRESOLVED
