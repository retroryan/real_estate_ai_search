"""Standardized neighborhood model with cleaned data."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class StandardizedNeighborhood(BaseModel):
    """Standardized neighborhood with validated and cleaned data."""
    
    model_config = ConfigDict(frozen=True)
    
    # Core identifiers
    neighborhood_id: str = Field(description="Standardized neighborhood ID")
    name: str = Field(description="Cleaned neighborhood name")
    
    # Location (standardized)
    city: str = Field(description="Standardized city name")
    state_code: str = Field(pattern="^[A-Z]{2}$", description="2-letter state code")
    county: str = Field(default="", description="County name")
    
    # Demographics (validated)
    population: int = Field(ge=0, description="Population count")
    households: int = Field(ge=0, description="Number of households")
    median_age: float = Field(ge=0, le=120, description="Median age")
    median_income: float = Field(ge=0, description="Median household income")
    
    # Housing statistics (validated)
    median_home_price: float = Field(ge=0, description="Median home price")
    median_rent: float = Field(ge=0, description="Median rent")
    home_ownership_rate: float = Field(ge=0, le=1, description="Ownership rate 0-1")
    
    # Quality metrics (normalized)
    crime_score: float = Field(ge=0, le=10, description="Crime score 0-10 (10=safest)")
    school_score: float = Field(ge=0, le=10, description="School score 0-10")
    walkability_score: int = Field(ge=0, le=100, description="Walkability 0-100")
    transit_score: int = Field(ge=0, le=100, description="Transit score 0-100")
    
    # Geographic data (validated)
    center_latitude: float = Field(ge=-90, le=90, description="Center latitude")
    center_longitude: float = Field(ge=-180, le=180, description="Center longitude")
    area_sqmi: float = Field(gt=0, description="Area in square miles")
    
    # Text fields (cleaned)
    description: str = Field(default="", description="Cleaned description")
    highlights: list[str] = Field(default_factory=list, description="Key highlights")
    
    # Relationships
    adjacent_neighborhoods: list[str] = Field(default_factory=list, description="Adjacent neighborhood IDs")
    wikipedia_page_id: Optional[str] = Field(default=None, description="Linked Wikipedia page")
    
    # Metadata
    data_quality_score: float = Field(ge=0, le=1, description="Data completeness score")
    processing_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Processing time")
    
    @field_validator("crime_score")
    @classmethod
    def normalize_crime_score(cls, v: float, info) -> float:
        """Ensure crime score is normalized."""
        return max(0, min(10, v))
    
    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        """Clean and standardize neighborhood name."""
        return v.strip().title()