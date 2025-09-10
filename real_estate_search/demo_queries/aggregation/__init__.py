"""
Aggregation queries module for statistical analysis.

This module provides demonstration functions for Elasticsearch aggregations
including neighborhood statistics and price distribution analysis.
"""

from .demo_runner import (
    demo_neighborhood_stats,
    demo_price_distribution
)

__all__ = [
    "demo_neighborhood_stats",
    "demo_price_distribution"
]