"""Base DataFrame transformer for search pipeline.

Provides common functionality and interface for all DataFrame transformers.
Follows Spark best practices with distributed processing and type safety.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4

from pydantic import BaseModel
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import lit, current_timestamp
from pyspark.sql.types import StructType

logger = logging.getLogger(__name__)


class TransformationResult(BaseModel):
    """Result of DataFrame transformation operation."""
    
    success: bool = True
    entity_type: Optional[str] = None
    error_message: Optional[str] = None
    
    def get_summary(self) -> str:
        """Get transformation result summary."""
        if self.success:
            return f"{self.entity_type} transformation completed successfully"
        else:
            return f"{self.entity_type} transformation failed: {self.error_message}"


class BaseDataFrameTransformer(ABC):
    """
    Abstract base class for DataFrame transformers.
    
    Provides common functionality for transforming input DataFrames to
    target document schema using Spark-native operations. All transformers
    follow the same pattern:
    
    1. Validate input DataFrame
    2. Apply transformations using DataFrame API
    3. Validate output schema
    4. Return transformed DataFrame
    """
    
    def __init__(self, entity_type: str):
        """
        Initialize base transformer.
        
        Args:
            entity_type: Type of entity being transformed (property, neighborhood, wikipedia)
        """
        self.entity_type = entity_type
        self.logger = logging.getLogger(f"{__name__}.{entity_type}")
    
    def transform(self, input_df: DataFrame) -> DataFrame:
        """
        Transform input DataFrame to target document schema.
        
        Args:
            input_df: Input DataFrame from data pipeline
            
        Returns:
            Transformed DataFrame ready for Elasticsearch indexing
        """
        start_time = datetime.now()
        
        try:
            # Validate input
            self._validate_input(input_df)
            
            self.logger.info(f"Transforming {self.entity_type} records")
            
            # Apply entity-specific transformation
            output_df = self._apply_transformation(input_df)
            
            # Add base document fields
            output_df = self._add_base_fields(output_df)
            
            # Validate output
            self._validate_output(output_df)
            
            self.logger.info(f"✓ {self.entity_type} transformation completed")
            
            return output_df
            
        except Exception as e:
            error_msg = f"{self.entity_type} transformation failed: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def _validate_input(self, df: DataFrame) -> None:
        """
        Validate input DataFrame structure.
        
        Args:
            df: Input DataFrame to validate
            
        Raises:
            ValueError: If input validation fails
        """
        if df is None:
            raise ValueError("Input DataFrame cannot be None")
        
        if len(df.columns) == 0:
            raise ValueError("Input DataFrame has no columns")
        
        # Check for required ID field
        id_field = self._get_id_field()
        if id_field not in df.columns:
            raise ValueError(f"Required field '{id_field}' not found in input DataFrame")
        
        self.logger.debug(f"Input validation passed for {self.entity_type}")
    
    def _validate_output(self, df: DataFrame) -> None:
        """
        Validate output DataFrame structure.
        
        Args:
            df: Output DataFrame to validate
            
        Raises:
            ValueError: If output validation fails
        """
        if df is None:
            raise ValueError("Output DataFrame cannot be None")
        
        # Check for required base document fields
        required_fields = ["doc_id", "entity_id", "entity_type"]
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"Required base field '{field}' not found in output DataFrame")
        
        self.logger.debug(f"Output validation passed for {self.entity_type}")
    
    def _add_base_fields(self, df: DataFrame) -> DataFrame:
        """
        Add base document fields to DataFrame.
        
        Args:
            df: DataFrame to add base fields to
            
        Returns:
            DataFrame with base document fields added
        """
        id_field = self._get_id_field()
        
        return df.withColumn("doc_id", df[id_field]) \
                 .withColumn("entity_id", df[id_field]) \
                 .withColumn("entity_type", lit(self.entity_type)) \
                 .withColumn("indexed_at", current_timestamp())
    
    @abstractmethod
    def _apply_transformation(self, input_df: DataFrame) -> DataFrame:
        """
        Apply entity-specific transformations to input DataFrame.
        
        This method must be implemented by each specific transformer
        to handle the unique transformation logic for that entity type.
        
        Args:
            input_df: Input DataFrame from data pipeline
            
        Returns:
            Transformed DataFrame with target schema
        """
        pass
    
    @abstractmethod
    def _get_id_field(self) -> str:
        """
        Get the ID field name for this entity type.
        
        Returns:
            Name of the primary ID field for this entity type
        """
        pass
    
    def _safe_column_access(self, df: DataFrame, column_path: str, default_value: Any = None):
        """
        Safely access nested column with fallback to default value.
        
        Args:
            df: DataFrame to access column from
            column_path: Dot-separated path to nested column (e.g., "address.city")
            default_value: Default value if column doesn't exist
            
        Returns:
            Column expression with safe access
        """
        from pyspark.sql.functions import col, lit, when
        
        try:
            # Check if column path exists
            if "." in column_path:
                # Nested column access
                parts = column_path.split(".")
                base_col = parts[0]
                
                if base_col in df.columns:
                    return col(column_path)
                else:
                    return lit(default_value)
            else:
                # Simple column access
                if column_path in df.columns:
                    return col(column_path)
                else:
                    return lit(default_value)
                    
        except Exception:
            return lit(default_value)
    
    
