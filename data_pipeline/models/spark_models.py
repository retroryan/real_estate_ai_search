"""
Spark models for the data pipeline.

This module contains all Pydantic model definitions that automatically generate
Spark StructType schemas using our custom converter.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from .spark_converter import SparkModel


# ============================================================================
# Property Models
# ============================================================================

class Address(BaseModel):
    """Address structure for properties."""
    street: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None  # Using 'zip' to match source data


class Coordinates(BaseModel):
    """Geographic coordinates."""
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class PropertyDetails(BaseModel):
    """Detailed property characteristics."""
    square_feet: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    property_type: Optional[str] = None
    year_built: Optional[int] = None
    lot_size: Optional[float] = None
    stories: Optional[int] = None
    garage_spaces: Optional[int] = None


class PriceHistory(BaseModel):
    """Price history entry."""
    date: Optional[str] = None
    price: Optional[Decimal] = Field(None, max_digits=12, decimal_places=2)
    event: Optional[str] = None


class Property(SparkModel):
    """Main property model with nested structures."""
    listing_id: str
    neighborhood_id: Optional[str] = None
    address: Optional[Address] = None
    coordinates: Optional[Coordinates] = None
    property_details: Optional[PropertyDetails] = None
    listing_price: Optional[Decimal] = Field(None, max_digits=12, decimal_places=2)
    price_per_sqft: Optional[int] = None
    description: Optional[str] = None
    features: Optional[List[str]] = None
    listing_date: Optional[str] = None
    days_on_market: Optional[int] = None
    virtual_tour_url: Optional[str] = None
    images: Optional[List[str]] = None
    price_history: Optional[List[PriceHistory]] = None


# ============================================================================
# Wikipedia Correlation Models
# ============================================================================

class WikipediaArticleReference(BaseModel):
    """Wikipedia article reference with confidence score."""
    page_id: int
    title: str
    url: str
    confidence: float
    relationship: Optional[str] = None  # e.g., "neighborhood", "park", "landmark", "reference"


class WikipediaGeoReference(BaseModel):
    """Simple Wikipedia reference for geographic entities."""
    page_id: int
    title: str


class ParentGeography(BaseModel):
    """Parent geographic Wikipedia references."""
    city_wiki: WikipediaGeoReference
    state_wiki: WikipediaGeoReference


class WikipediaCorrelations(BaseModel):
    """Container for all Wikipedia correlation data."""
    primary_wiki_article: WikipediaArticleReference
    related_wiki_articles: List[WikipediaArticleReference] = Field(default_factory=list)
    parent_geography: ParentGeography
    generated_by: str
    generated_at: str
    source: str
    updated_by: Optional[str] = None


# ============================================================================
# Neighborhood Models
# ============================================================================

class Demographics(BaseModel):
    """Demographics information for neighborhoods."""
    population: Optional[int] = None
    median_income: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    median_age: Optional[float] = None


class Neighborhood(SparkModel):
    """Neighborhood model with demographics and Wikipedia correlations."""
    neighborhood_id: str
    name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    description: Optional[str] = None
    amenities: Optional[List[str]] = None
    demographics: Optional[Demographics] = None
    wikipedia_correlations: Optional[WikipediaCorrelations] = None  # From graph_metadata in source


# ============================================================================
# Location Model
# ============================================================================

class Location(SparkModel):
    """Location hierarchy model."""
    state: Optional[str] = None
    county: Optional[str] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    location_type: Optional[str] = None
    full_hierarchy: Optional[str] = None
    source_file: Optional[str] = None
    ingested_at: Optional[str] = None  # Using string for timestamp compatibility


# ============================================================================
# Wikipedia Article Model
# ============================================================================

class WikipediaArticle(SparkModel):
    """Wikipedia article model."""
    page_id: int
    title: str
    url: Optional[str] = None
    best_city: Optional[str] = None
    best_state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    short_summary: Optional[str] = None
    long_summary: Optional[str] = None
    key_topics: Optional[str] = None
    relevance_score: Optional[float] = None
    embedding_text: Optional[str] = None
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    embedding_dimension: Optional[int] = None
    ingested_at: Optional[str] = None
    embedded_at: Optional[str] = None


# ============================================================================
# Relationship Model
# ============================================================================

class Relationship(SparkModel):
    """Relationship edge model for graph structures."""
    from_id: str
    to_id: str
    relationship_type: str


# ============================================================================
# Flattened Models for Entity Schema
# ============================================================================

class FlattenedProperty(SparkModel):
    """Flattened property model after transformation."""
    listing_id: str
    neighborhood_id: Optional[str] = None
    neighborhood: Optional[str] = None  # Neighborhood name for demo compatibility
    
    # Flattened address fields
    street: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    
    # Flattened coordinates
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Flattened property details
    square_feet: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    property_type: Optional[str] = None
    year_built: Optional[int] = None
    lot_size: Optional[float] = None
    stories: Optional[int] = None
    garage_spaces: Optional[int] = None
    
    # Direct fields
    listing_price: Optional[Decimal] = Field(None, max_digits=12, decimal_places=2)
    price_per_sqft: Optional[int] = None
    description: Optional[str] = None
    features: Optional[List[str]] = None
    listing_date: Optional[str] = None
    days_on_market: Optional[int] = None
    virtual_tour_url: Optional[str] = None
    images: Optional[List[str]] = None
    price_history: Optional[List[PriceHistory]] = None
    
    # Embedding fields
    embedding: Optional[List[float]] = None
    embedding_text: Optional[str] = None
    embedding_model: Optional[str] = None
    embedding_dimension: Optional[int] = None


class FlattenedNeighborhood(SparkModel):
    """Flattened neighborhood model after transformation."""
    neighborhood_id: str
    name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    description: Optional[str] = None
    amenities: Optional[List[str]] = None
    
    # Flattened demographics
    population: Optional[int] = None
    median_income: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    median_age: Optional[float] = None
    
    # Denormalized Wikipedia correlation fields
    primary_wikipedia_page_id: Optional[int] = None
    primary_wikipedia_title: Optional[str] = None
    primary_wikipedia_confidence: Optional[float] = None
    
    # Full correlations preserved for Elasticsearch nested object
    wikipedia_correlations: Optional[WikipediaCorrelations] = None