"""
Address model for properties.

Unified address model used across all property-related functionality.
"""

from typing import Optional, Dict
from pydantic import BaseModel, Field, ConfigDict, field_validator


class Address(BaseModel):
    """
    Comprehensive address model for properties.
    
    Combines all address fields from various models into a single, 
    consistent structure.
    """
    
    # Core address fields
    street: str = Field(default="", description="Street address")
    unit: Optional[str] = Field(default=None, description="Unit/Apt number")
    city: str = Field(default="", description="City name")
    state: str = Field(default="", description="State code or name")
    zip_code: str = Field(default="", description="ZIP code", alias="zip")
    county: Optional[str] = Field(default=None, description="County name")
    country: str = Field(default="US", description="Country code")
    
    # Geographic coordinates - stored as Elasticsearch expects
    location: Optional[Dict[str, float]] = Field(
        default=None,
        description="Geographic coordinates as {lat: float, lon: float}"
    )
    
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore"
    )
    
    @field_validator('zip_code')
    @classmethod
    def validate_zip(cls, v: str) -> str:
        """Validate ZIP code format."""
        if v and len(v) > 0:
            # Remove any non-digits
            digits_only = ''.join(c for c in v if c.isdigit())
            # Accept 5 or 9 digit zips
            if len(digits_only) in [5, 9]:
                if len(digits_only) == 9:
                    return f"{digits_only[:5]}-{digits_only[5:]}"
                return digits_only
        return v
    
    @property
    def full_address(self) -> str:
        """Generate complete address string."""
        parts = []
        if self.street:
            parts.append(self.street)
            if self.unit:
                parts.append(f"Unit {self.unit}")
        if self.city and self.state:
            parts.append(f"{self.city}, {self.state}")
        elif self.city:
            parts.append(self.city)
        elif self.state:
            parts.append(self.state)
        if self.zip_code:
            parts.append(self.zip_code)
        return " ".join(parts) if parts else "Address not available"
    
    @property
    def city_state(self) -> str:
        """Get city, state string."""
        if self.city and self.state:
            return f"{self.city}, {self.state}"
        return self.city or self.state or "Location unknown"
    
    @property
    def has_coordinates(self) -> bool:
        """Check if geographic coordinates are available."""
        return bool(self.location and 'lat' in self.location and 'lon' in self.location)
    
    @property
    def latitude(self) -> Optional[float]:
        """Get latitude if available."""
        if self.has_coordinates:
            return self.location.get('lat')
        return None
    
    @property
    def longitude(self) -> Optional[float]:
        """Get longitude if available."""
        if self.has_coordinates:
            return self.location.get('lon')
        return None