"""
Entity-specific schemas using Pydantic for type safety.

Each entity type has its own schema with proper typing,
providing clean, type-safe schemas for each entity.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field
from pyspark.sql.types import (
    ArrayType,
    DecimalType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)


class PropertySchema(BaseModel):
    """Schema for property entities with full type safety."""
    
    # Identity
    listing_id: str = Field(..., description="Unique property listing ID")
    
    # Location
    street: Optional[str] = Field(None, description="Street address")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State code")
    zip_code: Optional[str] = Field(None, description="ZIP code")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    
    # Property details
    property_type: Optional[str] = Field(None, description="Type of property")
    price: Optional[Decimal] = Field(None, ge=0, description="Property price")
    bedrooms: Optional[int] = Field(None, ge=0, le=20)
    bathrooms: Optional[float] = Field(None, ge=0, le=20)
    square_feet: Optional[int] = Field(None, ge=0, le=100000)
    year_built: Optional[int] = Field(None, ge=1800, le=2030)
    lot_size: Optional[int] = Field(None, ge=0)
    
    # Content
    description: Optional[str] = Field(None, max_length=5000)
    features: List[str] = Field(default_factory=list)
    
    # Embedding fields
    embedding_text: Optional[str] = Field(None, description="Text prepared for embedding")
    embedding: Optional[List[float]] = Field(None, description="Embedding vector")
    embedding_model: Optional[str] = Field(None, description="Model used for embedding")
    embedding_dimension: Optional[int] = Field(None, description="Embedding vector dimension")
    
    # Metadata
    data_quality_score: Optional[float] = Field(None, ge=0, le=1)
    ingested_at: datetime = Field(default_factory=datetime.now)
    embedded_at: Optional[datetime] = Field(None)
    
    @staticmethod
    def get_spark_schema() -> StructType:
        """Get Spark schema for property data."""
        return StructType([
            StructField("listing_id", StringType(), False),
            StructField("street", StringType(), True),
            StructField("city", StringType(), False),
            StructField("state", StringType(), False),
            StructField("zip_code", StringType(), True),
            StructField("latitude", DoubleType(), True),
            StructField("longitude", DoubleType(), True),
            StructField("property_type", StringType(), True),
            StructField("price", DecimalType(12, 2), True),
            StructField("bedrooms", IntegerType(), True),
            StructField("bathrooms", DoubleType(), True),
            StructField("square_feet", IntegerType(), True),
            StructField("year_built", IntegerType(), True),
            StructField("lot_size", IntegerType(), True),
            StructField("description", StringType(), True),
            StructField("features", ArrayType(StringType()), True),
            StructField("embedding_text", StringType(), True),
            StructField("embedding", ArrayType(DoubleType()), True),
            StructField("embedding_model", StringType(), True),
            StructField("embedding_dimension", IntegerType(), True),
            StructField("data_quality_score", DoubleType(), True),
            StructField("ingested_at", TimestampType(), False),
            StructField("embedded_at", TimestampType(), True),
        ])


class NeighborhoodSchema(BaseModel):
    """Schema for neighborhood entities with full type safety."""
    
    # Identity
    neighborhood_id: str = Field(..., description="Unique neighborhood ID")
    name: str = Field(..., description="Neighborhood name")
    
    # Location
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State code")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    boundary_polygon: Optional[str] = Field(None, description="WKT polygon string")
    
    # Demographics
    population: Optional[int] = Field(None, ge=0)
    median_income: Optional[Decimal] = Field(None, ge=0)
    median_age: Optional[float] = Field(None, ge=0, le=150)
    
    # Content
    description: Optional[str] = Field(None, max_length=5000)
    amenities: List[str] = Field(default_factory=list)
    points_of_interest: List[str] = Field(default_factory=list)
    
    # Embedding fields
    embedding_text: Optional[str] = Field(None, description="Text prepared for embedding")
    embedding: Optional[List[float]] = Field(None, description="Embedding vector")
    embedding_model: Optional[str] = Field(None, description="Model used for embedding")
    embedding_dimension: Optional[int] = Field(None, description="Embedding vector dimension")
    
    # Metadata
    data_quality_score: Optional[float] = Field(None, ge=0, le=1)
    ingested_at: datetime = Field(default_factory=datetime.now)
    embedded_at: Optional[datetime] = Field(None)
    
    @staticmethod
    def get_spark_schema() -> StructType:
        """Get Spark schema for neighborhood data."""
        return StructType([
            StructField("neighborhood_id", StringType(), False),
            StructField("name", StringType(), False),
            StructField("city", StringType(), False),
            StructField("state", StringType(), False),
            StructField("latitude", DoubleType(), True),
            StructField("longitude", DoubleType(), True),
            StructField("boundary_polygon", StringType(), True),
            StructField("population", IntegerType(), True),
            StructField("median_income", DecimalType(12, 2), True),
            StructField("median_age", DoubleType(), True),
            StructField("description", StringType(), True),
            StructField("amenities", ArrayType(StringType()), True),
            StructField("points_of_interest", ArrayType(StringType()), True),
            StructField("embedding_text", StringType(), True),
            StructField("embedding", ArrayType(DoubleType()), True),
            StructField("embedding_model", StringType(), True),
            StructField("embedding_dimension", IntegerType(), True),
            StructField("data_quality_score", DoubleType(), True),
            StructField("ingested_at", TimestampType(), False),
            StructField("embedded_at", TimestampType(), True),
        ])


class WikipediaArticleSchema(BaseModel):
    """Schema for Wikipedia articles with full type safety."""
    
    # Identity
    page_id: int = Field(..., description="Wikipedia page ID")
    title: str = Field(..., description="Article title")
    url: Optional[str] = Field(None, description="Wikipedia URL")
    
    # Location references
    best_city: Optional[str] = Field(None, description="Primary city mentioned")
    best_state: Optional[str] = Field(None, description="Primary state mentioned")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    
    # Content
    short_summary: str = Field(..., description="Brief summary for preview")
    long_summary: str = Field(..., description="Full summary for embedding")
    key_topics: Optional[str] = Field(None, description="Key topics covered")
    
    # Quality metrics
    relevance_score: Optional[float] = Field(None, ge=0, le=1)
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    
    # Embedding fields (no chunking for Wikipedia)
    embedding_text: Optional[str] = Field(None, description="Text prepared for embedding")
    embedding: Optional[List[float]] = Field(None, description="Embedding vector")
    embedding_model: Optional[str] = Field(None, description="Model used for embedding")
    embedding_dimension: Optional[int] = Field(None, description="Embedding vector dimension")
    
    # Metadata
    ingested_at: datetime = Field(default_factory=datetime.now)
    embedded_at: Optional[datetime] = Field(None)
    
    @staticmethod
    def get_spark_schema() -> StructType:
        """Get Spark schema for Wikipedia data."""
        return StructType([
            StructField("page_id", LongType(), False),
            StructField("title", StringType(), False),
            StructField("url", StringType(), True),
            StructField("best_city", StringType(), True),
            StructField("best_state", StringType(), True),
            StructField("latitude", DoubleType(), True),
            StructField("longitude", DoubleType(), True),
            StructField("short_summary", StringType(), False),
            StructField("long_summary", StringType(), False),
            StructField("key_topics", StringType(), True),
            StructField("relevance_score", DoubleType(), True),
            StructField("confidence_score", DoubleType(), True),
            StructField("embedding_text", StringType(), True),
            StructField("embedding", ArrayType(DoubleType()), True),
            StructField("embedding_model", StringType(), True),
            StructField("embedding_dimension", IntegerType(), True),
            StructField("ingested_at", TimestampType(), False),
            StructField("embedded_at", TimestampType(), True),
        ])