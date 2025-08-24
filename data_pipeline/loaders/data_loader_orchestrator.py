"""
Simple orchestrator for coordinating all data loaders.

This module provides a clean interface to load data from all sources
and combine them into a single unified DataFrame.
"""

import logging
from typing import Dict, List, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col

from data_pipeline.config.models import PipelineConfig
from data_pipeline.loaders.neighborhood_loader import NeighborhoodLoader
from data_pipeline.loaders.property_loader import PropertyLoader
from data_pipeline.loaders.wikipedia_loader import WikipediaLoader
from data_pipeline.schemas.unified_schema import UnifiedDataSchema

logger = logging.getLogger(__name__)


class DataLoaderOrchestrator:
    """Orchestrates loading from all data sources."""
    
    def __init__(self, spark: SparkSession, config: PipelineConfig):
        """
        Initialize the data loader orchestrator.
        
        Args:
            spark: Active SparkSession
            config: Pipeline configuration
        """
        self.spark = spark
        self.config = config
        
        # Initialize individual loaders
        self.property_loader = PropertyLoader(spark)
        self.neighborhood_loader = NeighborhoodLoader(spark)
        self.wikipedia_loader = WikipediaLoader(spark)
        
        # Track loaded DataFrames
        self._loaded_dataframes: Dict[str, DataFrame] = {}
    
    def load_all_sources(self) -> DataFrame:
        """
        Load data from all configured sources and combine into unified DataFrame.
        
        Returns:
            Unified DataFrame containing all data
        """
        logger.info("=" * 60)
        logger.info("Starting data loading from all sources")
        logger.info("=" * 60)
        
        dataframes = []
        
        # Load properties
        property_dfs = self._load_properties()
        dataframes.extend(property_dfs)
        
        # Load neighborhoods
        neighborhood_dfs = self._load_neighborhoods()
        dataframes.extend(neighborhood_dfs)
        
        # Load Wikipedia
        wikipedia_df = self._load_wikipedia()
        if wikipedia_df is not None:
            dataframes.append(wikipedia_df)
        
        # Combine all DataFrames
        if not dataframes:
            logger.warning("No data loaded from any source")
            return self._create_empty_dataframe()
        
        unified_df = self._union_dataframes(dataframes)
        
        # Log summary statistics
        self._log_summary(unified_df)
        
        return unified_df
    
    def _load_properties(self) -> List[DataFrame]:
        """
        Load all configured property data sources.
        
        Returns:
            List of property DataFrames
        """
        property_dfs = []
        
        for source_name, source_config in self.config.data_sources.items():
            if "properties" in source_name.lower() and source_config.enabled:
                try:
                    logger.info(f"Loading property source: {source_name}")
                    df = self.property_loader.load(source_config.path)
                    
                    if self.property_loader.validate(df):
                        property_dfs.append(df)
                        self._loaded_dataframes[source_name] = df
                        logger.info(f"✓ Successfully loaded {source_name}")
                    else:
                        logger.warning(f"✗ Validation failed for {source_name}")
                        
                except Exception as e:
                    logger.error(f"✗ Failed to load {source_name}: {e}")
                    if self.config.processing.enable_quality_checks:
                        raise
        
        return property_dfs
    
    def _load_neighborhoods(self) -> List[DataFrame]:
        """
        Load all configured neighborhood data sources.
        
        Returns:
            List of neighborhood DataFrames
        """
        neighborhood_dfs = []
        
        for source_name, source_config in self.config.data_sources.items():
            if "neighborhoods" in source_name.lower() and source_config.enabled:
                try:
                    logger.info(f"Loading neighborhood source: {source_name}")
                    df = self.neighborhood_loader.load(source_config.path)
                    
                    if self.neighborhood_loader.validate(df):
                        neighborhood_dfs.append(df)
                        self._loaded_dataframes[source_name] = df
                        logger.info(f"✓ Successfully loaded {source_name}")
                    else:
                        logger.warning(f"✗ Validation failed for {source_name}")
                        
                except Exception as e:
                    logger.error(f"✗ Failed to load {source_name}: {e}")
                    if self.config.processing.enable_quality_checks:
                        raise
        
        return neighborhood_dfs
    
    def _load_wikipedia(self) -> Optional[DataFrame]:
        """
        Load Wikipedia data if configured.
        
        Returns:
            Wikipedia DataFrame or None
        """
        for source_name, source_config in self.config.data_sources.items():
            if "wikipedia" in source_name.lower() and source_config.enabled:
                try:
                    logger.info(f"Loading Wikipedia source: {source_name}")
                    df = self.wikipedia_loader.load(source_config.path)
                    
                    if self.wikipedia_loader.validate(df):
                        self._loaded_dataframes[source_name] = df
                        logger.info(f"✓ Successfully loaded {source_name}")
                        return df
                    else:
                        logger.warning(f"✗ Validation failed for {source_name}")
                        
                except Exception as e:
                    logger.error(f"✗ Failed to load {source_name}: {e}")
                    if self.config.processing.enable_quality_checks:
                        raise
        
        return None
    
    def _union_dataframes(self, dataframes: List[DataFrame]) -> DataFrame:
        """
        Union multiple DataFrames into one.
        
        Args:
            dataframes: List of DataFrames to union
            
        Returns:
            Combined DataFrame
        """
        if len(dataframes) == 1:
            return dataframes[0]
        
        logger.info(f"Combining {len(dataframes)} DataFrames")
        
        # Start with first DataFrame
        result = dataframes[0]
        
        # Union remaining DataFrames
        for df in dataframes[1:]:
            result = result.unionByName(df, allowMissingColumns=True)
        
        return result
    
    def _create_empty_dataframe(self) -> DataFrame:
        """
        Create an empty DataFrame with unified schema.
        
        Returns:
            Empty DataFrame with correct schema
        """
        schema = UnifiedDataSchema.get_schema()
        return self.spark.createDataFrame([], schema)
    
    def _log_summary(self, df: DataFrame) -> None:
        """
        Log summary statistics for loaded data.
        
        Args:
            df: Combined DataFrame
        """
        total = df.count()
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Data Loading Complete: {total:,} total records")
        logger.info("=" * 60)
        
        # Count by entity type
        entity_counts = df.groupBy("entity_type").count().collect()
        for row in entity_counts:
            logger.info(f"  {row['entity_type']}: {row['count']:,} records")
        
        # Sources loaded
        logger.info("")
        logger.info(f"Sources loaded: {len(self._loaded_dataframes)}")
        for source_name in self._loaded_dataframes:
            logger.info(f"  ✓ {source_name}")
        
        logger.info("=" * 60)
    
    def get_loaded_source(self, source_name: str) -> Optional[DataFrame]:
        """
        Get a specific loaded DataFrame by source name.
        
        Args:
            source_name: Name of the source
            
        Returns:
            DataFrame or None if not loaded
        """
        return self._loaded_dataframes.get(source_name)
    
    def get_loaded_sources(self) -> List[str]:
        """
        Get list of successfully loaded source names.
        
        Returns:
            List of source names
        """
        return list(self._loaded_dataframes.keys())