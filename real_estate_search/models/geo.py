"""
Geographic models.

Models for geographic data including coordinates, distances, and boundaries.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, computed_field, field_validator


class GeoPoint(BaseModel):
    """
    Geographic coordinate point.
    
    Represents a geographic location with latitude and longitude.
    Provides multiple formats for different use cases.
    """
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    
    model_config = ConfigDict(frozen=True)
    
    @computed_field
    @property
    def as_list(self) -> List[float]:
        """Return as [lon, lat] for Elasticsearch geo_point."""
        return [self.lon, self.lat]
    
    @computed_field
    @property
    def as_dict(self) -> dict[str, float]:
        """Return as dict for Elasticsearch geo_point."""
        return {"lat": self.lat, "lon": self.lon}
    
    @computed_field
    @property
    def as_string(self) -> str:
        """Return as 'lat,lon' string format."""
        return f"{self.lat},{self.lon}"
    
    @computed_field
    @property
    def as_wkt(self) -> str:
        """Return as Well-Known Text (WKT) POINT format."""
        return f"POINT({self.lon} {self.lat})"


class Distance(BaseModel):
    """
    Geographic distance with unit.
    
    Represents a distance value with its unit (km, mi, m, etc.).
    """
    value: float = Field(..., gt=0, description="Distance value")
    unit: str = Field("km", description="Distance unit (km, mi, m, yd, ft)")
    
    model_config = ConfigDict(frozen=True)
    
    @field_validator('unit')
    @classmethod
    def validate_unit(cls, v):
        """Validate distance unit."""
        valid_units = {'km', 'mi', 'm', 'yd', 'ft', 'nmi'}
        if v.lower() not in valid_units:
            raise ValueError(f"Invalid distance unit: {v}. Must be one of {valid_units}")
        return v.lower()
    
    @computed_field
    @property
    def as_string(self) -> str:
        """Return as string format (e.g., '5km')."""
        return f"{self.value}{self.unit}"
    
    @computed_field
    @property
    def in_meters(self) -> float:
        """Convert distance to meters."""
        conversions = {
            'm': 1.0,
            'km': 1000.0,
            'mi': 1609.34,
            'yd': 0.9144,
            'ft': 0.3048,
            'nmi': 1852.0
        }
        return self.value * conversions.get(self.unit, 1.0)


class BoundingBox(BaseModel):
    """
    Geographic bounding box.
    
    Represents a rectangular geographic area defined by its corners.
    """
    top_left: GeoPoint = Field(..., description="Top-left corner")
    bottom_right: GeoPoint = Field(..., description="Bottom-right corner")
    
    model_config = ConfigDict(frozen=True)
    
    @computed_field
    @property
    def as_elasticsearch(self) -> dict:
        """Return in Elasticsearch geo_bounding_box format."""
        return {
            "top_left": self.top_left.as_dict,
            "bottom_right": self.bottom_right.as_dict
        }
    
    @computed_field
    @property
    def as_wkt(self) -> str:
        """Return as Well-Known Text (WKT) POLYGON format."""
        return (
            f"POLYGON(("
            f"{self.top_left.lon} {self.top_left.lat}, "
            f"{self.bottom_right.lon} {self.top_left.lat}, "
            f"{self.bottom_right.lon} {self.bottom_right.lat}, "
            f"{self.top_left.lon} {self.bottom_right.lat}, "
            f"{self.top_left.lon} {self.top_left.lat}"
            f"))"
        )
    
    @computed_field
    @property
    def center(self) -> GeoPoint:
        """Calculate center point of bounding box."""
        center_lat = (self.top_left.lat + self.bottom_right.lat) / 2
        center_lon = (self.top_left.lon + self.bottom_right.lon) / 2
        return GeoPoint(lat=center_lat, lon=center_lon)


class GeoSearchParams(BaseModel):
    """
    Parameters for geographic search.
    
    Used to configure geographic searches with center point and radius.
    """
    center: GeoPoint = Field(..., description="Center point for search")
    distance: Distance = Field(
        default_factory=lambda: Distance(value=5, unit="km"),
        description="Search radius"
    )
    size: int = Field(default=10, ge=1, le=10000, description="Number of results")
    
    model_config = ConfigDict(extra="ignore")
    
    @classmethod
    def from_lat_lon(cls, lat: float, lon: float, distance_km: float = 5, size: int = 10):
        """Create from latitude/longitude values."""
        return cls(
            center=GeoPoint(lat=lat, lon=lon),
            distance=Distance(value=distance_km, unit="km"),
            size=size
        )
    
    @computed_field
    @property
    def elasticsearch_query(self) -> dict:
        """Generate Elasticsearch geo_distance query."""
        return {
            "geo_distance": {
                "distance": self.distance.as_string,
                "location": self.center.as_dict
            }
        }