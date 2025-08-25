"""
Correlation engine for matching embeddings with source data.

Provides comprehensive correlation capabilities for linking embeddings
back to their source data with enrichment and validation.
"""

from .correlation_manager import CorrelationManager
from .enrichment_engine import EnrichmentEngine
from .models import (
    CorrelationResult,
    EnrichedEntity,
    CorrelationReport,
    SourceDataCache,
    BulkCorrelationRequest,
)

__all__ = [
    "CorrelationManager",
    "EnrichmentEngine",
    "CorrelationResult",
    "EnrichedEntity", 
    "CorrelationReport",
    "SourceDataCache",
    "BulkCorrelationRequest",
]