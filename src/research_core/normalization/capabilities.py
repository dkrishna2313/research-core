"""
Capability reporting for knowledge and web adapters.

Neither function performs network calls or opens a knowledge store.
They only check import availability for optional dependencies.
"""

from __future__ import annotations

import sys

from research_core.normalization.contracts import (
    AdapterCapability,
    CapabilityReport,
    CapabilityStatus,
)


def capability_report_for_knowledge(adapter: object) -> CapabilityReport:
    """Build a capability report for a KnowledgeAdapter instance.

    Checks whether the dc-power-agent package (module name: knowledge) is importable.
    Does not open the knowledge store or make any network calls.
    """
    knowledge_status = _check_import("knowledge")

    capabilities = (
        AdapterCapability(
            name="knowledge_store",
            status=knowledge_status,
            description="Access to local knowledge store via dc-power-agent",
        ),
    )

    overall = "available" if knowledge_status == CapabilityStatus.AVAILABLE else "unavailable"

    return CapabilityReport(
        adapter_name="KnowledgeAdapter",
        capabilities=capabilities,
        metadata={"overall": overall},
    )


def capability_report_for_web(adapter: object) -> CapabilityReport:
    """Build a capability report for a WebSearchAdapter instance.

    Checks whether ddgs, requests, trafilatura, pypdf, and python-docx (module: docx)
    are importable. Does not perform any network calls.
    """
    search_status = _check_import("ddgs")
    fetcher_status = _check_import("requests")
    html_status = _check_import("trafilatura")
    pdf_status = _check_import("pypdf")
    docx_status = _check_import("docx")

    capabilities = (
        AdapterCapability(
            name="search_provider",
            status=search_status,
            description="DuckDuckGo search via ddgs",
        ),
        AdapterCapability(
            name="page_fetcher",
            status=fetcher_status,
            description="HTTP page fetching via requests",
        ),
        AdapterCapability(
            name="html_extractor",
            status=html_status,
            description="HTML text extraction via trafilatura",
        ),
        AdapterCapability(
            name="pdf_extractor",
            status=pdf_status,
            description="PDF text extraction via pypdf",
        ),
        AdapterCapability(
            name="docx_extractor",
            status=docx_status,
            description="DOCX text extraction via python-docx",
        ),
    )

    core_missing = (
        search_status == CapabilityStatus.UNAVAILABLE
        or fetcher_status == CapabilityStatus.UNAVAILABLE
    )
    all_extractors_missing = (
        html_status == CapabilityStatus.UNAVAILABLE
        and pdf_status == CapabilityStatus.UNAVAILABLE
        and docx_status == CapabilityStatus.UNAVAILABLE
    )

    if core_missing:
        overall = "unavailable"
    elif all_extractors_missing:
        overall = "degraded"
    else:
        overall = "available"

    return CapabilityReport(
        adapter_name="WebSearchAdapter",
        capabilities=capabilities,
        metadata={"overall": overall},
    )


def _check_import(module_name: str) -> CapabilityStatus:
    """Check whether a module is importable without side effects."""
    if module_name in sys.modules:
        return CapabilityStatus.AVAILABLE
    try:
        __import__(module_name)
        return CapabilityStatus.AVAILABLE
    except ImportError:
        return CapabilityStatus.UNAVAILABLE
