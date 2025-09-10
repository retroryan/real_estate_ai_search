"""
Pydantic models for aggregation search functionality.

This module defines data structures for aggregation results using Pydantic
for proper validation and type safety.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class PropertyTypeCount(BaseModel):
    """Property type count within an aggregation bucket."""
    type: str = Field(..., description="Property type name")
    count: int = Field(..., description="Number of properties of this type")


class NeighborhoodStats(BaseModel):
    """Statistics for a neighborhood aggregation."""
    neighborhood_id: str = Field(..., description="Neighborhood identifier")
    property_count: int = Field(..., description="Total number of properties")
    avg_price: float = Field(..., description="Average property price")
    min_price: float = Field(..., description="Minimum property price")
    max_price: float = Field(..., description="Maximum property price")
    avg_bedrooms: float = Field(..., description="Average number of bedrooms")
    avg_square_feet: float = Field(..., description="Average square footage")
    price_per_sqft: float = Field(..., description="Average price per square foot")
    property_types: List[PropertyTypeCount] = Field(default_factory=list, description="Property type breakdown")


class PriceRangeStats(BaseModel):
    """Statistics for a price range bucket."""
    price_range: str = Field(..., description="Human-readable price range label")
    range_start: float = Field(..., description="Start of price range")
    range_end: float = Field(..., description="End of price range")
    count: int = Field(..., description="Number of properties in range")
    property_types: Dict[str, int] = Field(default_factory=dict, description="Property type counts")
    avg_price: Optional[float] = Field(None, description="Average price in range")


class PropertyTypeStats(BaseModel):
    """Statistics for a property type."""
    property_type: str = Field(..., description="Property type name")
    count: int = Field(..., description="Number of properties")
    avg_price: Optional[float] = Field(None, description="Average price")
    min_price: Optional[float] = Field(None, description="Minimum price")
    max_price: Optional[float] = Field(None, description="Maximum price")
    median_price: Optional[float] = Field(None, description="Median price")


class GlobalStats(BaseModel):
    """Global statistics across all properties."""
    total_properties: int = Field(0, description="Total number of properties")
    overall_avg_price: float = Field(0.0, description="Overall average price")