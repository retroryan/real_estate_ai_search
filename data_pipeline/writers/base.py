"""
Base classes for data writers.

This module provides the abstract base class for all data writers and the base
configuration model using Pydantic for type safety and validation.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

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


class DataWriter(ABC):
    """
    Abstract base class for data writers.
    
    All concrete writers must implement the required methods for validating
    connections and writing DataFrames to their respective destinations.
    """
    
    def __init__(self, config: WriterConfig):
        """
        Initialize the data writer.
        
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
    def write(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write a DataFrame to the destination.
        
        Args:
            df: DataFrame to write
            metadata: Additional metadata about the data being written
            
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
        return self.config.enabled
    
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