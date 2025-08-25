"""
Base classes for entity-specific data writers.

This module provides the abstract base class for all data writers with
entity-specific write methods and Pydantic models for type safety.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional

from pydantic import BaseModel, Field
from pyspark.sql import DataFrame


class WriterConfig(BaseModel):
    """Base configuration for all data writers."""
    
    enabled: bool = Field(
        default=True,
        description="Whether this writer is enabled"
    )
    batch_size: int = Field(
        default=1000,
        gt=0,
        description="Batch size for write operations"
    )
    clear_before_write: bool = Field(
        default=True,
        description="Clear existing data before writing (for demo purposes)"
    )


class EntityWriter(ABC):
    """
    Abstract base class for entity-specific data writers.
    
    All concrete writers must implement entity-specific write methods
    for properties, neighborhoods, and wikipedia data.
    """
    
    def __init__(self, config: WriterConfig):
        """
        Initialize the entity writer.
        
        Args:
            config: Writer configuration
        """
        self.config = config
        self._validated = False
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """
        Validate the connection to the destination.
        
        Returns:
            True if connection is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def write_properties(self, df: DataFrame) -> bool:
        """
        Write property data to the destination.
        
        Args:
            df: Property DataFrame
            
        Returns:
            True if write was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def write_neighborhoods(self, df: DataFrame) -> bool:
        """
        Write neighborhood data to the destination.
        
        Args:
            df: Neighborhood DataFrame
            
        Returns:
            True if write was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def write_wikipedia(self, df: DataFrame) -> bool:
        """
        Write Wikipedia data to the destination.
        
        Args:
            df: Wikipedia DataFrame
            
        Returns:
            True if write was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        pass
    
    def is_enabled(self) -> bool:
        """
        Check if this writer is enabled.
        
        Returns:
            True if writer is enabled
        """
        # Default implementation - always enabled if instantiated
        # Subclasses can override this if they have specific enable/disable logic
        return True
    
    def write_relationships(self, relationships: Dict[str, DataFrame]) -> bool:
        """
        Write relationship DataFrames to the destination.
        
        This is an optional method that writers can override if they support
        relationship storage (e.g., graph databases). Writers that don't support
        relationships can ignore this method.
        
        Args:
            relationships: Dictionary of relationship name to DataFrame
            
        Returns:
            True if all writes were successful, False otherwise
        """
        # Default implementation: no-op for writers that don't support relationships
        return True
    
    def supports_relationships(self) -> bool:
        """
        Check if this writer supports relationship storage.
        
        Returns:
            True if writer supports relationships, False otherwise
        """
        # Default: most writers don't support relationships
        return False
    
    def get_entity_path(self, entity_type: str) -> Optional[str]:
        """
        Get the output path for a specific entity type.
        
        Args:
            entity_type: Type of entity (properties, neighborhoods, wikipedia)
            
        Returns:
            Path string for the entity output, or None if not applicable
        """
        # Default implementation returns None
        # Writers that use file paths can override this
        return None
    
    def clear_entity_data(self, entity_type: str) -> bool:
        """
        Clear existing data for a specific entity type.
        
        Args:
            entity_type: Type of entity to clear
            
        Returns:
            True if successful or not applicable, False if failed
        """
        # Default implementation is no-op
        # Writers that support clearing can override this
        return True