"""Tests for ResearchResult, SynthesisResult, and ResearchStatus contracts."""

from __future__ import annotations

from datetime import datetime

import pytest

from research_core.contracts.result import ResearchResult, ResearchStatus
from research_core.exceptions import ContractValidationError
from tests.conftest import (
    make_claim,
    make_contradiction,
    make_evidence_item,
    make_full_result,
    make_gap,
    make_minimal_result,
    make_open_question,
    make_research_request,
    make_source,
    make_synthesis_result,
)


class TestResearchStatus:
    def test_only_complete_and_partial(self) -> None:
        members = {m.name for m in ResearchStatus}
        assert members == {"COMPLETE", "PARTIAL"}
        assert "FAILED" not in members

    def test_values_are_strings(self) -> None:
        for member in ResearchStatus:
            assert isinstance(member.value, str)


class TestSynthesisResult:
    def test_minimal_construction(self) -> None:
        sr = make_synthesis_result()
        assert "significant" in sr.narrative

    def test_empty_narrative_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_synthesis_result(narrative="")

    def test_naive_synthesized_at_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_synthesis_result(synthesized_at=datetime(2024, 1, 1))

    def test_confidence_out_of_range_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_synthesis_result(confidence=1.5)

    def test_confidence_none_accepted(self) -> None:
        sr = make_synthesis_result(confidence=None)
        assert sr.confidence is None


class TestResearchResultConstruction:
    def test_minimal_result_builds(self) -> None:
        result = make_minimal_result()
        assert result.is_complete

    def test_full_result_builds(self) -> None:
        result = make_full_result()
        assert result.status == ResearchStatus.COMPLETE

    def test_is_partial_property(self) -> None:
        result = make_minimal_result(status=ResearchStatus.PARTIAL)
        assert result.is_partial is True
        assert result.is_complete is False

    def test_naive_completed_at_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_minimal_result(completed_at=datetime(2024, 1, 1))


class TestResearchResultUniqueIds:
    def test_duplicate_source_ids_rejected(self) -> None:
        s1 = make_source(source_id="dup")
        s2 = make_source(source_id="dup")
        with pytest.raises(ContractValidationError, match="duplicate"):
            make_minimal_result(sources=(s1, s2))

    def test_duplicate_evidence_ids_rejected(self) -> None:
        s = make_source()
        ev1 = make_evidence_item(evidence_id="dup", source_id="src-1")
        ev2 = make_evidence_item(evidence_id="dup", source_id="src-1")
        with pytest.raises(ContractValidationError, match="duplicate"):
            make_minimal_result(sources=(s,), evidence=(ev1, ev2))

    def test_duplicate_claim_ids_rejected(self) -> None:
        s = make_source()
        cl1 = make_claim(claim_id="dup")
        cl2 = make_claim(claim_id="dup")
        with pytest.raises(ContractValidationError, match="duplicate"):
            make_minimal_result(sources=(s,), claims=(cl1, cl2))


class TestResearchResultCrossReferences:
    def test_evidence_with_unknown_source_rejected(self) -> None:
        s = make_source(source_id="src-1")
        ev = make_evidence_item(evidence_id="ev-1", source_id="src-UNKNOWN")
        with pytest.raises(ContractValidationError, match="source_id"):
            ResearchResult(
                request=make_research_request(),
                status=ResearchStatus.COMPLETE,
                sources=(s,),
                evidence=(ev,),
                claims=(),
                contradictions=(),
                gaps=(),
                open_questions=(),
            )

    def test_claim_with_unknown_evidence_rejected(self) -> None:
        s = make_source(source_id="src-1")
        cl = make_claim(claim_id="cl-1", supporting_evidence_ids=("ev-UNKNOWN",))
        with pytest.raises(ContractValidationError, match="evidence_id"):
            ResearchResult(
                request=make_research_request(),
                status=ResearchStatus.COMPLETE,
                sources=(s,),
                evidence=(),
                claims=(cl,),
                contradictions=(),
                gaps=(),
                open_questions=(),
            )

    def test_contradiction_with_unknown_claim_rejected(self) -> None:
        s = make_source(source_id="src-1")
        con = make_contradiction(claim_ids=("cl-UNKNOWN", "cl-ALSO-UNKNOWN"))
        with pytest.raises(ContractValidationError, match="claim_id"):
            ResearchResult(
                request=make_research_request(),
                status=ResearchStatus.COMPLETE,
                sources=(s,),
                evidence=(),
                claims=(),
                contradictions=(con,),
                gaps=(),
                open_questions=(),
            )

    def test_gap_with_unknown_claim_rejected(self) -> None:
        s = make_source()
        gap = make_gap(related_claim_ids=("cl-UNKNOWN",))
        with pytest.raises(ContractValidationError, match="claim_id"):
            ResearchResult(
                request=make_research_request(),
                status=ResearchStatus.COMPLETE,
                sources=(s,),
                evidence=(),
                claims=(),
                contradictions=(),
                gaps=(gap,),
                open_questions=(),
            )

    def test_open_question_with_unknown_gap_rejected(self) -> None:
        s = make_source()
        oq = make_open_question(related_gap_ids=("gap-UNKNOWN",))
        with pytest.raises(ContractValidationError, match="gap_id"):
            ResearchResult(
                request=make_research_request(),
                status=ResearchStatus.COMPLETE,
                sources=(s,),
                evidence=(),
                claims=(),
                contradictions=(),
                gaps=(),
                open_questions=(oq,),
            )

    def test_evidence_claim_link_to_unknown_claim_rejected(self) -> None:
        from research_core.contracts.evidence import EvidenceClaimLink, EvidenceRelationship
        s = make_source(source_id="src-1")
        ev = make_evidence_item(
            source_id="src-1",
            claim_links=(
                EvidenceClaimLink("cl-UNKNOWN", EvidenceRelationship.SUPPORTS),
            ),
        )
        with pytest.raises(ContractValidationError, match="claim_id"):
            ResearchResult(
                request=make_research_request(),
                status=ResearchStatus.COMPLETE,
                sources=(s,),
                evidence=(ev,),
                claims=(),
                contradictions=(),
                gaps=(),
                open_questions=(),
            )

    def test_fully_linked_result_is_valid(self) -> None:
        result = make_full_result()
        assert result is not None
