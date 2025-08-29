"""Pydantic models for all data entities based on actual source structure."""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, validator


class PropertyAddress(BaseModel):
    """Property address structure."""
    street: str
    city: str
    county: str
    state: str
    zip: str


class PropertyDetails(BaseModel):
    """Property details structure."""
    square_feet: int
    bedrooms: int
    bathrooms: float
    property_type: str
    year_built: int
    lot_size: float
    stories: int
    garage_spaces: int


class PropertyCoordinates(BaseModel):
    """Property coordinates structure."""
    latitude: float
    longitude: float


class Property(BaseModel):
    """Complete property model matching source JSON structure."""
    listing_id: str
    neighborhood_id: str
    listing_price: int
    price_per_sqft: float
    listing_date: str
    days_on_market: int
    address: PropertyAddress
    property_details: PropertyDetails
    coordinates: PropertyCoordinates
    description: str
    features: List[str]
    images: List[str]
    price_history: List[Dict[str, Any]]
    virtual_tour_url: Optional[str] = None


class NeighborhoodCharacteristics(BaseModel):
    """Neighborhood characteristics structure."""
    walkability_score: int
    transit_score: int
    school_rating: int
    safety_rating: int
    nightlife_score: int
    family_friendly_score: int


class NeighborhoodDemographics(BaseModel):
    """Neighborhood demographics structure."""
    primary_age_group: str
    vibe: str
    population: Optional[int] = None
    median_household_income: Optional[int] = None


class NeighborhoodCoordinates(BaseModel):
    """Neighborhood coordinates structure."""
    latitude: float
    longitude: float


class Neighborhood(BaseModel):
    """Complete neighborhood model matching source JSON structure."""
    neighborhood_id: str
    name: str
    city: str
    county: str
    state: str
    coordinates: NeighborhoodCoordinates
    characteristics: NeighborhoodCharacteristics
    demographics: NeighborhoodDemographics
    description: str
    amenities: List[str]
    lifestyle_tags: List[str]
    median_home_price: int
    price_trend: str
    wikipedia_correlations: Dict[str, Any]


class Location(BaseModel):
    """Location model matching source JSON structure."""
    city: str
    county: Optional[str] = None
    state: str
    zip_code: str
    neighborhood: Optional[str] = None


class WikipediaArticle(BaseModel):
    """Wikipedia article model matching database structure."""
    id: int
    pageid: int
    location_id: int
    title: str
    url: Optional[str] = None
    extract: Optional[str] = None
    categories: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    relevance_score: Optional[float] = None
    depth: Optional[int] = None
    crawled_at: Optional[str] = None
    html_file: Optional[str] = None
    file_hash: Optional[str] = None
    image_url: Optional[str] = None
    links_count: Optional[int] = None
    infobox_data: Optional[str] = None




class PropertySilver(BaseModel):
    """Silver tier property model with nested structures and denormalized fields."""
    # Core fields
    listing_id: str
    neighborhood_id: Optional[str]
    listing_price: Optional[int]
    price_per_sqft: Optional[float]
    listing_date: Optional[str]
    days_on_market: Optional[int]
    
    # Nested structures preserved from Bronze
    address: PropertyAddress
    property_details: PropertyDetails
    coordinates: PropertyCoordinates
    
    # Denormalized fields for common queries (extracted from nested)
    city: str  # From address.city
    state: str  # From address.state
    bedrooms: int  # From property_details.bedrooms
    bathrooms: float  # From property_details.bathrooms
    property_type: str  # From property_details.property_type
    square_feet: int  # From property_details.square_feet
    
    # Calculated fields
    calculated_price_per_sqft: Optional[float]
    
    # Arrays preserved
    features: List[str]
    images: List[str]
    price_history: Optional[List[Dict[str, Any]]]
    
    # Optional fields
    description: Optional[str]
    virtual_tour_url: Optional[str]
    
    # Silver layer metadata
    silver_processed_at: Optional[datetime]
    processing_version: Optional[str]


class NeighborhoodSilver(BaseModel):
    """Silver tier neighborhood model with nested structures and denormalized fields."""
    # Core fields
    neighborhood_id: str
    name: str
    city: str
    county: str
    state: str
    
    # Nested structures preserved from Bronze
    coordinates: NeighborhoodCoordinates
    characteristics: NeighborhoodCharacteristics
    demographics: NeighborhoodDemographics
    
    # Denormalized fields for common queries (extracted from nested)
    walkability_score: int  # From characteristics.walkability_score
    transit_score: int  # From characteristics.transit_score
    school_rating: int  # From characteristics.school_rating
    population: Optional[int]  # From demographics.population
    median_household_income: Optional[int]  # From demographics.median_household_income
    
    # Arrays preserved
    amenities: List[str]
    lifestyle_tags: List[str]
    
    # Other fields
    description: str
    median_home_price: int
    price_trend: str
    wikipedia_correlations: Optional[Dict[str, Any]]
    
    # Silver layer metadata
    silver_processed_at: Optional[datetime]
    processing_version: Optional[str]


class WikipediaArticleSilver(BaseModel):
    """Silver tier Wikipedia article model."""
    # Core fields (Wikipedia is already mostly flat)
    id: int
    pageid: int
    location_id: int
    title: str
    url: Optional[str]
    extract: Optional[str]
    categories: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    relevance_score: Optional[float]
    depth: Optional[int]
    crawled_at: Optional[str]
    html_file: Optional[str]
    file_hash: Optional[str]
    image_url: Optional[str]
    links_count: Optional[int]
    infobox_data: Optional[str]
    
    # Silver layer metadata
    silver_processed_at: Optional[datetime]
    processing_version: Optional[str]


class DataLoadingMetrics(BaseModel):
    """Metrics for data loading operations."""
    entity_type: str
    total_records: int
    successful_records: int
    failed_records: int
    processing_time_seconds: float
    data_quality_score: float


class ValidationResult(BaseModel):
    """Result of data validation operations."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    record_count: int
    null_counts: Dict[str, int] = Field(default_factory=dict)