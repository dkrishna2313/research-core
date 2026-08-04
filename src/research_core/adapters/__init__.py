"""
research_core.adapters — concrete provider implementations.

Each adapter sub-package implements one or more research_core protocols
and connects to an external backend. Adapters live inside research_core
but their backends are optional dependencies: importing an adapter module
does not require the backend at import time.

Available adapters:
  research_core.adapters.knowledge  — KnowledgeProvider backed by the
                                       knowledge-layer (dc-power-agent)
"""
