"""
Tests for DeterministicSynthesizer.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from research_core.contracts.claims import Claim
from research_core.contracts.common import SourceType
from research_core.contracts.contradictions import Contradiction, ContradictionType
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.gaps import GapSeverity, GapType, ResearchGap
from research_core.contracts.request import ResearchRequest
from research_core.contracts.result import SynthesisResult
from research_core.contracts.sources import EvidenceQuality, Provenance
from research_core.synthesis.deterministic import DeterministicSynthesizer

FIXED_TS = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)


def _prov(source_id: str) -> Provenance:
    return Provenance(
        source_id=source_id,
        source_type=SourceType.KNOWLEDGE,
        retrieved_at=FIXED_TS,
    )


def _ev(evidence_id: str, source_id: str, content: str = "Test content.") -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        content=content,
        source_id=source_id,
        provenance=_prov(source_id),
        quality=EvidenceQuality(relevance=0.8),
    )


def _claim(
    claim_id: str,
    statement: str,
    evidence_ids: tuple[str, ...] = (),
) -> Claim:
    return Claim(
        claim_id=claim_id,
        statement=statement,
        supporting_evidence_ids=evidence_ids,
    )


def _request() -> ResearchRequest:
    return ResearchRequest(question="What is the impact?")


def _gap(gap_id: str = "gap-1", severity: GapSeverity = GapSeverity.MEDIUM) -> ResearchGap:
    return ResearchGap(
        gap_id=gap_id,
        gap_type=GapType.INSUFFICIENT_COVERAGE,
        description="Insufficient coverage.",
        severity=severity,
    )


@pytest.mark.synthesis
class TestDeterministicSynthesizerProtocol:
    def test_satisfies_synthesizer_protocol(self) -> None:
        from research_core.protocols.synthesis import Synthesizer

        synth = DeterministicSynthesizer()
        assert isinstance(synth, Synthesizer)

    def test_returns_synthesis_result(self) -> None:
        synth = DeterministicSynthesizer()
        ev = _ev("ev-1", "src-1")
        cl = _claim("cl-1", "Revenue increased.", ("ev-1",))
        result = synth.synthesize(
            _request(), (ev,), (cl,), (), (), ()
        )
        assert isinstance(result, SynthesisResult)

    def test_narrative_non_empty(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_request(), (), (), (), (), ())
        assert result.narrative.strip()

    def test_synthesis_model_set(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_request(), (), (), (), (), ())
        assert result.synthesis_model is not None
        assert "DeterministicSynthesizer" in result.synthesis_model

    def test_no_timestamp_in_output(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_request(), (), (), (), (), ())
        assert result.synthesized_at is None

    def test_no_confidence_score(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_request(), (), (), (), (), ())
        assert result.confidence is None


@pytest.mark.synthesis
class TestDeterministicSynthesizerClaims:
    def test_claim_wording_preserved(self) -> None:
        synth = DeterministicSynthesizer()
        statement = "Revenue increased by $10 million due to market expansion."
        ev = _ev("ev-1", "src-1")
        cl = _claim("cl-1", statement, ("ev-1",))
        result = synth.synthesize(_request(), (ev,), (cl,), (), (), ())
        assert statement in result.key_findings

    def test_negation_preserved(self) -> None:
        synth = DeterministicSynthesizer()
        statement = "The treatment did not reduce mortality rates."
        ev = _ev("ev-1", "src-1")
        cl = _claim("cl-1", statement, ("ev-1",))
        result = synth.synthesize(_request(), (ev,), (cl,), (), (), ())
        assert statement in result.key_findings

    def test_modality_preserved(self) -> None:
        synth = DeterministicSynthesizer()
        statement = "Demand may increase significantly over the next decade."
        ev = _ev("ev-1", "src-1")
        cl = _claim("cl-1", statement, ("ev-1",))
        result = synth.synthesize(_request(), (ev,), (cl,), (), (), ())
        assert statement in result.key_findings

    def test_quantities_preserved(self) -> None:
        synth = DeterministicSynthesizer()
        statement = "Revenue was $100 million."
        ev = _ev("ev-1", "src-1")
        cl = _claim("cl-1", statement, ("ev-1",))
        result = synth.synthesize(_request(), (ev,), (cl,), (), (), ())
        assert statement in result.key_findings

    def test_two_distinct_claims_both_in_findings(self) -> None:
        synth = DeterministicSynthesizer()
        ev1 = _ev("ev-1", "src-1")
        ev2 = _ev("ev-2", "src-2")
        cl1 = _claim("cl-1", "Revenue was $10 million.", ("ev-1",))
        cl2 = _claim("cl-2", "Revenue was $100 million.", ("ev-2",))
        result = synth.synthesize(_request(), (ev1, ev2), (cl1, cl2), (), (), ())
        assert cl1.statement in result.key_findings
        assert cl2.statement in result.key_findings

    def test_empty_claims_yields_empty_findings(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_request(), (), (), (), (), ())
        assert result.key_findings == ()


@pytest.mark.synthesis
class TestDeterministicSynthesizerGaps:
    def test_gap_info_in_narrative(self) -> None:
        synth = DeterministicSynthesizer()
        ev = _ev("ev-1", "src-1")
        cl = _claim("cl-1", "Climate change impacts biodiversity.", ("ev-1",))
        gap = _gap("gap-1", GapSeverity.CRITICAL)
        result = synth.synthesize(_request(), (ev,), (cl,), (), (gap,), ())
        # Narrative should mention gap count
        assert "gap" in result.narrative.lower()

    def test_no_unsupported_content(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_request(), (), (), (), (), ())
        # Must not use phrases that imply truth or verification
        forbidden = ["the evidence proves", "the research confirms", "the best strategy"]
        for phrase in forbidden:
            assert phrase.lower() not in result.narrative.lower()


@pytest.mark.synthesis
class TestDeterministicSynthesizerDeterminism:
    def test_identical_inputs_identical_output(self) -> None:
        synth = DeterministicSynthesizer()
        ev = _ev("ev-1", "src-1", "Climate change impacts biodiversity.")
        cl = _claim("cl-1", "Climate impact is significant.", ("ev-1",))
        gap = _gap()
        request = _request()

        r1 = synth.synthesize(request, (ev,), (cl,), (), (gap,), ())
        r2 = synth.synthesize(request, (ev,), (cl,), (), (gap,), ())

        assert r1.narrative == r2.narrative
        assert r1.key_findings == r2.key_findings
        assert r1.synthesis_model == r2.synthesis_model

    def test_repeated_calls_same_instance(self) -> None:
        synth = DeterministicSynthesizer()
        ev = _ev("ev-1", "src-1")
        cl = _claim("cl-1", "Test claim.", ("ev-1",))

        r1 = synth.synthesize(_request(), (ev,), (cl,), (), (), ())
        r2 = synth.synthesize(_request(), (ev,), (cl,), (), (), ())

        assert r1.narrative == r2.narrative
        assert r1.key_findings == r2.key_findings

    def test_different_instances_same_output(self) -> None:
        ev = _ev("ev-1", "src-1")
        cl = _claim("cl-1", "Test claim.", ("ev-1",))

        r1 = DeterministicSynthesizer().synthesize(_request(), (ev,), (cl,), (), (), ())
        r2 = DeterministicSynthesizer().synthesize(_request(), (ev,), (cl,), (), (), ())

        assert r1.narrative == r2.narrative


@pytest.mark.synthesis
class TestDeterministicSynthesizerLimitations:
    def test_limitations_text_in_narrative(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_request(), (), (), (), (), ())
        assert "does not imply" in result.narrative

    def test_no_contradiction_resolution(self) -> None:
        synth = DeterministicSynthesizer()
        ev1 = _ev("ev-1", "src-1")
        ev2 = _ev("ev-2", "src-2")
        cl1 = _claim("cl-1", "Revenue was $10 million.", ("ev-1",))
        cl2 = _claim("cl-2", "Revenue was $100 million.", ("ev-2",))
        con = Contradiction(
            contradiction_id="con-1",
            contradiction_type=ContradictionType.NUMERIC,
            description="Revenue estimates conflict.",
            claim_ids=("cl-1", "cl-2"),
        )
        result = synth.synthesize(_request(), (ev1, ev2), (cl1, cl2), (con,), (), ())
        # Both claims still in findings (no resolution)
        assert cl1.statement in result.key_findings
        assert cl2.statement in result.key_findings
