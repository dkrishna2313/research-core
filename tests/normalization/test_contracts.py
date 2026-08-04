"""Tests for normalization contracts."""

from __future__ import annotations

import types

import pytest

pytestmark = pytest.mark.normalization

from research_core.normalization.contracts import (  # noqa: E402
    AdapterCapability,
    CapabilityReport,
    CapabilityStatus,
    ComponentStatus,
    RankedEvidence,
    RankingDiagnostics,
)
from research_core.normalization.normalize import normalize_evidence  # noqa: E402
from tests.normalization.conftest import (  # noqa: E402
    make_source,
    make_web_evidence,
)


class TestCapabilityStatus:
    def test_available_value(self) -> None:
        assert CapabilityStatus.AVAILABLE == "available"

    def test_unavailable_value(self) -> None:
        assert CapabilityStatus.UNAVAILABLE == "unavailable"

    def test_degraded_value(self) -> None:
        assert CapabilityStatus.DEGRADED == "degraded"

    def test_unknown_value(self) -> None:
        assert CapabilityStatus.UNKNOWN == "unknown"


class TestAdapterCapability:
    def test_metadata_coerced_to_proxy(self) -> None:
        cap = AdapterCapability(
            name="search",
            status=CapabilityStatus.AVAILABLE,
            metadata={"key": "value"},
        )
        assert isinstance(cap.metadata, types.MappingProxyType)

    def test_empty_metadata_default(self) -> None:
        cap = AdapterCapability(name="search", status=CapabilityStatus.AVAILABLE)
        assert isinstance(cap.metadata, types.MappingProxyType)
        assert len(cap.metadata) == 0


class TestCapabilityReport:
    def test_metadata_coerced_to_proxy(self) -> None:
        report = CapabilityReport(
            adapter_name="MyAdapter",
            capabilities=(),
            metadata={"overall": "available"},
        )
        assert isinstance(report.metadata, types.MappingProxyType)

    def test_capabilities_is_tuple(self) -> None:
        report = CapabilityReport(adapter_name="X", capabilities=())
        assert isinstance(report.capabilities, tuple)


class TestNormalizedEvidence:
    def test_metadata_coerced_to_proxy(self) -> None:
        src = make_source()
        ev = make_web_evidence(source_id=src.source_id)
        result = normalize_evidence(sources=(src,), evidence=(ev,))
        ne = result[0]
        assert isinstance(ne.metadata, types.MappingProxyType)

    def test_is_frozen(self) -> None:
        src = make_source()
        ev = make_web_evidence(source_id=src.source_id)
        result = normalize_evidence(sources=(src,), evidence=(ev,))
        ne = result[0]
        with pytest.raises((TypeError, AttributeError)):
            ne.provider = "changed"  # type: ignore[misc]


class TestRankedEvidence:
    def test_metadata_coerced_to_proxy(self) -> None:
        src = make_source()
        ev = make_web_evidence(source_id=src.source_id)
        ne = normalize_evidence(sources=(src,), evidence=(ev,))[0]
        ranked = RankedEvidence(
            normalized_evidence=ne,
            rank=1,
            score=0.5,
            components=(),
            metadata={"key": "val"},
        )
        assert isinstance(ranked.metadata, types.MappingProxyType)


class TestRankingDiagnostics:
    def test_metadata_coerced_to_proxy(self) -> None:
        diag = RankingDiagnostics(
            total_input=5,
            total_ranked=4,
            total_excluded=1,
            total_duplicates=0,
            config_fingerprint="abc123",
            metadata={"key": "val"},
        )
        assert isinstance(diag.metadata, types.MappingProxyType)


class TestComponentStatus:
    def test_all_values_present(self) -> None:
        values = {s.value for s in ComponentStatus}
        assert "available" in values
        assert "missing" in values
        assert "not_applicable" in values
        assert "penalty" in values
        assert "bonus" in values
