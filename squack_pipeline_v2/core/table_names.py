"""Type-safe table name definitions using Pydantic."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Literal


class TableNames(BaseModel):
    """Centralized, type-safe table name definitions."""
    
    model_config = ConfigDict(frozen=True)
    
    # Bronze layer tables
    bronze_properties: str = Field(default="bronze_properties", description="Bronze properties table")
    bronze_neighborhoods: str = Field(default="bronze_neighborhoods", description="Bronze neighborhoods table")
    bronze_wikipedia: str = Field(default="bronze_wikipedia", description="Bronze Wikipedia table")
    
    # Silver layer tables
    silver_properties: str = Field(default="silver_properties", description="Silver properties table")
    silver_neighborhoods: str = Field(default="silver_neighborhoods", description="Silver neighborhoods table")
    silver_wikipedia: str = Field(default="silver_wikipedia", description="Silver Wikipedia table")
    
    # Gold layer tables
    gold_properties: str = Field(default="gold_properties", description="Gold properties table")
    gold_neighborhoods: str = Field(default="gold_neighborhoods", description="Gold neighborhoods table")
    gold_wikipedia: str = Field(default="gold_wikipedia", description="Gold Wikipedia table")
    
    # Embedding tables
    embeddings_properties: str = Field(default="embeddings_properties", description="Property embeddings table")
    embeddings_neighborhoods: str = Field(default="embeddings_neighborhoods", description="Neighborhood embeddings table")
    embeddings_wikipedia: str = Field(default="embeddings_wikipedia", description="Wikipedia embeddings table")


class EntityType(BaseModel):
    """Type-safe entity type definition."""
    
    model_config = ConfigDict(frozen=True)
    
    name: Literal["property", "neighborhood", "wikipedia"] = Field(description="Entity type name")
    bronze_table: str = Field(description="Bronze table name")
    silver_table: str = Field(description="Silver table name")
    gold_table: str = Field(description="Gold table name")
    embeddings_table: str = Field(description="Embeddings table name")


class EntityTypes(BaseModel):
    """Collection of all entity types."""
    
    model_config = ConfigDict(frozen=True)
    
    property: EntityType = Field(
        default=EntityType(
            name="property",
            bronze_table="bronze_properties",
            silver_table="silver_properties",
            gold_table="gold_properties",
            embeddings_table="embeddings_properties"
        )
    )
    
    neighborhood: EntityType = Field(
        default=EntityType(
            name="neighborhood",
            bronze_table="bronze_neighborhoods",
            silver_table="silver_neighborhoods",
            gold_table="gold_neighborhoods",
            embeddings_table="embeddings_neighborhoods"
        )
    )
    
    wikipedia: EntityType = Field(
        default=EntityType(
            name="wikipedia",
            bronze_table="bronze_wikipedia",
            silver_table="silver_wikipedia",
            gold_table="gold_wikipedia",
            embeddings_table="embeddings_wikipedia"
        )
    )
    
    def get_entity(self, name: str) -> EntityType:
        """Get entity type by name.
        
        Args:
            name: Entity type name
            
        Returns:
            EntityType configuration
            
        Raises:
            ValueError: If entity type not found
        """
        if name == "property":
            return self.property
        elif name == "neighborhood":
            return self.neighborhood
        elif name == "wikipedia":
            return self.wikipedia
        else:
            raise ValueError(f"Unknown entity type: {name}")
    
    def all_entities(self) -> list[EntityType]:
        """Get all entity types.
        
        Returns:
            List of all entity types
        """
        return [self.property, self.neighborhood, self.wikipedia]


# Global instance for easy access
TABLE_NAMES = TableNames()
ENTITY_TYPES = EntityTypes()