"""
Hybrid search module for real estate search.

This module provides hybrid search capabilities with modular architecture:
- Semantic vector search
- Traditional text search  
- Location-aware filtering
- Elasticsearch RRF (Reciprocal Rank Fusion)

Components:
- search_engine: Core hybrid search engine
- query_builder: Elasticsearch query construction
- search_executor: Query execution with error handling
- result_processor: Response processing and transformation
- location: Location understanding and filtering
- models: Pydantic data models
"""

from .search_engine import HybridSearchEngine
from .models import HybridSearchParams, HybridSearchResult, SearchResult, LocationIntent
from .location import LocationUnderstandingModule, LocationFilterBuilder
from .query_builder import RRFQueryBuilder
from .search_executor import SearchExecutor
from .result_processor import ResultProcessor

__all__ = [
    # Core engine
    'HybridSearchEngine',
    
    # Models
    'HybridSearchParams',
    'HybridSearchResult',
    'SearchResult',
    'LocationIntent',
    
    # Components
    'LocationUnderstandingModule',
    'LocationFilterBuilder',
    'RRFQueryBuilder',
    'SearchExecutor',
    'ResultProcessor'
]