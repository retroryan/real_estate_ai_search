"""
Advanced search module for semantic, multi-entity, and Wikipedia searches.

This module provides specialized search capabilities:
- Semantic similarity search using vector embeddings
- Multi-entity cross-index search
- Wikipedia article search with geographic filtering
"""

from .models import (
    SearchRequest,
    MultiIndexSearchRequest,
    WikipediaSearchRequest,
    LocationFilter,
    EntityDiscriminationResult
)
from .semantic_search import SemanticSearchBuilder
from .multi_entity_search import MultiEntitySearchBuilder
from .wikipedia_search import WikipediaSearchBuilder
from .search_executor import AdvancedSearchExecutor
from .demo_runner import (
    AdvancedDemoRunner,
    demo_semantic_search,
    demo_multi_entity_search,
    demo_wikipedia_search
)
from .display_service import AdvancedDisplayService

__all__ = [
    # Models
    'SearchRequest',
    'MultiIndexSearchRequest',
    'WikipediaSearchRequest',
    'LocationFilter',
    'EntityDiscriminationResult',
    # Builders
    'SemanticSearchBuilder',
    'MultiEntitySearchBuilder',
    'WikipediaSearchBuilder',
    # Executor and Services
    'AdvancedSearchExecutor',
    'AdvancedDemoRunner',
    'AdvancedDisplayService',
    # Demo functions
    'demo_semantic_search',
    'demo_multi_entity_search',
    'demo_wikipedia_search',
]