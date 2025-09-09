"""
Pydantic models for rich listing demo.
Clean data models with proper validation, no runtime type checking needed.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict



class NeighborhoodModel(BaseModel):
    """Neighborhood information with proper typing."""
    neighborhood_id: Optional[str] = Field(default=None)
    name: str = Field(default="Unknown")
    city: str = Field(default="")
    state: str = Field(default="")
    population: Optional[int] = Field(default=None)
    walkability_score: Optional[int] = Field(default=None)
    school_rating: Optional[float] = Field(default=None)
    description: Optional[str] = Field(default=None)
    amenities: List[str] = Field(default_factory=list)
    demographics: Optional[Dict[str, Any]] = Field(default=None)
    
    @field_validator('amenities', mode='before')
    @classmethod
    def ensure_amenities_list(cls, v):
        """Ensure amenities is always a list."""
        if v is None:
            return []
        # Check if it's a list-like structure
        try:
            # Try to convert to list
            result = list(v)
            return result
        except (TypeError, ValueError):
            # Not list-like, return empty list
            return []
    
    @field_validator('walkability_score')
    @classmethod
    def validate_walkability(cls, v):
        """Ensure walkability score is in valid range."""
        if v is not None:
            return max(0, min(100, v))
        return v
    
    @field_validator('school_rating')
    @classmethod
    def validate_school_rating(cls, v):
        """Ensure school rating is in valid range."""
        if v is not None:
            return max(0.0, min(5.0, v))
        return v


