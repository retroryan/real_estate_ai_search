"""
Semantic search module with clean separation of concerns.

This module provides natural language semantic search functionality
using query embeddings and KNN search.
"""

from .demo_runner import (
    demo_natural_language_search,
    demo_natural_language_examples,
    demo_semantic_vs_keyword_comparison
)

__all__ = [
    'demo_natural_language_search',
    'demo_natural_language_examples',
    'demo_semantic_vs_keyword_comparison',
]