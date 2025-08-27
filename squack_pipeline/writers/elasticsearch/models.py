"""Pydantic models for Elasticsearch writer."""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Supported entity types for Elasticsearch indexing."""
    PROPERTIES = "properties"
    NEIGHBORHOODS = "neighborhoods"
    WIKIPEDIA = "wikipedia"


class WriteResult(BaseModel):
    """Result of an Elasticsearch write operation."""
    
    success: bool = Field(description="Whether the write operation succeeded")
    entity_type: EntityType = Field(description="Type of entity written")
    record_count: int = Field(description="Number of records successfully written")
    failed_count: int = Field(default=0, description="Number of records that failed")
    index_name: str = Field(description="Elasticsearch index name")
    error: Optional[str] = Field(default=None, description="Error message if operation failed")
    duration_seconds: Optional[float] = Field(default=None, description="Operation duration")
    
    def is_successful(self) -> bool:
        """Check if the write was completely successful."""
        return self.success and self.failed_count == 0


class BulkOperation(BaseModel):
    """Configuration for a bulk write operation."""
    
    entity_type: EntityType = Field(description="Type of entity being written")
    index_name: str = Field(description="Target index name")
    records: List[Dict[str, Any]] = Field(description="Records to write")
    id_field: str = Field(description="Field to use as document ID")
    chunk_size: int = Field(default=500, ge=1, description="Bulk operation chunk size")
    
    def get_record_count(self) -> int:
        """Get the total number of records."""
        return len(self.records)


class TransformationConfig(BaseModel):
    """Configuration for data transformations."""
    
    convert_decimals: bool = Field(
        default=True,
        description="Convert Decimal types to float"
    )
    create_geo_points: bool = Field(
        default=True,
        description="Create geo_point from lat/lon fields"
    )
    flatten_nested: bool = Field(
        default=False,
        description="Flatten nested structures"
    )
    exclude_fields: List[str] = Field(
        default_factory=list,
        description="Fields to exclude from indexing"
    )
    
    def should_exclude(self, field_name: str) -> bool:
        """Check if a field should be excluded."""
        return field_name in self.exclude_fields


class IndexMapping(BaseModel):
    """Index mapping configuration for an entity type."""
    
    entity_type: EntityType = Field(description="Entity type")
    id_field: str = Field(description="Document ID field")
    geo_fields: Optional[Dict[str, str]] = Field(
        default=None,
        description="Mapping of geo_point field to lat/lon source fields"
    )
    text_fields: List[str] = Field(
        default_factory=list,
        description="Fields to treat as text for full-text search"
    )
    keyword_fields: List[str] = Field(
        default_factory=list,
        description="Fields to treat as keywords for exact match"
    )
    
    @classmethod
    def for_properties(cls) -> "IndexMapping":
        """Create mapping for property entities."""
        return cls(
            entity_type=EntityType.PROPERTIES,
            id_field="listing_id",
            geo_fields={"location": {"lat": "latitude", "lon": "longitude"}},
            text_fields=["description", "property_type", "city", "state"],
            keyword_fields=["listing_id", "status", "zip_code"]
        )
    
    @classmethod
    def for_neighborhoods(cls) -> "IndexMapping":
        """Create mapping for neighborhood entities."""
        return cls(
            entity_type=EntityType.NEIGHBORHOODS,
            id_field="neighborhood_id",
            geo_fields={"location": {"lat": "latitude", "lon": "longitude"}},
            text_fields=["name", "description", "city"],
            keyword_fields=["neighborhood_id", "state"]
        )
    
    @classmethod
    def for_wikipedia(cls) -> "IndexMapping":
        """Create mapping for Wikipedia entities."""
        return cls(
            entity_type=EntityType.WIKIPEDIA,
            id_field="page_id",
            geo_fields={"location": {"lat": "latitude", "lon": "longitude"}},
            text_fields=["title", "text", "summary"],
            keyword_fields=["page_id", "categories"]
        )