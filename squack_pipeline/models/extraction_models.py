"""Pydantic models for data extraction from DuckDB."""

from typing import List, Optional, Any
from decimal import Decimal
from datetime import datetime
import json
from pydantic import BaseModel, Field, field_validator, ConfigDict


class ExtractedRecord(BaseModel):
    """Base model for records extracted from DuckDB.
    
    This model handles automatic conversion of Decimal types to float
    and provides a base for all extracted records.
    """
    
    model_config = ConfigDict(
        extra='allow',  # Allow extra fields from DuckDB
        validate_assignment=True,
        arbitrary_types_allowed=False
    )
    
    @field_validator('*', mode='before')
    @classmethod
    def convert_types_for_json(cls, value: Any) -> Any:
        """Convert types for JSON serialization.
        
        - Decimal to float
        - datetime to ISO string
        - Lists with Decimals to lists with floats
        """
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, list):
            # Convert any Decimals in lists to floats
            return [float(v) if isinstance(v, Decimal) else v for v in value]
        return value
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for Elasticsearch."""
        return self.model_dump(exclude_none=True)


class PropertyExtractedRecord(ExtractedRecord):
    """Property record extracted from DuckDB."""
    
    listing_id: str = Field(description="Unique listing identifier")
    neighborhood_id: Optional[str] = Field(default=None)
    price: Optional[float] = Field(default=None)
    price_per_sqft: Optional[float] = Field(default=None)
    calculated_price_per_sqft: Optional[float] = Field(default=None)
    days_on_market: Optional[int] = Field(default=None)
    
    # Nested structures - these come as dicts from DuckDB
    address: Optional[dict] = Field(default=None)
    property_details: Optional[dict] = Field(default=None)
    coordinates: Optional[dict] = Field(default=None)
    parking: Optional[dict] = Field(default=None)
    
    # Basic fields
    city: Optional[str] = Field(default=None)
    state: Optional[str] = Field(default=None)
    bedrooms: Optional[int] = Field(default=None)
    bathrooms: Optional[float] = Field(default=None)
    property_type: Optional[str] = Field(default=None)
    square_feet: Optional[int] = Field(default=None)
    
    # Arrays
    location: Optional[List[float]] = Field(default=None)
    features: Optional[List[str]] = Field(default=None)
    images: Optional[List[str]] = Field(default=None)
    price_history: Optional[List[dict]] = Field(default=None)
    
    # Text fields
    description: Optional[str] = Field(default=None)
    virtual_tour_url: Optional[str] = Field(default=None)
    
    # Metadata
    entity_type: str = Field(default="property")
    gold_processed_at: Optional[str] = Field(default=None)
    processing_version: Optional[str] = Field(default=None)
    
    # Embeddings
    embedding: Optional[List[float]] = Field(default=None)
    embedding_model: Optional[str] = Field(default=None)
    embedding_dimension: Optional[int] = Field(default=None)


class NeighborhoodExtractedRecord(ExtractedRecord):
    """Neighborhood record extracted from DuckDB."""
    
    neighborhood_id: str = Field(description="Unique neighborhood identifier")
    name: str = Field(description="Neighborhood name")
    city: str = Field(description="City name")
    state: str = Field(description="State code")
    
    # Statistics
    population: Optional[int] = Field(default=None)
    median_income: Optional[float] = Field(default=None)
    median_home_value: Optional[float] = Field(default=None)
    
    # Nested structures
    demographics: Optional[dict] = Field(default=None)
    boundaries: Optional[dict] = Field(default=None)
    
    # Arrays
    schools: Optional[List[dict]] = Field(default=None)
    amenities: Optional[List[str]] = Field(default=None)
    
    # Text
    description: Optional[str] = Field(default=None)
    
    # Metadata
    entity_type: str = Field(default="neighborhood")
    gold_processed_at: Optional[str] = Field(default=None)
    
    # Embeddings
    embedding: Optional[List[float]] = Field(default=None)
    embedding_model: Optional[str] = Field(default=None)
    embedding_dimension: Optional[int] = Field(default=None)


class WikipediaExtractedRecord(ExtractedRecord):
    """Wikipedia record extracted from DuckDB."""
    
    page_id: int = Field(description="Wikipedia page ID")
    title: str = Field(description="Article title")
    
    # Content
    content: Optional[str] = Field(default=None)
    summary: Optional[str] = Field(default=None)
    
    # Metadata
    entity_type: str = Field(default="wikipedia")
    article_filename: Optional[str] = Field(default=None)
    content_loaded: Optional[bool] = Field(default=None)
    gold_processed_at: Optional[str] = Field(default=None)
    
    # Arrays
    categories: Optional[List[str]] = Field(default=None)
    links: Optional[List[str]] = Field(default=None)
    
    # Embeddings
    embedding: Optional[List[float]] = Field(default=None)
    embedding_model: Optional[str] = Field(default=None)
    embedding_dimension: Optional[int] = Field(default=None)
    
    @field_validator('categories', 'links', mode='before')
    @classmethod
    def parse_json_arrays(cls, value: Any) -> Any:
        """Parse JSON string arrays that come from DuckDB."""
        if isinstance(value, str):
            # Handle JSON array strings
            if value.startswith('['):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return None
            # Handle plain text strings - convert to None for categories/links
            # These are likely malformed data that should be filtered out
            elif value.strip():
                return None
        return value


class ExtractionResult(BaseModel):
    """Result of extracting records from DuckDB."""
    
    model_config = ConfigDict(extra='forbid')
    
    records: List[ExtractedRecord] = Field(description="Extracted records")
    embeddings_count: int = Field(default=0, ge=0, description="Number of records with embeddings")
    total_count: int = Field(default=0, ge=0, description="Total number of records")
    entity_type: Optional[str] = Field(default=None, description="Type of entities extracted")