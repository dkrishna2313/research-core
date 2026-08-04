"""Tests for ResearchGap and OpenQuestion contracts."""

from __future__ import annotations

import pytest

from research_core.contracts.gaps import (
    GapSeverity,
    GapStatus,
    GapType,
    OpenQuestion,
    QuestionPriority,
)
from research_core.exceptions import ContractValidationError
from tests.conftest import make_gap, make_open_question


class TestResearchGap:
    def test_minimal_construction(self) -> None:
        gap = make_gap()
        assert gap.gap_id == "gap-1"
        assert gap.gap_type == GapType.NO_EVIDENCE

    def test_empty_gap_id_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_gap(gap_id="")

    def test_empty_description_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_gap(description="")

    def test_defaults(self) -> None:
        gap = make_gap()
        assert gap.severity == GapSeverity.MEDIUM
        assert gap.status == GapStatus.OPEN
        assert gap.recommended_action == ""
        assert gap.related_claim_ids == ()
        assert gap.related_evidence_ids == ()

    def test_gap_type_values_are_strings(self) -> None:
        for member in GapType:
            assert isinstance(member.value, str)

    def test_all_gap_types_exist(self) -> None:
        expected = {
            "NO_EVIDENCE", "INSUFFICIENT_COVERAGE", "WEAK_AUTHORITY",
            "UNCORROBORATED_CLAIM", "STALE_EVIDENCE", "UNRESOLVED_CONTRADICTION",
            "LOW_EXTRACTION_CONFIDENCE", "MISSING_DIMENSION",
            "METHODOLOGICAL_UNCERTAINTY", "INCONSISTENT_DEFINITION", "OTHER",
        }
        assert {m.name for m in GapType} == expected


class TestOpenQuestion:
    def test_minimal_construction(self) -> None:
        oq = make_open_question()
        assert oq.question == "What is the scope?"

    def test_empty_question_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            OpenQuestion(question="")

    def test_whitespace_question_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            OpenQuestion(question="   ")

    def test_defaults(self) -> None:
        oq = make_open_question()
        assert oq.priority == QuestionPriority.MEDIUM
        assert oq.reason == ""
        assert oq.related_claim_ids == ()
        assert oq.related_gap_ids == ()

    def test_priorities_exist(self) -> None:
        assert QuestionPriority.LOW
        assert QuestionPriority.MEDIUM
        assert QuestionPriority.HIGH
