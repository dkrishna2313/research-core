"""Tests for claim contract serialization."""

from __future__ import annotations

import json
import types

import pytest

from research_core.claims import (
    DeterministicClaimExtractor,
)
from research_core.contracts.serialization import serialize
from tests.claims.conftest import make_ranked_evidence

pytestmark = pytest.mark.claims

extractor = DeterministicClaimExtractor()


def test_extracted_claim_serializable() -> None:
    ranked = make_ranked_evidence(content="Revenue increased by 12%.")
    result = extractor.extract([ranked])
    assert len(result.claims) >= 1
    serialized = serialize(result.claims[0])
    json.dumps(serialized)  # must not raise


def test_result_fully_serializable() -> None:
    evidence = [
        make_ranked_evidence(
            content=(
                "Revenue increased by 12%. The policy may reduce emissions."
                " Costs did not fall."
            ),
            rank=1,
        )
    ]
    result = extractor.extract(evidence)
    serialized = serialize(result)
    # Must be JSON-dumpable
    dumped = json.dumps(serialized)
    assert isinstance(dumped, str)


def test_enums_become_strings_in_serialization() -> None:
    ranked = make_ranked_evidence(content="Revenue increased by 12%.")
    result = extractor.extract([ranked])
    claim = result.claims[0]
    serialized = serialize(claim)
    assert isinstance(serialized["claim_type"], str)
    assert isinstance(serialized["modality"], str)
    assert isinstance(serialized["polarity"], str)


def test_mapping_proxy_becomes_dict_in_serialization() -> None:
    ranked = make_ranked_evidence(content="Revenue increased by 12%.")
    result = extractor.extract([ranked])
    serialized = serialize(result.diagnostics)
    assert isinstance(serialized["claims_by_type"], dict)
    assert isinstance(serialized["claims_by_modality"], dict)
    assert not isinstance(serialized["claims_by_type"], types.MappingProxyType)


def test_tuple_becomes_list_in_serialization() -> None:
    ranked = make_ranked_evidence(content="Revenue increased by 12%.")
    result = extractor.extract([ranked])
    serialized = serialize(result)
    assert isinstance(serialized["claims"], list)


def test_attribution_serializes_correctly() -> None:
    ranked = make_ranked_evidence(
        content="According to the agency, costs increased by $2 million."
    )
    result = extractor.extract([ranked])
    claims_with_attr = [c for c in result.claims if c.attribution is not None]
    for claim in claims_with_attr:
        s = serialize(claim)
        assert isinstance(s["attribution"], dict)
        assert "source_text" in s["attribution"]
        assert "reporting_verb" in s["attribution"]


def test_none_attribution_serializes_as_none() -> None:
    ranked = make_ranked_evidence(content="Revenue increased by 12%.")
    result = extractor.extract([ranked])
    for claim in result.claims:
        if claim.attribution is None:
            s = serialize(claim)
            assert s["attribution"] is None


def test_quantitative_expressions_serialize() -> None:
    ranked = make_ranked_evidence(content="Revenue increased by 12%.")
    result = extractor.extract([ranked])
    for claim in result.claims:
        s = serialize(claim)
        assert isinstance(s["quantitative_expressions"], list)


def test_empty_result_serializable() -> None:
    result = extractor.extract([])
    serialized = serialize(result)
    json.dumps(serialized)
