"""
Neighborhood models.

Consolidated neighborhood and demographic models used throughout the application.
Single source of truth for all neighborhood-related data structures.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field
from .geojson import GeographicBoundaries


class Demographics(BaseModel):
    """Neighborhood demographic information."""
    population: Optional[int] = Field(None, ge=0, description="Total population")
    households: Optional[int] = Field(None, ge=0, description="Number of households")
    median_age: Optional[float] = Field(None, ge=0, le=120, description="Median age")
    median_income: Optional[float] = Field(None, ge=0, description="Median household income")
    median_home_value: Optional[float] = Field(None, ge=0, description="Median home value")
    
    model_config = ConfigDict(extra="ignore")


class SchoolRatings(BaseModel):
    """School ratings for a neighborhood."""
    elementary: Optional[float] = Field(None, ge=0, le=10, description="Elementary school rating")
    middle: Optional[float] = Field(None, ge=0, le=10, description="Middle school rating")
    high: Optional[float] = Field(None, ge=0, le=10, description="High school rating")
    overall: Optional[float] = Field(None, ge=0, le=10, description="Overall school rating")
    
    @computed_field
    @property
    def average_rating(self) -> Optional[float]:
        """Calculate average school rating."""
        ratings = [r for r in [self.elementary, self.middle, self.high] if r is not None]
        return sum(ratings) / len(ratings) if ratings else None
    
    @field_validator('overall')
    @classmethod
    def validate_overall(cls, v):
        """Ensure overall rating is in valid range."""
        if v is not None:
            return max(0.0, min(10.0, v))
        return v
    
    model_config = ConfigDict(extra="ignore")


class Neighborhood(BaseModel):
    """
    Complete neighborhood model.
    
    This model consolidates all neighborhood information from various sources
    including demographic data, school ratings, amenities, and statistics.
    """
    # Core identification
    neighborhood_id: str = Field(..., description="Unique neighborhood identifier")
    name: str = Field(..., description="Neighborhood name")
    
    # Location
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State code or name")
    county: Optional[str] = Field(None, description="County name")
    
    # Geographic data
    location: Optional[List[float]] = Field(None, description="[longitude, latitude]")
    boundaries: Optional[GeographicBoundaries] = Field(None, description="Geographic boundaries")
    area_sqmi: Optional[float] = Field(None, ge=0, description="Area in square miles")
    
    # Characteristics
    description: Optional[str] = Field(None, description="Neighborhood description")
    established_year: Optional[int] = Field(None, ge=1600, le=2100, description="Year established")
    
    # Amenities and features
    amenities: List[str] = Field(default_factory=list, description="Neighborhood amenities")
    public_transport: List[str] = Field(default_factory=list, description="Public transport options")
    nearby_schools: List[str] = Field(default_factory=list, description="Nearby schools")
    parks: List[str] = Field(default_factory=list, description="Parks and recreation")
    
    # Statistics
    demographics: Optional[Demographics] = Field(None, description="Demographic information")
    school_ratings: Optional[SchoolRatings] = Field(None, description="School ratings")
    crime_rate: Optional[str] = Field(None, description="Crime rate category")
    walkability_score: Optional[int] = Field(None, ge=0, le=100, description="Walk score")
    overall_livability_score: Optional[float] = Field(None, ge=0, le=100, description="Overall livability")
    
    # Property statistics
    avg_price: Optional[float] = Field(None, ge=0, description="Average property price")
    avg_price_per_sqft: Optional[float] = Field(None, ge=0, description="Average price per sqft")
    property_count: Optional[int] = Field(None, ge=0, description="Number of properties")
    
    # Embedding fields (for vector search)
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    embedding_model: Optional[str] = Field(None, description="Model used for embedding")
    embedding_dimension: Optional[int] = Field(None, description="Embedding dimension")
    embedded_at: Optional[datetime] = Field(None, description="When embedding was created")
    
    # Wikipedia correlations
    wikipedia_correlations: Optional[List[str]] = Field(None, description="Related Wikipedia article IDs")
    
    # Search metadata
    score: Optional[float] = Field(None, alias="_score", description="Search relevance score")
    
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


    
    @computed_field
    @property
    def display_name(self) -> str:
        """Get display name with city."""
        if self.city:
            return f"{self.name}, {self.city}"
        return self.name
    
