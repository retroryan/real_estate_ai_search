"""
Unified data loader for all sources.

This module provides a single interface for loading data from multiple sources
and combining them into a unified DataFrame with standardized schema.
Uses Spark's native capabilities where possible.
"""

import logging
from typing import Dict, List, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, lit

from data_pipeline.config.models import DataSourceConfig, PipelineConfig
from data_pipeline.ingestion.spark_native_loader import SparkNativeLoader
from data_pipeline.schemas.unified_schema import UnifiedDataSchema

logger = logging.getLogger(__name__)


class UnifiedLoader:
    """Unified data loader for all source types."""
    
    def __init__(self, spark: SparkSession, config: PipelineConfig):
        """
        Initialize unified loader.
        
        Args:
            spark: SparkSession instance
            config: Pipeline configuration
        """
        self.spark = spark
        self.config = config
        self.schema = UnifiedDataSchema()
        self.native_loader = SparkNativeLoader(spark, config)
        self._loaded_dataframes: Dict[str, DataFrame] = {}
    
    def load_all_sources(self) -> DataFrame:
        """
        Load and union all configured data sources.
        
        Returns:
            Unified DataFrame containing all data
        """
        logger.info("Starting unified data loading process")
        
        dataframes = []
        
        # Load each enabled data source
        for source_name, source_config in self.config.data_sources.items():
            if not source_config.enabled:
                logger.info(f"Skipping disabled source: {source_name}")
                continue
            
            try:
                df = self._load_source(source_name, source_config)
                if df is not None:
                    dataframes.append(df)
                    self._loaded_dataframes[source_name] = df
            except Exception as e:
                logger.error(f"Failed to load source {source_name}: {e}")
                if self.config.processing.enable_quality_checks:
                    raise  # Fail fast if quality checks are enabled
                continue
        
        if not dataframes:
            logger.warning("No data sources loaded successfully")
            return self._create_empty_dataframe()
        
        # Union all dataframes
        unified_df = self._union_dataframes(dataframes)
        
        # Log statistics
        self._log_loading_statistics(unified_df)
        
        return unified_df
    
    def load_source(self, source_name: str) -> Optional[DataFrame]:
        """
        Load a specific data source.
        
        Args:
            source_name: Name of the source to load
            
        Returns:
            DataFrame with loaded data or None if source not found
        """
        if source_name not in self.config.data_sources:
            logger.error(f"Source not found in configuration: {source_name}")
            return None
        
        source_config = self.config.data_sources[source_name]
        
        if not source_config.enabled:
            logger.warning(f"Source is disabled: {source_name}")
            return None
        
        return self._load_source(source_name, source_config)
    
    def _load_source(
        self, 
        source_name: str, 
        source_config: DataSourceConfig
    ) -> Optional[DataFrame]:
        """
        Load data from a single source using Spark's native capabilities.
        
        Args:
            source_name: Name of the source
            source_config: Source configuration
            
        Returns:
            DataFrame with unified schema or None if loading fails
        """
        logger.info(f"Loading source: {source_name}")
        
        try:
            # Determine source type and use appropriate native loader method
            if "properties" in source_name.lower():
                unified_df = self.native_loader.load_json_properties(source_config.path)
            elif "neighborhoods" in source_name.lower():
                unified_df = self.native_loader.load_json_neighborhoods(source_config.path)
            elif source_config.format == "sqlite" or "wikipedia" in source_name.lower():
                # Use pure Python approach by default (pandas/sqlite3)
                use_pandas = source_config.options.get("use_pandas", True)
                unified_df = self.native_loader.load_sqlite_wikipedia(
                    source_config.path,
                    use_jdbc=not use_pandas
                )
            else:
                logger.error(f"Unknown source type: {source_name}")
                return None
            
            if unified_df is None or unified_df.count() == 0:
                logger.warning(f"No data loaded from source: {source_name}")
                return None
            
            # Validate schema conformance
            unified_df = self._ensure_schema_conformance(unified_df)
            
            record_count = unified_df.count()
            logger.info(f"Successfully loaded {record_count} records from {source_name}")
            
            return unified_df
            
        except Exception as e:
            logger.error(f"Error loading source {source_name}: {e}")
            raise
    
    def _union_dataframes(self, dataframes: List[DataFrame]) -> DataFrame:
        """
        Union multiple DataFrames with unified schema.
        
        Args:
            dataframes: List of DataFrames to union
            
        Returns:
            Single unified DataFrame
        """
        if len(dataframes) == 1:
            return dataframes[0]
        
        logger.info(f"Unioning {len(dataframes)} dataframes")
        
        # Start with first dataframe
        result = dataframes[0]
        
        # Union remaining dataframes
        for df in dataframes[1:]:
            result = result.unionByName(df, allowMissingColumns=True)
        
        return result
    
    def _ensure_schema_conformance(self, df: DataFrame) -> DataFrame:
        """
        Ensure DataFrame conforms to unified schema.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with correct schema
        """
        # Get expected schema
        expected_schema = self.schema.get_schema()
        
        # Add missing columns with null values
        for field in expected_schema.fields:
            if field.name not in df.columns:
                df = df.withColumn(field.name, lit(None).cast(field.dataType))
        
        # Select columns in correct order
        column_names = [field.name for field in expected_schema.fields]
        df = df.select(*column_names)
        
        # Cast to correct types if needed
        for field in expected_schema.fields:
            df = df.withColumn(field.name, col(field.name).cast(field.dataType))
        
        return df
    
    def _create_empty_dataframe(self) -> DataFrame:
        """
        Create empty DataFrame with unified schema.
        
        Returns:
            Empty DataFrame with correct schema
        """
        logger.info("Creating empty DataFrame with unified schema")
        return self.spark.createDataFrame([], self.schema.get_schema())
    
    def _log_loading_statistics(self, df: DataFrame) -> None:
        """
        Log statistics about loaded data.
        
        Args:
            df: Unified DataFrame
        """
        total_count = df.count()
        logger.info(f"Total records loaded: {total_count}")
        
        # Count by entity type
        entity_counts = df.groupBy("entity_type").count().collect()
        for row in entity_counts:
            logger.info(f"  {row['entity_type']}: {row['count']} records")
        
        # Count by state
        state_counts = df.filter(col("state").isNotNull()) \
                        .groupBy("state").count() \
                        .orderBy(col("count").desc()) \
                        .limit(5).collect()
        
        if state_counts:
            logger.info("Top states by record count:")
            for row in state_counts:
                logger.info(f"  {row['state']}: {row['count']} records")
        
        # Check for null entity IDs (data quality issue)
        null_ids = df.filter(col("entity_id").isNull()).count()
        if null_ids > 0:
            logger.warning(f"Found {null_ids} records with null entity_id")
        
        # Memory usage estimate
        partitions = df.rdd.getNumPartitions()
        logger.info(f"DataFrame partitions: {partitions}")
    
    def get_loaded_sources(self) -> List[str]:
        """
        Get list of successfully loaded sources.
        
        Returns:
            List of source names
        """
        return list(self._loaded_dataframes.keys())
    
    def get_source_dataframe(self, source_name: str) -> Optional[DataFrame]:
        """
        Get DataFrame for a specific loaded source.
        
        Args:
            source_name: Name of the source
            
        Returns:
            DataFrame or None if not loaded
        """
        return self._loaded_dataframes.get(source_name)
    
    def validate_loaded_data(self) -> Dict[str, Any]:
        """
        Validate all loaded data and return metrics.
        
        Returns:
            Dictionary with validation metrics
        """
        metrics = {
            "sources_loaded": len(self._loaded_dataframes),
            "source_metrics": {}
        }
        
        for source_name, df in self._loaded_dataframes.items():
            source_metrics = {
                "record_count": df.count(),
                "null_entity_ids": df.filter(col("entity_id").isNull()).count(),
                "unique_entity_ids": df.select("entity_id").distinct().count(),
                "entity_types": df.select("entity_type").distinct().collect()
            }
            metrics["source_metrics"][source_name] = source_metrics
        
        return metrics