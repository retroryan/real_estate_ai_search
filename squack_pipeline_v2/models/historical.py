"""Simplified annual historical data models using Pydantic.

This module contains minimal historical data models for neighborhoods and properties.
Simple annual records with only essential fields for demo purposes.
"""

from pydantic import BaseModel, Field


class AnnualHistoricalRecord(BaseModel):
    """Annual historical record for neighborhoods.
    
    Contains only essential yearly metrics for price trends.
    """
    
    year: int = Field(ge=2015, le=2024)
    avg_price: float = Field(gt=0)
    sales_count: int = Field(ge=0)


class PropertyHistoricalRecord(BaseModel):
    """Annual historical record for individual properties.
    
    Even simpler than neighborhoods - just annual prices.
    """
    
    year: int = Field(ge=2015, le=2024)
    price: float = Field(gt=0)