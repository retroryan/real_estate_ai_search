"""
Elasticsearch writer package.

This package contains the Elasticsearch orchestrator for entity-specific indexing.
"""

from .elasticsearch_orchestrator import ElasticsearchOrchestrator

__all__ = ["ElasticsearchOrchestrator"]