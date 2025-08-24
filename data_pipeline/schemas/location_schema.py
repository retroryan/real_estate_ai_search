"""
Location entity schema using Pydantic for type safety.

This module defines the schema for location reference data with proper typing,
providing clean, type-safe schema for geographic hierarchy.
"""

from typing import Optional

from pydantic import BaseModel, Field
from pyspark.sql.types import (
    StringType,
    StructField,
    StructType,
    TimestampType,
)


class LocationSchema(BaseModel):
    """Schema for location entities with geographic hierarchy."""
    
    # Geographic hierarchy - all optional since locations can be at different levels
    state: Optional[str] = Field(None, description="State name or abbreviation")
    county: Optional[str] = Field(None, description="County name")
    city: Optional[str] = Field(None, description="City name") 
    neighborhood: Optional[str] = Field(None, description="Neighborhood name")
    
    # Derived fields
    location_type: Optional[str] = Field(None, description="Type of location (state, county, city, neighborhood)")
    full_hierarchy: Optional[str] = Field(None, description="Complete geographic path")
    
    # Metadata
    source_file: Optional[str] = Field(None, description="Source file path")
    ingested_at: Optional[str] = Field(None, description="Ingestion timestamp")


def get_location_spark_schema() -> StructType:
    """
    Get Spark schema for location data.
    
    Returns:
        StructType defining location data schema for Spark
    """
    return StructType([
        StructField("state", StringType(), True),
        StructField("county", StringType(), True), 
        StructField("city", StringType(), True),
        StructField("neighborhood", StringType(), True),
        StructField("location_type", StringType(), True),
        StructField("full_hierarchy", StringType(), True),
        StructField("source_file", StringType(), True),
        StructField("ingested_at", TimestampType(), True),
    ])