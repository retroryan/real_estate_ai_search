"""Raw neighborhood model matching source data."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class RawNeighborhood(BaseModel):
    """Raw neighborhood data as it appears in source files."""
    
    model_config = ConfigDict(frozen=True)
    
    # Core identifiers
    neighborhood_id: str = Field(description="Unique neighborhood identifier")
    name: str = Field(description="Neighborhood name")
    
    # Location
    city: str = Field(description="City")
    state: str = Field(description="State code")
    county: Optional[str] = Field(default=None, description="County name")
    
    # Demographics
    population: Optional[int] = Field(default=None, description="Population count")
    households: Optional[int] = Field(default=None, description="Number of households")
    median_age: Optional[float] = Field(default=None, description="Median age of residents")
    median_income: Optional[float] = Field(default=None, description="Median household income")
    
    # Housing statistics
    median_home_price: Optional[float] = Field(default=None, description="Median home price")
    median_rent: Optional[float] = Field(default=None, description="Median rent price")
    home_ownership_rate: Optional[float] = Field(default=None, description="Home ownership percentage")
    
    # Quality metrics
    crime_rate: Optional[str] = Field(default=None, description="Crime rate category")
    school_rating: Optional[float] = Field(default=None, description="Average school rating")
    walkability_score: Optional[int] = Field(default=None, description="Walkability score 0-100")
    transit_score: Optional[int] = Field(default=None, description="Transit score 0-100")
    
    # Boundaries
    boundary_coordinates: Optional[str] = Field(default=None, description="Boundary polygon coordinates")
    center_latitude: Optional[float] = Field(default=None, description="Center point latitude")
    center_longitude: Optional[float] = Field(default=None, description="Center point longitude")
    area_sqmi: Optional[float] = Field(default=None, description="Area in square miles")
    
    # Description
    description: Optional[str] = Field(default=None, description="Neighborhood description")
    highlights: Optional[str] = Field(default=None, description="Neighborhood highlights")
    
    # Wikipedia correlation
    wikipedia_url: Optional[str] = Field(default=None, description="Wikipedia article URL")
    wikipedia_summary: Optional[str] = Field(default=None, description="Wikipedia summary")