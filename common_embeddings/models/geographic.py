"""
Geographic and location-related models.

Provides models for coordinates, addresses, and location information.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class GeoLocation(BaseModel):
    """Geographic coordinates with automatic validation."""
    
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")


class GeoPolygon(BaseModel):
    """Geographic polygon for boundaries."""
    
    points: List[GeoLocation] = Field(..., min_length=3, description="Polygon points (minimum 3)")


class EnrichedAddress(BaseModel):
    """
    Enriched address with normalized city and state.
    """
    
    street: str = Field(..., description="Street address")
    city: str = Field(..., description="Normalized city name (e.g., 'San Francisco', not 'SF')")
    state: str = Field(..., description="Full state name (e.g., 'California', not 'CA')")
    zip_code: str = Field(..., description="ZIP code")
    coordinates: Optional[GeoLocation] = Field(None, description="Validated geographic coordinates")
    
    @field_validator('city')
    @classmethod
    def validate_city(cls, v: str) -> str:
        """Ensure city is not empty."""
        if not v or not v.strip():
            raise ValueError("City cannot be empty")
        return v.strip()
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Ensure state is not empty."""
        if not v or not v.strip():
            raise ValueError("State cannot be empty")
        return v.strip()


class LocationInfo(BaseModel):
    """Location information for Wikipedia articles."""
    
    city: Optional[str] = Field(None, description="Associated city")
    state: Optional[str] = Field(None, description="Associated state")
    country: str = Field("United States", description="Country")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")