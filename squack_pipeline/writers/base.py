"""Base writer interface for data output operations."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
import time

import duckdb

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.models import EntityType
from squack_pipeline.models.writer_interface import (
    WriteRequest,
    WriteResponse,
    WriteMetrics,
    ValidationResult
)
from squack_pipeline.utils.logging import PipelineLogger


class BaseWriter(ABC):
    """Abstract base class for all data writers with standardized interface."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize the writer with pipeline settings."""
        self.settings = settings
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        self.connection: Optional[duckdb.DuckDBPyConnection] = None
    
    def set_connection(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Set the DuckDB connection for the writer."""
        self.connection = connection
        self.logger.debug("DuckDB connection established")
    
    @abstractmethod
    def write(self, request: WriteRequest) -> WriteResponse:
        """Write data based on the request.
        
        Args:
            request: Write request with entity type, table name, and options
            
        Returns:
            WriteResponse with success status, metrics, and validation
        """
        pass
    
    @abstractmethod
    def validate(self, entity_type: EntityType, destination: str) -> ValidationResult:
        """Validate written output meets requirements.
        
        Args:
            entity_type: Type of entity that was written
            destination: Where the data was written (file path or index name)
            
        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        pass
    
    @abstractmethod
    def get_metrics(self, entity_type: EntityType, destination: str) -> WriteMetrics:
        """Get metrics for written data.
        
        Args:
            entity_type: Type of entity
            destination: Where the data was written
            
        Returns:
            WriteMetrics with performance and size information
        """
        pass
    
    def write_with_validation(self, request: WriteRequest) -> WriteResponse:
        """Write data and validate the output.
        
        This is a convenience method that combines write and validate.
        
        Args:
            request: Write request
            
        Returns:
            WriteResponse with validation results included
        """
        # Perform the write operation
        response = self.write(request)
        
        # If write was successful, perform validation
        if response.success and self.settings.validate_output:
            validation = self.validate(response.entity_type, response.destination)
            response.validation = validation
            
            # Update success status based on validation
            if not validation.is_valid:
                response.success = False
                response.error = f"Validation failed: {', '.join(validation.errors)}"
        
        return response
    
    def cleanup(self) -> None:
        """Clean up resources. Override in subclasses if needed."""
        pass


