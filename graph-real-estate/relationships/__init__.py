"""
Neo4j Relationship Builder Module

This module handles all relationship creation using pure Neo4j Cypher queries.
It operates as a separate orchestration step after nodes are loaded.

Features:
- Pydantic-based configuration and validation
- Performance monitoring and timing
- Robust error handling with graceful degradation
- Hierarchical geographic relationship building
- Type-safe result objects
"""

from .builder import RelationshipOrchestrator, RelationshipStats, BuildProcessStats
from .config import RelationshipConfig, RelationshipResult, RelationshipBatchConfig
from .geographic import GeographicRelationshipBuilder
from .classification import ClassificationRelationshipBuilder
from .similarity import SimilarityRelationshipBuilder

__all__ = [
    # Main orchestration
    "RelationshipOrchestrator",
    "RelationshipStats",
    "BuildProcessStats",
    
    # Configuration models
    "RelationshipConfig",
    "RelationshipResult", 
    "RelationshipBatchConfig",
    
    # Individual builders
    "GeographicRelationshipBuilder",
    "ClassificationRelationshipBuilder", 
    "SimilarityRelationshipBuilder",
]