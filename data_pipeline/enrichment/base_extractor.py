"""
Base extractor class for entity extraction.

Provides common functionality for all entity extractors to ensure consistency
and reduce code duplication.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Type, TypeVar
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import StructType
from pydantic import BaseModel

from data_pipeline.models.spark_converter import SparkModel

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=SparkModel)


class BaseExtractor(ABC):
    """Base class for all entity extractors."""
    
    def __init__(self, spark: SparkSession):
        """
        Initialize the base extractor.
        
        Args:
            spark: Active SparkSession
        """
        self.spark = spark
        self._initialize()
    
    def _initialize(self) -> None:
        """
        Optional initialization hook for subclasses.
        Override this to perform additional setup.
        """
        pass
    
    def create_empty_dataframe(self, model_class: Type[SparkModel]) -> DataFrame:
        """
        Create an empty DataFrame with the correct schema from a Pydantic model.
        
        Args:
            model_class: The Pydantic model class that extends SparkModel
            
        Returns:
            Empty DataFrame with correct schema
        """
        try:
            return self.spark.createDataFrame([], model_class.spark_schema())
        except Exception as e:
            logger.error(f"Error creating empty DataFrame for {model_class.__name__}: {e}")
            # Fallback to basic schema
            return self.spark.createDataFrame([], StructType([]))
    
    def validate_input_columns(self, df: DataFrame, required_columns: List[str]) -> bool:
        """
        Validate that a DataFrame has the required columns.
        
        Args:
            df: DataFrame to validate
            required_columns: List of required column names
            
        Returns:
            True if all required columns exist, False otherwise
        """
        existing_columns = set(df.columns)
        missing_columns = set(required_columns) - existing_columns
        
        if missing_columns:
            logger.warning(f"Missing required columns: {missing_columns}")
            return False
        return True
    
    def safe_collect_to_models(
        self,
        df: DataFrame,
        model_class: Type[T],
        max_records: Optional[int] = None
    ) -> List[Dict]:
        """
        Safely collect DataFrame rows and convert to Pydantic model dictionaries.
        
        Args:
            df: DataFrame to collect from
            model_class: Pydantic model class for validation
            max_records: Maximum number of records to collect (for safety)
            
        Returns:
            List of model dictionaries ready for DataFrame creation
        """
        models = []
        
        try:
            # Limit collection for safety if specified
            if max_records:
                rows = df.limit(max_records).collect()
            else:
                rows = df.collect()
            
            for row in rows:
                try:
                    # Convert row to dict and validate with Pydantic
                    row_dict = row.asDict()
                    model_instance = model_class(**row_dict)
                    models.append(model_instance.model_dump())
                except Exception as e:
                    logger.debug(f"Skipping invalid row: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error collecting DataFrame: {e}")
        
        return models
    
    def create_dataframe_from_models(
        self,
        models: List[Dict],
        model_class: Type[SparkModel]
    ) -> DataFrame:
        """
        Create a DataFrame from a list of model dictionaries.
        
        Args:
            models: List of model dictionaries
            model_class: The Pydantic model class for schema
            
        Returns:
            DataFrame with the models or empty DataFrame with schema
        """
        if models:
            try:
                # Use the model's spark schema for proper type inference
                schema = model_class.spark_schema()
                return self.spark.createDataFrame(models, schema=schema)
            except Exception as e:
                logger.error(f"Error creating DataFrame from models: {e}")
                return self.create_empty_dataframe(model_class)
        else:
            return self.create_empty_dataframe(model_class)
    
    def log_extraction_stats(self, entity_type: str, count: int) -> None:
        """
        Log extraction statistics.
        
        Args:
            entity_type: Type of entity extracted
            count: Number of entities extracted
        """
        if count > 0:
            logger.info(f"Extracted {count} {entity_type} entities")
        else:
            logger.warning(f"No {entity_type} entities extracted")
    
    @abstractmethod
    def extract(self, *args, **kwargs) -> DataFrame:
        """
        Extract entities from input data.
        
        This method must be implemented by subclasses.
        
        Returns:
            DataFrame of extracted entities
        """
        pass
    


class ConfigurableExtractor(BaseExtractor):
    """Base class for extractors that need configuration."""
    
    def __init__(self, spark: SparkSession, config: Optional[Dict] = None):
        """
        Initialize with optional configuration.
        
        Args:
            spark: Active SparkSession
            config: Optional configuration dictionary
        """
        self.config = config or {}
        super().__init__(spark)
    
    def get_config_value(self, key: str, default=None):
        """
        Get a configuration value with a default.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)