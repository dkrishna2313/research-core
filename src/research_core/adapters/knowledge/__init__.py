"""
research_core.adapters.knowledge — KnowledgeProvider backed by the knowledge-layer.

Importing this module does NOT require the knowledge package (dc-power-agent).
The KnowledgeAdapter class is importable at all times; retrieve() raises
ProviderUnavailableError at runtime if the package is not installed.

Install the optional extra to enable the adapter:
    pip install research-core[knowledge]

Usage::

    from research_core.adapters.knowledge import KnowledgeAdapter

    adapter = KnowledgeAdapter(store_root="/path/to/knowledge_store")
    result = adapter.retrieve(request)  # KnowledgeRetrievalResult
"""

from research_core.adapters.knowledge.adapter import KnowledgeAdapter

__all__ = ["KnowledgeAdapter"]
