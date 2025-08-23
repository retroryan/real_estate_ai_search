"""
Pydantic models for enriched neighborhood data.

Note: This imports the EnrichedNeighborhood model from property.py
to maintain backward compatibility while keeping the model definitions
in one place. In a future refactor, the model could be moved here.
"""

from .property import EnrichedNeighborhood

__all__ = ['EnrichedNeighborhood']