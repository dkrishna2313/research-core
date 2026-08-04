"""Tests for Contradiction contract."""

from __future__ import annotations

import pytest

from research_core.contracts.contradictions import (
    ContradictionResolutionStatus,
    ContradictionSeverity,
    ContradictionType,
)
from research_core.exceptions import ContractValidationError
from tests.conftest import make_contradiction


class TestContradictionConstruction:
    def test_minimal_with_two_claims(self) -> None:
        con = make_contradiction(claim_ids=("cl-1", "cl-2"))
        assert con.contradiction_id == "con-1"

    def test_minimal_with_two_evidence(self) -> None:
        con = make_contradiction(claim_ids=(), evidence_ids=("ev-1", "ev-2"))
        assert con.evidence_ids == ("ev-1", "ev-2")

    def test_minimal_with_one_claim_one_evidence(self) -> None:
        con = make_contradiction(claim_ids=("cl-1",), evidence_ids=("ev-1",))
        assert len(con.claim_ids) + len(con.evidence_ids) == 2

    def test_less_than_two_references_rejected(self) -> None:
        with pytest.raises(ContractValidationError, match="two"):
            make_contradiction(claim_ids=("cl-1",), evidence_ids=())

    def test_zero_references_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_contradiction(claim_ids=(), evidence_ids=())

    def test_empty_contradiction_id_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_contradiction(contradiction_id="")

    def test_empty_description_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_contradiction(description="")

    def test_defaults(self) -> None:
        con = make_contradiction()
        assert con.severity == ContradictionSeverity.MEDIUM
        assert con.resolution_status == ContradictionResolutionStatus.UNRESOLVED
        assert con.resolution_notes == ""


class TestContradictionEnums:
    def test_all_contradiction_types_exist(self) -> None:
        expected = {
            "NUMERIC", "TEMPORAL", "DEFINITIONAL", "SCOPE",
            "METHODOLOGICAL", "ENTITY_IDENTITY", "CATEGORICAL", "OTHER",
        }
        assert {m.name for m in ContradictionType} == expected

    def test_severities_exist(self) -> None:
        assert ContradictionSeverity.LOW
        assert ContradictionSeverity.MEDIUM
        assert ContradictionSeverity.HIGH
        assert ContradictionSeverity.CRITICAL

    def test_resolution_statuses_exist(self) -> None:
        assert ContradictionResolutionStatus.UNRESOLVED
        assert ContradictionResolutionStatus.ACKNOWLEDGED
        assert ContradictionResolutionStatus.RESOLVED

    def test_values_are_strings(self) -> None:
        for member in ContradictionType:
            assert isinstance(member.value, str)
