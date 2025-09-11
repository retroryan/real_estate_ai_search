"""
GeoJSON models for geographic data structures.

Pydantic models representing GeoJSON structures for geographic boundaries.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class GeoJSONPoint(BaseModel):
    """GeoJSON Point geometry."""
    type: Literal["Point"] = Field("Point", description="Geometry type")
    coordinates: List[float] = Field(..., description="[longitude, latitude]", min_length=2, max_length=2)


class GeoJSONPolygon(BaseModel):
    """GeoJSON Polygon geometry."""
    type: Literal["Polygon"] = Field("Polygon", description="Geometry type")
    coordinates: List[List[List[float]]] = Field(..., description="Polygon coordinates")


class GeoJSONMultiPolygon(BaseModel):
    """GeoJSON MultiPolygon geometry."""
    type: Literal["MultiPolygon"] = Field("MultiPolygon", description="Geometry type")
    coordinates: List[List[List[List[float]]]] = Field(..., description="MultiPolygon coordinates")


class GeoJSONBoundingBox(BaseModel):
    """Geographic bounding box."""
    min_lon: float = Field(..., ge=-180, le=180, description="Minimum longitude")
    min_lat: float = Field(..., ge=-90, le=90, description="Minimum latitude")
    max_lon: float = Field(..., ge=-180, le=180, description="Maximum longitude")
    max_lat: float = Field(..., ge=-90, le=90, description="Maximum latitude")
    
    def to_elasticsearch(self) -> dict:
        """Convert to Elasticsearch geo bounding box format."""
        return {
            "top_left": {"lat": self.max_lat, "lon": self.min_lon},
            "bottom_right": {"lat": self.min_lat, "lon": self.max_lon}
        }


class GeographicBoundaries(BaseModel):
    """Geographic boundaries for a region."""
    bounding_box: Optional[GeoJSONBoundingBox] = Field(None, description="Bounding box")
    polygon: Optional[GeoJSONPolygon] = Field(None, description="Boundary polygon")
    multi_polygon: Optional[GeoJSONMultiPolygon] = Field(None, description="Multiple boundary polygons")
    center_point: Optional[GeoJSONPoint] = Field(None, description="Center point of region")