"""Tests for EvidenceItem and EvidenceClaimLink contracts."""

from __future__ import annotations

import types
from datetime import datetime

import pytest

from research_core.contracts.evidence import (
    EvidenceClaimLink,
    EvidenceRelationship,
)
from research_core.exceptions import ContractValidationError
from tests.conftest import FIXED_TS, make_evidence_item, make_provenance


class TestEvidenceClaimLink:
    def test_construction(self) -> None:
        link = EvidenceClaimLink(
            claim_id="cl-1",
            relationship=EvidenceRelationship.SUPPORTS,
        )
        assert link.confidence == 1.0

    def test_empty_claim_id_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            EvidenceClaimLink(claim_id="", relationship=EvidenceRelationship.SUPPORTS)

    def test_confidence_out_of_range_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            EvidenceClaimLink(
                claim_id="cl-1",
                relationship=EvidenceRelationship.SUPPORTS,
                confidence=1.5,
            )

    def test_confidence_zero_accepted(self) -> None:
        link = EvidenceClaimLink(
            claim_id="cl-1",
            relationship=EvidenceRelationship.SUPPORTS,
            confidence=0.0,
        )
        assert link.confidence == 0.0

    def test_is_frozen(self) -> None:
        link = EvidenceClaimLink(claim_id="cl-1", relationship=EvidenceRelationship.NEUTRAL)
        with pytest.raises((AttributeError, TypeError)):
            link.claim_id = "other"  # type: ignore[misc]


class TestEvidenceItem:
    def test_minimal_construction(self) -> None:
        ev = make_evidence_item()
        assert ev.evidence_id == "ev-1"
        assert ev.content == "Test evidence content."

    def test_empty_evidence_id_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_evidence_item(evidence_id="")

    def test_empty_content_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_evidence_item(content="")

    def test_whitespace_content_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_evidence_item(content="   ")

    def test_empty_source_id_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_evidence_item(
                source_id="",
                provenance=make_provenance(source_id=""),
            )

    def test_naive_observed_at_rejected(self) -> None:
        with pytest.raises(ContractValidationError, match="timezone"):
            make_evidence_item(observed_at=datetime(2024, 1, 1))

    def test_aware_observed_at_accepted(self) -> None:
        ev = make_evidence_item(observed_at=FIXED_TS)
        assert ev.observed_at == FIXED_TS

    def test_metadata_wrapped(self) -> None:
        ev = make_evidence_item(metadata={"key": "value"})
        assert isinstance(ev.metadata, types.MappingProxyType)

    def test_is_frozen(self) -> None:
        ev = make_evidence_item()
        with pytest.raises((AttributeError, TypeError)):
            ev.content = "changed"  # type: ignore[misc]

    def test_multiple_claim_links(self) -> None:
        links = (
            EvidenceClaimLink("cl-1", EvidenceRelationship.SUPPORTS),
            EvidenceClaimLink("cl-2", EvidenceRelationship.WEAKENS),
        )
        ev = make_evidence_item(claim_links=links)
        assert len(ev.claim_links) == 2
        assert ev.claim_links[0].relationship == EvidenceRelationship.SUPPORTS
        assert ev.claim_links[1].relationship == EvidenceRelationship.WEAKENS

    def test_claim_links_are_tuple(self) -> None:
        ev = make_evidence_item()
        assert isinstance(ev.claim_links, tuple)


class TestEvidenceRelationship:
    def test_all_values_are_strings(self) -> None:
        for member in EvidenceRelationship:
            assert isinstance(member.value, str)

    def test_expected_members_exist(self) -> None:
        assert EvidenceRelationship.SUPPORTS
        assert EvidenceRelationship.WEAKENS
        assert EvidenceRelationship.CONTRADICTS
        assert EvidenceRelationship.NEUTRAL
