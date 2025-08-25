"""
Base enricher class for common enrichment functionality.

Provides shared functionality for all entity-specific enrichers to reduce
code duplication and ensure consistent patterns.
"""

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, current_timestamp, lit, udf, when
from pyspark.sql.types import StringType

logger = logging.getLogger(__name__)

class BaseEnricher(ABC):
    """
    Abstract base class for entity-specific enrichers.
    
    Provides common functionality like UUID generation, correlation IDs,
    and timestamp management.
    """

    # Shared static location abbreviation constants
    CITY_ABBREVIATIONS = {
        "SF": "San Francisco",
        "PC": "Park City",
        "NYC": "New York City",
        "LA": "Los Angeles",
        "SLC": "Salt Lake City",
        "LV": "Las Vegas",
    }
    STATE_ABBREVIATIONS = {
        "CA": "California",
        "UT": "Utah",
        "NY": "New York",
        "TX": "Texas",
        "NV": "Nevada",
        "CO": "Colorado",
    }

    def __init__(
        self,
        spark: SparkSession,
        location_broadcast: Optional[Any] = None
    ):
        """
        Initialize the base enricher.
        
        Args:
            spark: Active SparkSession
            location_broadcast: Optional broadcast variable with location data
        """
        self.spark = spark
        self.location_broadcast = location_broadcast
        self.location_enricher = None
        
        # Register common UDFs
        self._register_common_udfs()
        self._initialize_location_enricher()
    
    @abstractmethod
    def enrich(self, df: DataFrame) -> DataFrame:
        """
        Apply entity-specific enrichments.
        
        Args:
            df: DataFrame to enrich
            
        Returns:
            Enriched DataFrame
        """
        pass
    
    def _register_common_udfs(self):
        """Register UDFs used by all enrichers."""
        def generate_uuid() -> str:
            return str(uuid.uuid4())
        
        self.generate_uuid_udf = udf(generate_uuid, StringType())
    
    def _initialize_location_enricher(self):
        """Initialize location enricher if location data is available."""
        if self.location_broadcast:
            from .location_enricher import LocationEnricher
            self.location_enricher = LocationEnricher(
                self.spark,
                self.location_broadcast,
            )
            logger.info(f"LocationEnricher initialized for {self.__class__.__name__}")
    
    def set_location_data(self, location_broadcast: Any):
        """
        Set or update location broadcast data.
        
        Args:
            location_broadcast: Broadcast variable containing location reference data
        """
        self.location_broadcast = location_broadcast
        self._initialize_location_enricher()
    
    def add_correlation_ids(self, df: DataFrame, id_column: str) -> DataFrame:
        """
        Add correlation IDs for entity tracking.
        
        Args:
            df: DataFrame to add IDs to
            id_column: Name of the correlation ID column
            
        Returns:
            DataFrame with correlation IDs
        """
        if id_column in df.columns:
            return df.withColumn(
                id_column,
                when(col(id_column).isNull(), self.generate_uuid_udf())
                .otherwise(col(id_column))
            )
        else:
            return df.withColumn(id_column, self.generate_uuid_udf())
    
    def add_processing_timestamp(self, df: DataFrame) -> DataFrame:
        """
        Add processing timestamp to DataFrame.
        
        Args:
            df: DataFrame to add timestamp to
            
        Returns:
            DataFrame with processed_at column
        """
        return df.withColumn("processed_at", current_timestamp())
    
    def validate_enrichment(
        self, 
        df: DataFrame, 
        initial_count: int, 
        entity_name: str
    ) -> DataFrame:
        """
        Validate enrichment didn't lose records.
        
        Args:
            df: Enriched DataFrame
            initial_count: Original record count
            entity_name: Name of entity type for logging
            
        Returns:
            The enriched DataFrame
        """
        final_count = df.count()
        if final_count != initial_count:
            logger.warning(
                f"{entity_name} count changed during enrichment: "
                f"{initial_count} -> {final_count}"
            )
        else:
            logger.info(f"{entity_name} enrichment completed for {final_count} records")
        
        return df
    
    def get_enrichment_statistics(self, df: DataFrame) -> Dict[str, Any]:
        """
        Calculate basic enrichment statistics.
        
        Args:
            df: Enriched DataFrame
            
        Returns:
            Dictionary of statistics
        """
        stats = {
            "total_records": df.count(),
            "columns": len(df.columns)
        }
        
        # Add quality score stats if available
        quality_col = None
        for col_name in df.columns:
            if "quality_score" in col_name:
                quality_col = col_name
                break
        
        if quality_col:
            quality_stats = df.select(
                col(quality_col).alias("score")
            ).summary("mean", "min", "max").collect()
            
            if quality_stats:
                stats["quality_scores"] = {
                    "mean": float(quality_stats[1]["score"]) if quality_stats[1]["score"] else 0,
                    "min": float(quality_stats[2]["score"]) if quality_stats[2]["score"] else 0,
                    "max": float(quality_stats[3]["score"]) if quality_stats[3]["score"] else 0,
                }
        
        return stats

    def get_city_abbreviations(self) -> Dict[str, str]:  # convenience accessor
        return self.CITY_ABBREVIATIONS

    def get_state_abbreviations(self) -> Dict[str, str]:  # convenience accessor
        return self.STATE_ABBREVIATIONS
