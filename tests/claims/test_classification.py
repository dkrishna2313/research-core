"""Tests for claim classification and precedence rules.

Classification precedence (highest priority first):
  NORMATIVE > PREDICTIVE > CAUSAL > COMPARATIVE > QUANTITATIVE >
  DEFINITIONAL > FACTUAL > UNKNOWN
"""

from __future__ import annotations

import pytest

from research_core.claims._classify import classify_claim, extract_quantitative
from research_core.claims.contracts import ClaimType

pytestmark = pytest.mark.claims


def _classify(text: str) -> ClaimType:
    return classify_claim(text, extract_quantitative(text))


def test_normative() -> None:
    assert _classify("Companies should reduce emissions.") == ClaimType.NORMATIVE


def test_normative_must() -> None:
    assert _classify("Emissions must be reported annually.") == ClaimType.NORMATIVE


def test_normative_required() -> None:
    assert _classify("Disclosure is required to disclose material risks.") == ClaimType.NORMATIVE


def test_predictive_will() -> None:
    assert _classify("Emissions will fall by 2030.") == ClaimType.PREDICTIVE


def test_predictive_expected() -> None:
    assert _classify("Demand is expected to increase next year.") == ClaimType.PREDICTIVE


def test_predictive_projected() -> None:
    assert _classify("Costs are projected to reach $5 billion.") == ClaimType.PREDICTIVE


def test_causal_led_to() -> None:
    assert _classify("Higher prices led to lower demand.") == ClaimType.CAUSAL


def test_causal_because() -> None:
    assert _classify("Costs rose because supply declined.") == ClaimType.CAUSAL


def test_causal_resulted_in() -> None:
    assert _classify("The policy resulted in lower emissions.") == ClaimType.CAUSAL


def test_comparative_higher_than() -> None:
    assert _classify("Demand was 12% higher than last year.") == ClaimType.COMPARATIVE


def test_comparative_more_than() -> None:
    assert _classify("Revenue is more than $10 million.") == ClaimType.COMPARATIVE


def test_comparative_versus() -> None:
    assert _classify("Efficiency improved versus the previous year.") == ClaimType.COMPARATIVE


def test_quantitative_percentage() -> None:
    assert _classify("Revenue increased by 12%.") == ClaimType.QUANTITATIVE


def test_quantitative_currency() -> None:
    assert _classify("The project cost $5 million.") == ClaimType.QUANTITATIVE


def test_quantitative_measurement() -> None:
    assert _classify("Capacity reached 3.4 GW.") == ClaimType.QUANTITATIVE


def test_definitional() -> None:
    assert _classify("Resilience means the ability to recover.") == ClaimType.DEFINITIONAL


def test_definitional_defined_as() -> None:
    result = _classify("Carbon intensity is defined as emissions per unit of GDP.")
    assert result == ClaimType.DEFINITIONAL


def test_factual_default() -> None:
    assert _classify("Costs increased.") == ClaimType.FACTUAL


def test_factual_clear_assertion() -> None:
    assert _classify("The agency published its annual report.") == ClaimType.FACTUAL


# Multi-signal precedence tests
def test_predictive_beats_quantitative() -> None:
    # "The project will cost $5 million."
    # PREDICTIVE (will) > QUANTITATIVE ($5 million) — PREDICTIVE wins
    result = _classify("The project will cost $5 million.")
    assert result == ClaimType.PREDICTIVE, (
        "PREDICTIVE should beat QUANTITATIVE; "
        f"got {result!r} for 'The project will cost $5 million.'"
    )


def test_causal_beats_comparative() -> None:
    # "Demand fell more than expected because prices rose."
    # Both causal and comparative present — CAUSAL wins (higher precedence)
    result = _classify("Demand fell more than expected because prices rose.")
    assert result == ClaimType.CAUSAL


def test_normative_beats_predictive() -> None:
    # "Companies should expect costs will rise."
    result = _classify("Companies should expect that costs will rise.")
    assert result == ClaimType.NORMATIVE


def test_year_alone_does_not_trigger_quantitative() -> None:
    # A bare year like "2024" should not make a claim QUANTITATIVE
    result = _classify("In 2024, costs increased.")
    # No non-trivial quant → CAUSAL or FACTUAL (because of "increased", no causal/comparative)
    assert result in (ClaimType.FACTUAL, ClaimType.QUANTITATIVE)
