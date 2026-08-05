"""
Tests for GapAnalyzer protocol compliance.
"""

from __future__ import annotations

import pytest

from research_core.analysis.analyzer import DeterministicGapAnalyzer, GapAnalyzer
from research_core.analysis.config import GapAnalysisConfig
from research_core.analysis.contracts import GapAnalysisResult


@pytest.mark.diagnostics
class TestGapAnalyzerProtocol:
    def test_deterministic_analyzer_implements_protocol(self) -> None:
        analyzer = DeterministicGapAnalyzer()
        assert isinstance(analyzer, GapAnalyzer)

    def test_protocol_method_returns_correct_type(self) -> None:
        analyzer = DeterministicGapAnalyzer()
        cfg = GapAnalysisConfig()
        result = analyzer.analyze([], [], [], None, cfg)
        assert isinstance(result, GapAnalysisResult)

    def test_custom_class_not_compliant_without_analyze(self) -> None:
        class NotAnalyzer:
            def something_else(self) -> None:
                pass

        assert not isinstance(NotAnalyzer(), GapAnalyzer)

    def test_custom_class_compliant_with_analyze(self) -> None:
        from collections.abc import Sequence

        from research_core.claims.contracts import ExtractedClaim
        from research_core.contracts.sources import Source
        from research_core.normalization.contracts import (
            EvidenceRankingResult,
            RankedEvidence,
        )

        class MinimalAnalyzer:
            def analyze(
                self,
                sources: Sequence[Source],
                ranked_evidence: Sequence[RankedEvidence],
                claims: Sequence[ExtractedClaim],
                ranking_result: EvidenceRankingResult | None,
                config: GapAnalysisConfig,
            ) -> GapAnalysisResult:  # type: ignore[empty-body]
                ...

        assert isinstance(MinimalAnalyzer(), GapAnalyzer)
