"""
Centralized configuration for all demo queries.

This module provides type-safe configuration using Pydantic models,
eliminating magic strings and centralizing all demo-related constants.
"""

from typing import List
from pydantic import BaseModel, Field

from ..indexer.enums import IndexName, FieldName


class PropertyDemoDefaults(BaseModel):
    """Default values for property demos."""
    query_text: str = Field(default="modern home with pool", description="Default search text")
    property_type: str = Field(default="single-family", description="Default property type")
    min_price: float = Field(default=300000.0, description="Default minimum price")
    max_price: float = Field(default=800000.0, description="Default maximum price")
    min_bedrooms: int = Field(default=3, description="Default minimum bedrooms")
    min_bathrooms: float = Field(default=2.0, description="Default minimum bathrooms")
    geo_center_lat: float = Field(default=37.7749, description="Default geo search center latitude (SF)")
    geo_center_lon: float = Field(default=-122.4194, description="Default geo search center longitude (SF)")
    geo_radius_km: int = Field(default=5, description="Default geo search radius in km")


class AggregationDemoDefaults(BaseModel):
    """Default values for aggregation demos."""
    neighborhood_size: int = Field(default=20, description="Default max neighborhoods for stats")
    price_interval: int = Field(default=100000, description="Default price histogram bucket size")
    min_price: float = Field(default=0.0, description="Default minimum price for distribution")
    max_price: float = Field(default=2000000.0, description="Default maximum price for distribution")
    top_properties_count: int = Field(default=5, description="Number of top properties to show")
    max_buckets: int = Field(default=10, description="Maximum buckets for terms aggregations")
    percentiles: List[int] = Field(default=[25, 50, 75, 90, 95, 99], description="Percentile levels")


class AdvancedDemoDefaults(BaseModel):
    """Default values for advanced demos."""
    semantic_similarity_size: int = Field(default=10, description="Default results for similarity search")
    multi_entity_size_per_type: int = Field(default=5, description="Default results per entity type")
    wikipedia_search_size: int = Field(default=10, description="Default Wikipedia search results")
    wikipedia_default_city: str = Field(default="San Francisco", description="Default city for Wikipedia search")
    wikipedia_default_state: str = Field(default="CA", description="Default state for Wikipedia search")


class DisplayDefaults(BaseModel):
    """Default values for display formatting."""
    histogram_bar_max_width: int = Field(default=50, description="Max width for histogram bars")
    price_label_width: int = Field(default=15, description="Width for price labels")
    table_max_rows: int = Field(default=10, description="Maximum rows to display in tables")
    results_per_page: int = Field(default=20, description="Default results per page")


class DemoIndexConfig(BaseModel):
    """Index configuration for demos."""
    # Using enum values for type safety
    properties_index: str = Field(default=IndexName.PROPERTIES, description="Properties index name")
    neighborhoods_index: str = Field(default=IndexName.NEIGHBORHOODS, description="Neighborhoods index name") 
    wikipedia_index: str = Field(default=IndexName.WIKIPEDIA, description="Wikipedia index name")
    property_relationships_index: str = Field(default=IndexName.PROPERTY_RELATIONSHIPS, description="Denormalized relationships index name")


class DemoFieldConfig(BaseModel):
    """Field name configuration for demos."""
    # Using enum values for type safety
    listing_id: str = Field(default=FieldName.LISTING_ID, description="Listing ID field")
    neighborhood_id: str = Field(default=FieldName.NEIGHBORHOOD_ID, description="Neighborhood ID field")
    price: str = Field(default=FieldName.PRICE, description="Price field")
    bedrooms: str = Field(default=FieldName.BEDROOMS, description="Bedrooms field")
    bathrooms: str = Field(default=FieldName.BATHROOMS, description="Bathrooms field")
    property_type: str = Field(default=FieldName.PROPERTY_TYPE, description="Property type field")
    square_feet: str = Field(default=FieldName.SQUARE_FEET, description="Square feet field")
    price_per_sqft: str = Field(default=FieldName.PRICE_PER_SQFT, description="Price per sqft field")
    address_city: str = Field(default=FieldName.ADDRESS_CITY, description="Address city field")
    address_state: str = Field(default=FieldName.ADDRESS_STATE, description="Address state field")
    address_location: str = Field(default=FieldName.ADDRESS_LOCATION, description="Address location field")
    description: str = Field(default=FieldName.DESCRIPTION, description="Description field")


class DemoConfiguration(BaseModel):
    """Master configuration for all demo queries."""
    
    # Sub-configurations
    property_defaults: PropertyDemoDefaults = Field(default_factory=PropertyDemoDefaults)
    aggregation_defaults: AggregationDemoDefaults = Field(default_factory=AggregationDemoDefaults)
    advanced_defaults: AdvancedDemoDefaults = Field(default_factory=AdvancedDemoDefaults)
    display_defaults: DisplayDefaults = Field(default_factory=DisplayDefaults)
    indexes: DemoIndexConfig = Field(default_factory=DemoIndexConfig)
    fields: DemoFieldConfig = Field(default_factory=DemoFieldConfig)
    
    class Config:
        """Pydantic configuration."""
        frozen = True  # Make immutable
        extra = "forbid"  # Prevent extra fields


# Global instance - singleton pattern for configuration
demo_config = DemoConfiguration()