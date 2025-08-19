"""
Unified ingestion module for Elasticsearch.
Orchestrates property and Wikipedia data ingestion using existing components.
"""

from .orchestrator import UnifiedIngestionPipeline

__all__ = ["UnifiedIngestionPipeline"]