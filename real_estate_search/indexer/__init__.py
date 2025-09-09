"""
Elasticsearch Indexer Module for Real Estate Search.

This module contains specialized indexers for different data types,
managing the indexing pipeline, document processing, and bulk operations.
"""

from .wikipedia_indexer import (
    WikipediaIndexer,
    WikipediaEnrichmentConfig,
    WikipediaEnrichmentResult
)

__all__ = [
    'WikipediaIndexer',
    'WikipediaEnrichmentConfig',
    'WikipediaEnrichmentResult'
]