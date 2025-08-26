"""
Base document builder for search pipeline.

Provides abstract base class and common utilities for transforming
DataFrames into search documents with field name standardization.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from pyspark.sql import DataFrame
from pydantic import BaseModel

# Import the FieldMapper from data_pipeline
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from data_pipeline.transformers.field_mapper import FieldMapper, FieldMappingResult
except ImportError:
    FieldMapper = None
    FieldMappingResult = None

logger = logging.getLogger(__name__)


class BaseDocumentBuilder(ABC):
    """
    Abstract base class for document builders.
    
    Each entity type should have its own builder that inherits from this class
    and implements the transform method. Includes field name standardization
    using FieldMapper.
    """
    
    def __init__(self, field_mapper_config_path: Optional[str] = None):
        """
        Initialize the document builder.
        
        Args:
            field_mapper_config_path: Optional path to field mapping configuration.
                                    If None, uses default configuration.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.field_mapper = None
        
        # Initialize field mapper if available
        if FieldMapper is not None:
            try:
                self.field_mapper = FieldMapper(field_mapper_config_path)
                self.logger.info("Field mapper initialized successfully")
            except Exception as e:
                self.logger.warning(f"Could not initialize field mapper: {e}")
                self.field_mapper = None
        else:
            self.logger.warning("FieldMapper not available - field mapping will be skipped")
        
    @abstractmethod
    def transform(self, df: DataFrame) -> List[BaseModel]:
        """
        Transform a DataFrame into a list of document models.
        
        Args:
            df: Spark DataFrame containing entity data
            
        Returns:
            List of Pydantic document models
            
        Raises:
            ValueError: If DataFrame is invalid or transformation fails
        """
        pass
    
    def validate_dataframe(self, df: DataFrame, required_columns: List[str]) -> None:
        """
        Validate that DataFrame has required columns.
        
        Args:
            df: DataFrame to validate
            required_columns: List of column names that must be present
            
        Raises:
            ValueError: If required columns are missing
        """
        if df is None:
            raise ValueError("DataFrame is None")
        
        existing_columns = df.columns
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Check if DataFrame is empty
        try:
            if df.count() == 0:
                self.logger.warning("DataFrame is empty")
        except Exception as e:
            self.logger.error(f"Error checking DataFrame count: {e}")
    
    def extract_field(self, row: Dict[str, Any], field_name: str, default: Any = None) -> Any:
        """
        Safely extract a field from a DataFrame row.
        
        Args:
            row: Dictionary representing a DataFrame row
            field_name: Name of the field to extract
            default: Default value if field is missing or None
            
        Returns:
            Field value or default
        """
        value = row.get(field_name)
        if value is None:
            return default
        return value
    
    def combine_text_fields(self, *fields: Optional[str], separator: str = " ") -> Optional[str]:
        """
        Combine multiple text fields into a single search text.
        
        Args:
            fields: Text fields to combine
            separator: Separator between fields
            
        Returns:
            Combined text or None if all fields are None
        """
        non_null_fields = [f for f in fields if f is not None and str(f).strip()]
        
        if not non_null_fields:
            return None
        
        return separator.join(str(f) for f in non_null_fields)
    
    def clean_text(self, text: Optional[str]) -> Optional[str]:
        """
        Clean text field for indexing.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text or None
        """
        if text is None:
            return None
        
        # Convert to string and strip whitespace
        cleaned = str(text).strip()
        
        # Return None if empty after cleaning
        if not cleaned:
            return None
        
        # Replace multiple spaces with single space
        cleaned = " ".join(cleaned.split())
        
        return cleaned
    
    def parse_list_field(self, value: Any) -> List[str]:
        """
        Parse a field that should be a list of strings.
        
        Args:
            value: Value to parse (could be list, string, or None)
            
        Returns:
            List of strings (empty list if None)
        """
        if value is None:
            return []
        
        if isinstance(value, list):
            # Ensure all items are strings
            return [str(item) for item in value if item is not None]
        
        if isinstance(value, str):
            # Handle comma-separated strings
            if "," in value:
                return [item.strip() for item in value.split(",") if item.strip()]
            # Single item
            return [value] if value.strip() else []
        
        # Convert single value to list
        return [str(value)]
    
    def create_id(self, entity_type: str, entity_id: str) -> str:
        """
        Create a document ID from entity type and ID.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity's unique identifier
            
        Returns:
            Document ID
        """
        return f"{entity_type}_{entity_id}"
    
    def apply_field_mapping(self, df: DataFrame, entity_type: str) -> DataFrame:
        """
        Apply field name standardization to DataFrame.
        
        Args:
            df: Source DataFrame
            entity_type: Type of entity (property, neighborhood, wikipedia)
            
        Returns:
            DataFrame with standardized field names
            
        Raises:
            ValueError: If field mapping fails or required fields are missing
        """
        if self.field_mapper is None:
            self.logger.warning("Field mapper not available, returning DataFrame unchanged")
            return df
        
        try:
            # Apply field mapping based on entity type
            if entity_type == "property":
                result = self.field_mapper.map_property_fields(df)
            elif entity_type == "neighborhood":
                result = self.field_mapper.map_neighborhood_fields(df)
            elif entity_type == "wikipedia":
                result = self.field_mapper.map_wikipedia_fields(df)
            else:
                raise ValueError(f"Unsupported entity type: {entity_type}")
            
            # Log mapping results
            if result.warnings:
                for warning in result.warnings:
                    self.logger.warning(warning)
            
            self.logger.info(
                f"Field mapping completed for {entity_type}: "
                f"{len(result.mapped_fields)} fields mapped, "
                f"{len(result.unmapped_fields)} fields unmapped"
            )
            
            return result.dataframe
            
        except Exception as e:
            self.logger.error(f"Field mapping failed for {entity_type}: {e}")
            raise
    
    def validate_field_mapping_requirements(self, df: DataFrame, entity_type: str) -> None:
        """
        Validate that required fields for field mapping are present.
        
        Args:
            df: DataFrame to validate
            entity_type: Type of entity
            
        Raises:
            ValueError: If required fields are missing
        """
        if self.field_mapper is None:
            return
        
        missing_fields = self.field_mapper.validate_required_fields(df, entity_type)
        
        if missing_fields:
            raise ValueError(
                f"Missing required fields for {entity_type}: {missing_fields}"
            )
    
    def _parse_date(self, value: Any) -> Optional[Any]:
        """
        Parse date field from various formats.
        
        Args:
            value: Date value (could be datetime, string, or None)
            
        Returns:
            datetime object or None
        """
        from datetime import datetime
        
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return value
        
        # Try to parse string dates
        if isinstance(value, str):
            try:
                # Try ISO format first
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                pass
            
            # Try other common formats
            for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"]:
                try:
                    return datetime.strptime(value, fmt)
                except:
                    continue
        
        return None