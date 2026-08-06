# Research Result

## Status

**Status:** complete
**Is Complete:** True
**Completed At:** 2024-03-01T12:00:00+00:00

## Research Question

What is the impact of climate change on biodiversity?

## Executive Summary

The research retrieved 2 evidence item(s) from 2 source(s), yielding 2 claim(s). 1 research gap(s) were identified. This synthesis does not imply verification, corroboration, or truth inference.

## Sources

- `src-know-01` — IPCC Sixth Assessment Report (knowledge) [IPCC]
- `src-web-01` — Climate Biodiversity Impact (web) (https://example.org/climate-biodiversity)

## Evidence

1. `ev-001` (source: `src-know-01`)
   relevance=0.950, authority=0.900
   > Global average temperatures have risen by 1.1°C since pre-industrial times.

2. `ev-002` (source: `src-web-01`)
   relevance=0.850, authority=0.700
   > Approximately 1 million species are currently at risk of extinction.

## Claims

1. `cl-001` (factual)
   Global temperatures have risen 1.1°C since pre-industrial times.
   Supporting evidence: `ev-001`

2. `cl-002` (factual)
   Approximately 1 million species face extinction risk.
   Supporting evidence: `ev-002`

## Quality Diagnostics

| Dimension | Score |
|-----------|-------|
| relevance | 0.900 |
| authority | 0.800 |
| recency | 0.800 |
| corroboration | Unavailable |
| independence | Unavailable |
| coverage | Unavailable |
| extraction_confidence | Unavailable |
| contradiction_severity | Unavailable |
| uncertainty | Unavailable |
| completeness | Unavailable |
| provenance_completeness | Unavailable |
| reproducibility | Unavailable |

## Research Gaps

1. [HIGH] `gap-001`
   Type: missing_dimension | Status: open
   Evidence does not cover projections beyond 2050.
   Recommended action: Retrieve sources covering post-2050 projections.
   Related claims: none
   Related evidence: none

## Synthesis

**Model:** DeterministicSynthesizer/1.0

The research retrieved 2 evidence item(s) from 2 source(s), yielding 2 claim(s). 1 research gap(s) were identified. This synthesis does not imply verification, corroboration, or truth inference.

**Key Findings:**

- Global temperatures have risen 1.1°C since pre-industrial times.
- Approximately 1 million species face extinction risk.

## Open Questions

1. [HIGH] What are the projected extinction rates after 2100?
   Reason: Current evidence does not cover long-term projections.

## Execution Trace

1. [init] COMPLETED — Research engine starting.
2. [profile_resolution] SKIPPED — No profiles specified; profile resolution skipped.
3. [retrieval] COMPLETED — Knowledge retrieval: 1 item(s) from 1 source(s).
4. [retrieval] COMPLETED — Web retrieval: 1 item(s) from 1 source(s).
5. [extraction] COMPLETED — Claim extraction: 2 claim(s) extracted.
6. [contradiction_detection] SKIPPED — Contradiction detection skipped (no detector configured).
7. [gap_analysis] COMPLETED — Gap analysis: 1 gap(s), 1 open question(s).
8. [synthesis] COMPLETED — Synthesis completed.
9. [finalization] COMPLETED — Research finalized. Status: complete. Sources: 2, evidence: 2, claims: 2, gaps: 1.

## Limitations

This result was produced by a deterministic research pipeline. Evidence-derived claims are not automatically verified, corroborated, or assigned authority. Quality scores reflect pipeline signals, not factual reliability. Research gaps indicate incomplete coverage; they do not indicate that the research question has no answer.
