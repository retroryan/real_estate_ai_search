"""Base writer strategy for entity-specific output transformations."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import duckdb
import pandas as pd

from squack_pipeline.models import EntityType
from squack_pipeline.config.entity_config import EntityConfig
from squack_pipeline.utils.logging import PipelineLogger


class WriterConfig(BaseModel):
    """Configuration for writer strategies."""
    
    entity_type: EntityType = Field(
        ...,
        description="Entity type this writer handles"
    )
    
    output_format: str = Field(
        default="parquet",
        description="Output format (parquet, json, csv, elasticsearch)"
    )
    
    batch_size: int = Field(
        default=1000,
        gt=0,
        description="Batch size for writing"
    )
    
    flatten_nested: bool = Field(
        default=False,
        description="Whether to flatten nested structures"
    )
    
    include_metadata: bool = Field(
        default=True,
        description="Whether to include metadata fields"
    )
    
    field_mappings: Dict[str, str] = Field(
        default_factory=dict,
        description="Field name mappings for output"
    )
    
    excluded_fields: List[str] = Field(
        default_factory=list,
        description="Fields to exclude from output"
    )


class BaseWriterStrategy(ABC):
    """Abstract base class for entity-specific writer strategies.
    
    Writer strategies handle entity-specific transformations when
    writing data to various output formats. Each entity type can
    have its own strategy for handling nested structures, field
    mappings, and format-specific requirements.
    """
    
    def __init__(self, config: WriterConfig):
        """Initialize the writer strategy.
        
        Args:
            config: Writer configuration
        """
        self.config = config
        self.logger = PipelineLogger.get_logger(
            f"{self.__class__.__name__}({config.entity_type.value})"
        )
    
    @abstractmethod
    def prepare_for_output(
        self,
        data: pd.DataFrame,
        entity_config: Optional[EntityConfig] = None
    ) -> pd.DataFrame:
        """Prepare data for output format.
        
        Args:
            data: DataFrame to prepare
            entity_config: Optional entity-specific configuration
            
        Returns:
            Prepared DataFrame
        """
        pass
    
    @abstractmethod
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single record for output.
        
        Args:
            record: Record to transform
            
        Returns:
            Transformed record
        """
        pass
    
    @abstractmethod
    def get_field_mappings(self) -> Dict[str, str]:
        """Get field name mappings for output.
        
        Returns:
            Dictionary of source field to output field mappings
        """
        pass
    
    def apply_field_mappings(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply field name mappings to DataFrame.
        
        Args:
            data: DataFrame to apply mappings to
            
        Returns:
            DataFrame with mapped field names
        """
        mappings = self.get_field_mappings()
        if mappings:
            # Update mappings with config overrides
            mappings.update(self.config.field_mappings)
            
            # Rename columns
            data = data.rename(columns=mappings)
            
            self.logger.debug(f"Applied {len(mappings)} field mappings")
        
        return data
    
    def exclude_fields(self, data: pd.DataFrame) -> pd.DataFrame:
        """Remove excluded fields from DataFrame.
        
        Args:
            data: DataFrame to process
            
        Returns:
            DataFrame with excluded fields removed
        """
        if self.config.excluded_fields:
            columns_to_drop = [
                col for col in self.config.excluded_fields
                if col in data.columns
            ]
            
            if columns_to_drop:
                data = data.drop(columns=columns_to_drop)
                self.logger.debug(f"Excluded {len(columns_to_drop)} fields")
        
        return data
    
    def flatten_nested_structures(self, data: pd.DataFrame) -> pd.DataFrame:
        """Flatten nested structures in DataFrame.
        
        Args:
            data: DataFrame with potential nested structures
            
        Returns:
            DataFrame with flattened structures
        """
        if not self.config.flatten_nested:
            return data
        
        # Identify columns with nested data
        nested_cols = []
        for col in data.columns:
            if data[col].dtype == 'object':
                # Check if column contains dicts or lists
                sample = data[col].dropna().iloc[0] if not data[col].dropna().empty else None
                if sample and isinstance(sample, (dict, list)):
                    nested_cols.append(col)
        
        if not nested_cols:
            return data
        
        self.logger.debug(f"Flattening {len(nested_cols)} nested columns")
        
        # Flatten each nested column
        for col in nested_cols:
            if data[col].dtype == 'object':
                # Handle dict columns
                if isinstance(data[col].dropna().iloc[0] if not data[col].dropna().empty else None, dict):
                    # Normalize the dict column
                    normalized = pd.json_normalize(data[col].fillna({}))
                    # Prefix column names
                    normalized.columns = [f"{col}_{subcol}" for subcol in normalized.columns]
                    # Drop original column and concat normalized
                    data = pd.concat([data.drop(columns=[col]), normalized], axis=1)
                
                # Handle list columns
                elif isinstance(data[col].dropna().iloc[0] if not data[col].dropna().empty else None, list):
                    # Convert lists to comma-separated strings
                    data[col] = data[col].apply(
                        lambda x: ', '.join(map(str, x)) if isinstance(x, list) else x
                    )
        
        return data
    
    def add_metadata(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add metadata fields to DataFrame.
        
        Args:
            data: DataFrame to add metadata to
            
        Returns:
            DataFrame with metadata fields
        """
        if self.config.include_metadata:
            # Add entity type
            data['_entity_type'] = self.config.entity_type.value
            
            # Add processing timestamp
            import time
            data['_processed_at'] = int(time.time())
            
            # Add output format
            data['_output_format'] = self.config.output_format
            
            self.logger.debug("Added metadata fields")
        
        return data
    
    def validate_output(self, data: pd.DataFrame) -> bool:
        """Validate prepared data before writing.
        
        Args:
            data: DataFrame to validate
            
        Returns:
            True if valid, False otherwise
        """
        if data.empty:
            self.logger.warning("Empty DataFrame")
            return False
        
        # Check for required columns based on entity type
        # This can be extended with entity-specific validation
        
        return True
    
    def get_elasticsearch_mapping(self) -> Dict[str, Any]:
        """Get Elasticsearch mapping for the entity type.
        
        Returns:
            Elasticsearch mapping configuration
        """
        # Default mapping - should be overridden by entity-specific strategies
        return {
            "properties": {
                "_entity_type": {"type": "keyword"},
                "_processed_at": {"type": "long"},
                "_output_format": {"type": "keyword"}
            }
        }