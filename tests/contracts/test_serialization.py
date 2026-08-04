"""Tests for the serialize() utility."""

from __future__ import annotations

import json
import types
from datetime import UTC, date, datetime
from enum import StrEnum

import pytest

from research_core.contracts.serialization import serialize


class SampleEnum(StrEnum):
    FOO = "foo"
    BAR = "bar"


class TestSerializePrimitives:
    def test_none(self) -> None:
        assert serialize(None) is None

    def test_bool(self) -> None:
        assert serialize(True) is True
        assert serialize(False) is False

    def test_int(self) -> None:
        assert serialize(42) == 42

    def test_float(self) -> None:
        assert serialize(3.14) == pytest.approx(3.14)

    def test_str(self) -> None:
        assert serialize("hello") == "hello"


class TestSerializeEnum:
    def test_enum_to_value(self) -> None:
        assert serialize(SampleEnum.FOO) == "foo"
        assert serialize(SampleEnum.BAR) == "bar"

    def test_str_enum_returns_plain_str(self) -> None:
        """StrEnum values must serialize to plain str, not the enum subclass."""
        result = serialize(SampleEnum.FOO)
        assert type(result) is str, (
            f"Expected plain str, got {type(result)}; "
            "StrEnum extends str so isinstance checks pass — "
            "serialize must convert to .value explicitly"
        )

    def test_research_status_serializes_to_plain_str(self) -> None:
        from research_core.contracts.result import ResearchStatus
        result = serialize(ResearchStatus.COMPLETE)
        assert type(result) is str
        assert result == "complete"


class TestSerializeDatetime:
    def test_aware_datetime(self) -> None:
        dt = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        result = serialize(dt)
        assert isinstance(result, str)
        assert "2024-06-15" in result

    def test_date_only(self) -> None:
        d = date(2024, 6, 15)
        result = serialize(d)
        assert result == "2024-06-15"


class TestSerializeCollections:
    def test_tuple_becomes_list(self) -> None:
        result = serialize((1, 2, 3))
        assert result == [1, 2, 3]
        assert isinstance(result, list)

    def test_list_stays_list(self) -> None:
        result = serialize([1, 2, 3])
        assert result == [1, 2, 3]

    def test_dict_serialized(self) -> None:
        result = serialize({"a": 1, "b": "two"})
        assert result == {"a": 1, "b": "two"}

    def test_mapping_proxy_serialized(self) -> None:
        proxy = types.MappingProxyType({"x": 10})
        result = serialize(proxy)
        assert result == {"x": 10}
        assert isinstance(result, dict)

    def test_nested_tuple_of_enums(self) -> None:
        result = serialize((SampleEnum.FOO, SampleEnum.BAR))
        assert result == ["foo", "bar"]


class TestSerializeDataclass:
    def test_evidence_quality_serialized(self) -> None:
        from research_core.contracts.sources import EvidenceQuality

        q = EvidenceQuality(relevance=0.8, authority=0.6)
        result = serialize(q)
        assert isinstance(result, dict)
        assert result["relevance"] == pytest.approx(0.8)
        assert result["authority"] == pytest.approx(0.6)

    def test_enum_field_serialized_to_value(self) -> None:
        from research_core.contracts.claims import Claim

        cl = Claim(claim_id="cl-1", statement="Test")
        result = serialize(cl)
        assert result["claim_type"] == "factual"

    def test_source_type_serialized(self) -> None:
        from tests.conftest import make_source

        s = make_source()
        result = serialize(s)
        assert result["source_type"] == "knowledge"

    def test_metadata_proxy_serialized_as_dict(self) -> None:
        from tests.conftest import make_source

        s = make_source(metadata={"key": "value"})
        result = serialize(s)
        assert result["metadata"] == {"key": "value"}
        assert isinstance(result["metadata"], dict)

    def test_result_is_json_serializable(self) -> None:
        from tests.conftest import make_full_result

        result = make_full_result()
        serialized = serialize(result)
        json_str = json.dumps(serialized)
        assert len(json_str) > 0
