"""
Property relationships demo queries module.

This module contains query builders and utilities for searching
the denormalized property_relationships index.
"""

from .query_builder import PropertyRelationshipsQueryBuilder

__all__ = [
    "PropertyRelationshipsQueryBuilder"
]