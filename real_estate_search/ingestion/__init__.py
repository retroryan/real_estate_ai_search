"""
Multi-entity ingestion module for Elasticsearch.
Orchestrates property and Wikipedia data ingestion using existing components.
"""

from .orchestrator import IngestionOrchestrator

__all__ = ["IngestionOrchestrator"]