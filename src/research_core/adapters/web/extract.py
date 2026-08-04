"""
Content extraction for the web search adapter.

Extractor pipeline (in priority order):
1. PyPDFExtractor   — PDF via pypdf (optional: pypdf)
2. DocxExtractor    — DOCX via python-docx (optional: python-docx)
3. TrafilaturaExtractor — HTML/text via trafilatura (optional: trafilatura)
4. PlainTextExtractor   — plain text (no external dep)

Each extractor imports its dependency lazily at extract() time.
Missing dependencies raise ProviderExecutionError with an install hint.

Unsupported content types raise ProviderExecutionError("unsupported content type").
"""

from __future__ import annotations

import io
import re
from typing import Protocol, runtime_checkable

from research_core.adapters.web.models import ExtractionResult, FetchedResource
from research_core.exceptions import ProviderExecutionError


@runtime_checkable
class ContentExtractor(Protocol):
    """Internal protocol for a content extractor."""

    def can_extract(self, content_type: str, url: str) -> bool:
        """Return True if this extractor can handle the given content type / URL."""
        ...

    def extract(self, resource: FetchedResource) -> ExtractionResult:
        """Extract text from resource. Raises ProviderExecutionError on failure."""
        ...


class PyPDFExtractor:
    """PDF extraction via pypdf. Handles application/pdf and .pdf URLs."""

    def can_extract(self, content_type: str, url: str) -> bool:
        ct = content_type.lower()
        return "application/pdf" in ct or url.lower().split("?")[0].endswith(".pdf")

    def extract(self, resource: FetchedResource) -> ExtractionResult:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ProviderExecutionError(
                "pypdf is not installed; PDF extraction unavailable. "
                "Install with: pip install pypdf"
            ) from exc

        try:
            reader = PdfReader(io.BytesIO(resource.content))
        except Exception as exc:
            raise ProviderExecutionError(
                f"PDF parse failed for {resource.final_url!r}: {exc}"
            ) from exc

        title: str | None = None
        if reader.metadata and reader.metadata.title:
            title = str(reader.metadata.title).strip() or None

        pages: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text)

        text = "\n\n".join(pages)
        if not text.strip():
            raise ProviderExecutionError(
                f"PDF returned empty text for {resource.final_url!r} "
                f"(may be scanned/image-only)"
            )

        return ExtractionResult(
            text=text,
            title=title,
            extraction_method="pypdf",
            page_count=len(reader.pages),
            truncated=resource.truncated,
        )


class DocxExtractor:
    """DOCX extraction via python-docx."""

    def can_extract(self, content_type: str, url: str) -> bool:
        ct = content_type.lower()
        url_lower = url.lower().split("?")[0]
        return (
            "application/vnd.openxmlformats-officedocument.wordprocessingml" in ct
            or "application/msword" in ct
            or url_lower.endswith(".docx")
        )

    def extract(self, resource: FetchedResource) -> ExtractionResult:
        try:
            import docx
        except ImportError as exc:
            raise ProviderExecutionError(
                "python-docx is not installed; DOCX extraction unavailable. "
                "Install with: pip install python-docx"
            ) from exc

        try:
            doc = docx.Document(io.BytesIO(resource.content))
        except Exception as exc:
            raise ProviderExecutionError(
                f"DOCX parse failed for {resource.final_url!r}: {exc}"
            ) from exc

        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n\n".join(paragraphs)
        if not text.strip():
            raise ProviderExecutionError(
                f"DOCX returned empty text for {resource.final_url!r}"
            )

        title: str | None = None
        props = doc.core_properties
        if props and props.title:
            title = props.title.strip() or None

        return ExtractionResult(
            text=text,
            title=title,
            extraction_method="docx",
            truncated=resource.truncated,
        )


class TrafilaturaExtractor:
    """HTML extraction via trafilatura. Falls back to <title> regex for title."""

    def can_extract(self, content_type: str, url: str) -> bool:
        ct = content_type.lower()
        return "html" in ct or "xhtml" in ct or "xml" in ct or "text/" in ct

    def extract(self, resource: FetchedResource) -> ExtractionResult:
        try:
            import trafilatura
        except ImportError as exc:
            raise ProviderExecutionError(
                "trafilatura is not installed; HTML extraction unavailable. "
                "Install with: pip install trafilatura"
            ) from exc

        encoding = resource.encoding or "utf-8"
        try:
            html_str = resource.content.decode(encoding, errors="replace")
        except Exception:
            html_str = resource.content.decode("utf-8", errors="replace")

        try:
            text = trafilatura.extract(html_str) or ""
        except Exception as exc:
            raise ProviderExecutionError(
                f"trafilatura extraction failed for {resource.final_url!r}: {exc}"
            ) from exc

        if not text.strip():
            raise ProviderExecutionError(
                f"trafilatura returned empty text for {resource.final_url!r} "
                f"(page may be JS-rendered, paywalled, or navigation-only)"
            )

        title = _extract_html_title(html_str)

        return ExtractionResult(
            text=text,
            title=title or None,
            extraction_method="trafilatura",
            truncated=resource.truncated,
        )


class PlainTextExtractor:
    """Plain text extraction — no external dependency."""

    def can_extract(self, content_type: str, url: str) -> bool:
        return "text/plain" in content_type.lower()

    def extract(self, resource: FetchedResource) -> ExtractionResult:
        encoding = resource.encoding or "utf-8"
        try:
            text = resource.content.decode(encoding, errors="replace")
        except Exception:
            text = resource.content.decode("utf-8", errors="replace")

        if not text.strip():
            raise ProviderExecutionError(
                f"plain text resource is empty for {resource.final_url!r}"
            )

        return ExtractionResult(
            text=text,
            title=None,
            extraction_method="plaintext",
            truncated=resource.truncated,
        )


class CompositeExtractor:
    """Selects the first capable extractor for a given resource."""

    def __init__(self, extractors: list[ContentExtractor]) -> None:
        self._extractors = extractors

    def can_extract(self, content_type: str, url: str) -> bool:
        return any(e.can_extract(content_type, url) for e in self._extractors)

    def extract(self, resource: FetchedResource) -> ExtractionResult:
        ct = resource.content_type
        url = resource.final_url
        for extractor in self._extractors:
            if extractor.can_extract(ct, url):
                return extractor.extract(resource)
        raise ProviderExecutionError(
            f"unsupported content type {ct!r} for {url!r}; "
            f"no extractor available"
        )


def default_extractor() -> CompositeExtractor:
    """Create the default extractor pipeline.

    Order: PyPDF → Docx → Trafilatura → PlainText.
    Each extractor imports its dependency lazily — construction never fails due
    to missing optional packages.
    """
    return CompositeExtractor(
        [PyPDFExtractor(), DocxExtractor(), TrafilaturaExtractor(), PlainTextExtractor()]
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_html_title(html: str) -> str:
    """Extract text from the first <title> tag in html."""
    m = re.search(r"<title[^>]*>([^<]*)</title>", html, re.IGNORECASE)
    return m.group(1).strip() if m else ""
