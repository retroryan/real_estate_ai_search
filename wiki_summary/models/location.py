"""
Pydantic models and constants for location management.
Follows SOLID principles with clear separation of concerns.
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class LocationType(str, Enum):
    """Enumeration for location types."""
    CITY = "city"
    COUNTY = "county"
    STATE = "state"
    NEIGHBORHOOD = "neighborhood"
    NATIONAL_PARK = "national_park"
    MOUNTAIN = "mountain"
    CANYON = "canyon"
    VALLEY = "valley"
    DISTRICT = "district"


class StateAbbreviation(str, Enum):
    """Common state abbreviations and variations."""
    CALIFORNIA = "california"
    CA = "ca"
    CALIF = "calif"
    UTAH = "utah"
    UT = "ut"
    ILLINOIS = "illinois"
    IL = "il"
    COLORADO = "colorado"
    CO = "co"
    OHIO = "ohio"
    OH = "oh"
    KENTUCKY = "kentucky"
    KY = "ky"


class Country(str, Enum):
    """Country constants."""
    UNITED_STATES = "United States"


class ConfidenceThreshold(float, Enum):
    """Confidence thresholds for different operations."""
    HIGH_CONFIDENCE = 0.8
    MEDIUM_CONFIDENCE = 0.7
    LOW_CONFIDENCE = 0.5
    MINIMUM_FOR_FIX = 0.7


class LocationData(BaseModel):
    """Represents a geographic location with all necessary fields."""
    model_config = ConfigDict(validate_assignment=True)
    
    country: str = Field(default=Country.UNITED_STATES.value, description="Country name")
    state: str = Field(..., description="State name")
    county: Optional[str] = Field(None, description="County name")
    city: Optional[str] = Field(None, description="City name")
    location_type: LocationType = Field(..., description="Type of location")
    path: str = Field(..., description="Hierarchical path representation")
    location_id: Optional[int] = Field(None, description="Database ID")
    
    @classmethod
    def from_components(cls, state: str, city: Optional[str] = None, 
                       county: Optional[str] = None) -> "LocationData":
        """Create LocationData from components."""
        # Normalize inputs
        state = state.strip() if state else ""
        city = city.strip() if city else None
        county = county.strip() if county else None
        
        # Determine location type
        if city:
            location_type = LocationType.CITY
        elif county:
            location_type = LocationType.COUNTY
        else:
            location_type = LocationType.STATE
        
        # Build path
        path_parts = [Country.UNITED_STATES.value, state]
        if county:
            path_parts.append(county)
        if city:
            path_parts.append(city)
        path = "/".join(path_parts)
        
        return cls(
            state=state,
            city=city,
            county=county,
            location_type=location_type,
            path=path
        )
    
    def matches_state(self, other_state: str) -> bool:
        """Check if this location's state matches another state (handles abbreviations)."""
        if not other_state:
            return False
            
        self_state = self.state.lower()
        other_state = other_state.lower()
        
        # Direct match
        if self_state == other_state:
            return True
        
        # Check state abbreviations
        state_mappings = {
            'california': ['ca', 'calif'],
            'utah': ['ut'],
            'illinois': ['il'],
            'colorado': ['co'],
            'ohio': ['oh'],
            'kentucky': ['ky']
        }
        
        for full_name, abbrevs in state_mappings.items():
            if (self_state == full_name and other_state in abbrevs) or \
               (other_state == full_name and self_state in abbrevs):
                return True
        
        return False


class ArticleData(BaseModel):
    """Represents article data from the database."""
    model_config = ConfigDict(validate_assignment=True)
    
    id: int = Field(..., description="Article ID")
    pageid: int = Field(..., description="Wikipedia page ID")
    title: str = Field(..., description="Article title")
    location_id: int = Field(..., description="Associated location ID")
    url: Optional[str] = Field(None, description="Wikipedia URL")
    extract: Optional[str] = Field(None, description="Article extract")
    categories: Optional[str] = Field(None, description="Categories as JSON")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    relevance_score: Optional[float] = Field(None, description="Relevance score")
    depth: Optional[int] = Field(None, description="Crawl depth")
    crawled_at: Optional[str] = Field(None, description="Crawl timestamp")
    html_file: Optional[str] = Field(None, description="HTML file path")
    file_hash: Optional[str] = Field(None, description="File hash")
    image_url: Optional[str] = Field(None, description="Image URL")
    links_count: Optional[int] = Field(None, description="Number of links")
    infobox_data: Optional[str] = Field(None, description="Infobox data as JSON")


class LocationMismatch(BaseModel):
    """Represents a detected location mismatch."""
    model_config = ConfigDict(validate_assignment=True)
    
    article: ArticleData = Field(..., description="Article with mismatched location")
    current_location: LocationData = Field(..., description="Current (incorrect) location")
    corrected_location: LocationData = Field(..., description="Corrected location from LLM")
    confidence: float = Field(..., description="Confidence in the correction")
    
    @property
    def should_fix(self) -> bool:
        """Determine if this mismatch should be fixed.
        
        Returns True if:
        1. Normal case: confidence is high enough for a location fix
        2. Special case: confidence is very low AND no location was found
           (indicates article is not about a geographic location at all)
        """
        # Special case: very low confidence with no corrected location means
        # the article is likely not about a geographic place at all
        if not self.corrected_location.state and self.confidence < 0.1:
            return True  # Should be processed (for removal)
        
        # Normal case: confidence threshold for location fixes
        return self.confidence >= ConfidenceThreshold.MINIMUM_FOR_FIX.value


class LocationFixResult(BaseModel):
    """Result of a location fix operation."""
    model_config = ConfigDict(validate_assignment=True)
    
    success: bool = Field(..., description="Whether the fix was successful")
    article_title: str = Field(..., description="Title of the article")
    article_id: int = Field(..., description="Article ID (unchanged)")
    old_location_id: int = Field(..., description="Previous location ID")
    new_location_id: int = Field(..., description="New location ID")
    error_message: Optional[str] = Field(None, description="Error message if failed")