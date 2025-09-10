"""
Pydantic models for location-related functionality.
"""

from typing import Optional
from pydantic import BaseModel, Field


class LocationIntent(BaseModel):
    """Extracted location intent from natural language query."""
    city: Optional[str] = Field(None, description="Extracted city name")
    state: Optional[str] = Field(None, description="Extracted state name")
    neighborhood: Optional[str] = Field(None, description="Extracted neighborhood name")
    zip_code: Optional[str] = Field(None, description="Extracted ZIP code")
    has_location: bool = Field(False, description="Whether location was found in query")
    cleaned_query: str = Field(..., description="Query with location terms removed")
    confidence: float = Field(0.0, description="Confidence score for extraction")