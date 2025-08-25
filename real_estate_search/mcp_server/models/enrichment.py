"""
Enrichment data models.
Models for Wikipedia and location enrichment data.
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator

from .property import GeoLocation


class POICategory(str, Enum):
    """Point of Interest categories."""
    education = "education"
    healthcare = "healthcare"
    shopping = "shopping"
    dining = "dining"
    entertainment = "entertainment"
    transportation = "transportation"
    recreation = "recreation"
    cultural = "cultural"
    government = "government"
    religious = "religious"
    other = "other"


class WikipediaContext(BaseModel):
    """Wikipedia enrichment context for a location."""
    
    wikipedia_title: Optional[str] = Field(None, description="Wikipedia article title")
    wikipedia_url: Optional[str] = Field(None, description="Wikipedia article URL")
    summary: Optional[str] = Field(None, max_length=2000, description="Location summary")
    location_summary: Optional[str] = Field(None, description="Brief location description")
    historical_significance: Optional[str] = Field(None, description="Historical importance")
    key_topics: List[str] = Field(default_factory=list, description="Key topics mentioned")
    notable_features: List[str] = Field(default_factory=list, description="Notable features")
    character: Optional[str] = Field(None, description="Neighborhood character")
    notable_residents: List[str] = Field(default_factory=list, description="Notable residents")
    confidence_score: float = Field(0.0, ge=0, le=1, description="Data confidence score")
    
    @field_validator("wikipedia_url")
    @classmethod
    def validate_wikipedia_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate Wikipedia URL format."""
        if v and not v.startswith("https://en.wikipedia.org/"):
            raise ValueError("Invalid Wikipedia URL")
        return v


class POIInfo(BaseModel):
    """Point of Interest information."""
    
    name: str = Field(..., min_length=1, description="POI name")
    category: POICategory = Field(..., description="POI category")
    subcategory: Optional[str] = Field(None, description="Specific subcategory")
    location: Optional[GeoLocation] = Field(None, description="POI coordinates")
    distance_miles: Optional[float] = Field(None, ge=0, description="Distance in miles")
    address: Optional[str] = Field(None, description="POI address")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Rating if available")
    wikipedia_url: Optional[str] = Field(None, description="Wikipedia URL if available")
    description: Optional[str] = Field(None, max_length=500, description="Brief description")
    
    def get_display_distance(self) -> str:
        """Get formatted distance for display."""
        if self.distance_miles is None:
            return "Distance unknown"
        elif self.distance_miles < 0.1:
            return "< 0.1 miles"
        elif self.distance_miles < 1:
            return f"{self.distance_miles:.1f} miles"
        else:
            return f"{self.distance_miles:.0f} miles"


class NeighborhoodContext(BaseModel):
    """Enriched neighborhood information."""
    
    name: str = Field(..., description="Neighborhood name")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State code")
    boundary: Optional[List[GeoLocation]] = Field(None, description="Neighborhood boundary")
    center: Optional[GeoLocation] = Field(None, description="Neighborhood center")
    wikipedia_context: Optional[WikipediaContext] = Field(None, description="Wikipedia data")
    demographics: Optional[Dict[str, Any]] = Field(None, description="Demographic data")
    walkability_score: Optional[int] = Field(None, ge=0, le=100, description="Walk score")
    transit_score: Optional[int] = Field(None, ge=0, le=100, description="Transit score")
    bike_score: Optional[int] = Field(None, ge=0, le=100, description="Bike score")
    crime_grade: Optional[str] = Field(None, pattern="^[A-F][+-]?$", description="Crime grade")
    school_rating: Optional[float] = Field(None, ge=0, le=10, description="School rating")
    median_home_price: Optional[float] = Field(None, gt=0, description="Median home price")
    price_trend: Optional[float] = Field(None, description="Price trend percentage")
    
    def get_lifestyle_summary(self) -> str:
        """Get lifestyle summary for the neighborhood."""
        scores = []
        if self.walkability_score:
            scores.append(f"Walk Score: {self.walkability_score}")
        if self.transit_score:
            scores.append(f"Transit: {self.transit_score}")
        if self.school_rating:
            scores.append(f"Schools: {self.school_rating}/10")
        
        return " | ".join(scores) if scores else "Lifestyle data unavailable"


class LocationHistory(BaseModel):
    """Historical information about a location."""
    
    location: GeoLocation = Field(..., description="Location coordinates")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State code")
    founded_year: Optional[int] = Field(None, description="Year founded/established")
    historical_events: List[Dict[str, Any]] = Field(default_factory=list, description="Historical events")
    notable_landmarks: List[str] = Field(default_factory=list, description="Notable landmarks")
    cultural_significance: Optional[str] = Field(None, description="Cultural importance")
    economic_history: Optional[str] = Field(None, description="Economic development history")
    population_history: List[Dict[str, Any]] = Field(default_factory=list, description="Population over time")
    wikipedia_context: Optional[WikipediaContext] = Field(None, description="Wikipedia data")


class MarketContext(BaseModel):
    """Real estate market context for a location."""
    
    location_name: str = Field(..., description="Location name")
    median_price: Optional[float] = Field(None, gt=0, description="Median home price")
    average_price_sqft: Optional[float] = Field(None, gt=0, description="Average price per sq ft")
    inventory_count: Optional[int] = Field(None, ge=0, description="Active listings count")
    days_on_market: Optional[float] = Field(None, ge=0, description="Average days on market")
    price_trend_30d: Optional[float] = Field(None, description="30-day price trend %")
    price_trend_90d: Optional[float] = Field(None, description="90-day price trend %")
    price_trend_1y: Optional[float] = Field(None, description="1-year price trend %")
    buyer_seller_index: Optional[float] = Field(None, ge=-1, le=1, description="Market balance (-1 buyer's, +1 seller's)")
    forecast_3m: Optional[str] = Field(None, description="3-month forecast")
    forecast_1y: Optional[str] = Field(None, description="1-year forecast")
    
    def get_market_summary(self) -> str:
        """Get market summary text."""
        if self.buyer_seller_index is not None:
            if self.buyer_seller_index < -0.3:
                market_type = "Strong buyer's market"
            elif self.buyer_seller_index < 0:
                market_type = "Buyer's market"
            elif self.buyer_seller_index > 0.3:
                market_type = "Strong seller's market"
            elif self.buyer_seller_index > 0:
                market_type = "Seller's market"
            else:
                market_type = "Balanced market"
        else:
            market_type = "Market conditions unknown"
        
        return f"{market_type} - Median: ${self.median_price:,.0f}" if self.median_price else market_type


class EnrichmentBundle(BaseModel):
    """Complete enrichment data bundle for a property."""
    
    property_id: str = Field(..., description="Property ID")
    wikipedia_context: Optional[WikipediaContext] = Field(None, description="Wikipedia enrichment")
    neighborhood_context: Optional[NeighborhoodContext] = Field(None, description="Neighborhood data")
    nearby_pois: List[POIInfo] = Field(default_factory=list, description="Nearby points of interest")
    location_history: Optional[LocationHistory] = Field(None, description="Location history")
    market_context: Optional[MarketContext] = Field(None, description="Market context")
    enrichment_timestamp: Optional[str] = Field(None, description="When enrichment was performed")
    
    def has_enrichment(self) -> bool:
        """Check if any enrichment data is present."""
        return bool(
            self.wikipedia_context or
            self.neighborhood_context or
            self.nearby_pois or
            self.location_history or
            self.market_context
        )