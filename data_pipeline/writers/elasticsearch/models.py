"""
Pydantic models for Elasticsearch writer functionality.

This module defines type-safe models for all Elasticsearch operations,
transformations, and configurations.
"""

from enum import Enum
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field, field_validator


class ElasticsearchWriteMode(str, Enum):
    """Supported Elasticsearch write modes."""
    APPEND = "append"
    OVERWRITE = "overwrite"
    UPSERT = "upsert"


class EntityType(str, Enum):
    """Supported entity types."""
    PROPERTIES = "properties"
    NEIGHBORHOODS = "neighborhoods"
    WIKIPEDIA = "wikipedia"


class IndexSettings(BaseModel):
    """Elasticsearch index settings configuration."""
    
    name: str = Field(description="Index name")
    entity_type: EntityType = Field(description="Entity type this index handles")
    id_field: str = Field(description="Field to use as document ID")
    write_mode: ElasticsearchWriteMode = Field(
        default=ElasticsearchWriteMode.APPEND,
        description="Write mode for this index"
    )
    enable_geo_point: bool = Field(
        default=True,
        description="Whether to create geo_point from lat/lng fields"
    )
    
    @field_validator("name")
    @classmethod
    def validate_index_name(cls, v: str) -> str:
        """Validate index name follows Elasticsearch conventions."""
        if not v:
            raise ValueError("Index name cannot be empty")
        if not v.islower():
            raise ValueError("Index name must be lowercase")
        return v


class SchemaTransformation(BaseModel):
    """Configuration for DataFrame schema transformations."""
    
    convert_decimals: bool = Field(
        default=True,
        description="Convert decimal types to double for ES compatibility"
    )
    add_geo_point: bool = Field(
        default=True,
        description="Add geo_point field from latitude/longitude"
    )
    latitude_field: str = Field(
        default="latitude",
        description="Name of latitude field"
    )
    longitude_field: str = Field(
        default="longitude",
        description="Name of longitude field"
    )
    excluded_fields: Set[str] = Field(
        default_factory=set,
        description="Fields to exclude from writing"
    )


class WriteOperation(BaseModel):
    """Configuration for a specific write operation."""
    
    index_settings: IndexSettings = Field(description="Index configuration")
    schema_transform: SchemaTransformation = Field(
        default_factory=SchemaTransformation,
        description="Schema transformation settings"
    )
    record_count: Optional[int] = Field(
        default=None,
        description="Expected record count for validation"
    )
    
    def get_spark_options(self) -> Dict[str, str]:
        """Get Spark write options for Elasticsearch."""
        return {
            "es.resource": self.index_settings.name,
            "es.mapping.id": "id",
        }


class WriteResult(BaseModel):
    """Result of an Elasticsearch write operation."""
    
    success: bool = Field(description="Whether write was successful")
    index_name: str = Field(description="Target index name")
    entity_type: EntityType = Field(description="Entity type written")
    record_count: int = Field(description="Number of records written")
    fields_written: List[str] = Field(description="List of fields written to ES")
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if write failed"
    )
    transformation_applied: bool = Field(
        default=False,
        description="Whether schema transformation was applied"
    )
    
    def is_success(self) -> bool:
        """Check if operation was successful."""
        return self.success and self.error_message is None


class ElasticsearchWriterSettings(BaseModel):
    """Complete settings for Elasticsearch writer."""
    
    index_prefix: str = Field(description="Prefix for all indices")
    default_write_mode: ElasticsearchWriteMode = Field(
        default=ElasticsearchWriteMode.APPEND,
        description="Default write mode"
    )
    batch_size: int = Field(
        default=1000,
        gt=0,
        description="Batch size for write operations"
    )
    enable_schema_transformation: bool = Field(
        default=True,
        description="Enable automatic schema transformations"
    )
    
    def create_index_settings(self, entity_type: EntityType) -> IndexSettings:
        """Create index settings for a specific entity type."""
        entity_configs = {
            EntityType.PROPERTIES: {
                "id_field": "listing_id",
                "enable_geo_point": True,
            },
            EntityType.NEIGHBORHOODS: {
                "id_field": "neighborhood_id", 
                "enable_geo_point": True,
            },
            EntityType.WIKIPEDIA: {
                "id_field": "page_id",
                "enable_geo_point": True,
            },
        }
        
        config = entity_configs[entity_type]
        
        return IndexSettings(
            name=f"{self.index_prefix}_{entity_type.value}",
            entity_type=entity_type,
            id_field=config["id_field"],
            write_mode=self.default_write_mode,
            enable_geo_point=config["enable_geo_point"],
        )