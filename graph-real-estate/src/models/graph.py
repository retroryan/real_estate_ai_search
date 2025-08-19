"""Graph node models"""
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum

class PriceRange(str, Enum):
    """Price range categories"""
    UNDER_500K = "0-500k"
    TO_1M = "500k-1M"
    TO_2M = "1M-2M"
    TO_3M = "2M-3M"
    OVER_3M = "3M+"

class Neighborhood(BaseModel):
    """Neighborhood model"""
    id: str = Field(..., description="Neighborhood identifier")
    name: str = Field(..., description="Neighborhood name")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State name")

class City(BaseModel):
    """City model"""
    name: str = Field(..., description="City name")
    state: str = Field(..., description="State name")

class Feature(BaseModel):
    """Feature model"""
    name: str = Field(..., description="Feature name")
    category: Optional[str] = Field(default=None, description="Feature category")

class GraphStats(BaseModel):
    """Graph database statistics"""
    total_nodes: int = 0
    properties: int = 0
    neighborhoods: int = 0
    cities: int = 0
    features: int = 0
    relationships: int = 0