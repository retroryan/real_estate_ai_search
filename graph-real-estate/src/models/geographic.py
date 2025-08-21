"""Pydantic models for geographic entities"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime


class State(BaseModel):
    """State entity model"""
    state_code: str = Field(..., min_length=2, max_length=2, description="Two-letter state code")
    state_name: str = Field(..., min_length=1, description="Full state name")
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    
    @validator('state_code')
    def uppercase_state_code(cls, v):
        return v.upper()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class County(BaseModel):
    """County entity model"""
    county_id: str = Field(..., description="Unique county identifier")
    county_name: str = Field(..., description="Official county name (e.g., 'Summit County')")
    state_code: str = Field(..., min_length=2, max_length=2)
    state_name: Optional[str] = None
    
    @validator('county_id')
    def normalize_county_id(cls, v):
        """Ensure county_id is lowercase with underscores"""
        return v.lower().replace(' ', '_')
    
    @validator('state_code')
    def uppercase_state_code(cls, v):
        return v.upper()


class City(BaseModel):
    """City entity model"""
    city_id: str = Field(..., description="Unique city identifier")
    city_name: str = Field(..., description="City name")
    county_id: str = Field(..., description="Parent county identifier")
    county_name: Optional[str] = None
    state_code: str = Field(..., min_length=2, max_length=2)
    state_name: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    
    @validator('city_id')
    def normalize_city_id(cls, v):
        """Ensure city_id is lowercase with underscores"""
        return v.lower().replace(' ', '_')
    
    @validator('state_code')
    def uppercase_state_code(cls, v):
        return v.upper()


class LocationEntry(BaseModel):
    """Entry from locations.json"""
    state: Optional[str] = None
    county: Optional[str] = None
    city: Optional[str] = None
    
    def is_state_only(self) -> bool:
        """Check if this is a state-only entry"""
        return self.state is not None and self.county is None and self.city is None
    
    def is_county_entry(self) -> bool:
        """Check if this entry has county information"""
        return self.county is not None and self.state is not None
    
    def is_city_entry(self) -> bool:
        """Check if this is a complete city entry"""
        return all([self.city, self.county, self.state])


class GeographicHierarchy(BaseModel):
    """Complete geographic hierarchy"""
    states: List[State] = Field(default_factory=list)
    counties: List[County] = Field(default_factory=list)
    cities: List[City] = Field(default_factory=list)
    
    def get_state_by_code(self, state_code: str) -> Optional[State]:
        """Get state by code"""
        state_code = state_code.upper()
        for state in self.states:
            if state.state_code == state_code:
                return state
        return None
    
    def get_county_by_id(self, county_id: str) -> Optional[County]:
        """Get county by ID"""
        county_id = county_id.lower().replace(' ', '_')
        for county in self.counties:
            if county.county_id == county_id:
                return county
        return None
    
    def get_city_by_id(self, city_id: str) -> Optional[City]:
        """Get city by ID"""
        city_id = city_id.lower().replace(' ', '_')
        for city in self.cities:
            if city.city_id == city_id:
                return city
        return None
    
    def get_cities_in_county(self, county_id: str) -> List[City]:
        """Get all cities in a county"""
        county_id = county_id.lower().replace(' ', '_')
        return [city for city in self.cities if city.county_id == county_id]
    
    def get_counties_in_state(self, state_code: str) -> List[County]:
        """Get all counties in a state"""
        state_code = state_code.upper()
        return [county for county in self.counties if county.state_code == state_code]


class GeographicStats(BaseModel):
    """Statistics about geographic data"""
    total_states: int = 0
    total_counties: int = 0
    total_cities: int = 0
    cities_with_complete_path: int = 0
    counties_with_multiple_names: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)