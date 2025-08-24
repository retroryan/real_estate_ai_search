"""
Orchestrator for coordinating entity-specific data loaders.

This module provides a clean interface to load data from all sources
and returns them as separate DataFrames for each entity type.
"""

import logging
from typing import Dict, List, Optional

from pyspark.sql import DataFrame, SparkSession

from data_pipeline.config.models import PipelineConfig
from data_pipeline.loaders.location_loader import LocationLoader
from data_pipeline.loaders.neighborhood_loader import NeighborhoodLoader
from data_pipeline.loaders.property_loader import PropertyLoader
from data_pipeline.loaders.wikipedia_loader import WikipediaLoader

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
        self.location_loader = LocationLoader(spark)
        self.property_loader = PropertyLoader(spark)
        self.neighborhood_loader = NeighborhoodLoader(spark)
        self.wikipedia_loader = WikipediaLoader(spark)
        
        # Track loaded DataFrames and broadcast variables
        self._loaded_dataframes: Dict[str, DataFrame] = {}
        self._location_broadcast = None
    
    def load_all_sources(self) -> Dict[str, DataFrame]:
        """
        Load data from all configured sources and return as separate DataFrames.
        
        Returns:
            Dictionary with keys 'locations', 'properties', 'neighborhoods', 'wikipedia' 
            and their corresponding DataFrames (or None if not loaded)
        """
        logger.info("=" * 60)
        logger.info("Starting data loading from all sources")
        logger.info("=" * 60)
        
        result = {}
        
        # Load locations first as reference data
        locations_df = self._load_locations()
        if locations_df is not None:
            result["locations"] = locations_df
            # Create broadcast variable for efficient lookups
            self._location_broadcast = self.spark.sparkContext.broadcast(
                locations_df.collect()
            )
            logger.info("Created broadcast variable for location reference data")
        
        # Load properties
        result['properties'] = self._load_and_union_entity('properties', self._load_properties())
        
        # Load neighborhoods
        result['neighborhoods'] = self._load_and_union_entity('neighborhoods', self._load_neighborhoods())
        
        # Load Wikipedia
        wikipedia_df = self._load_wikipedia()
        if wikipedia_df is not None:
            result['wikipedia'] = wikipedia_df
            logger.info(f"Loaded {result['wikipedia'].count()} Wikipedia articles")
        else:
            result['wikipedia'] = None
        
        # Log summary statistics
        self._log_summary(result)
        
        return result
    
    def _load_and_union_entity(self, entity_name: str, dataframes: List[DataFrame]) -> Optional[DataFrame]:
        """
        Union multiple DataFrames for an entity type.
        
        Args:
            entity_name: Name of the entity type for logging
            dataframes: List of DataFrames to union
            
        Returns:
            Unioned DataFrame or None if no data
        """
        if not dataframes:
            return None
            
        if len(dataframes) == 1:
            result = dataframes[0]
        else:
            result = dataframes[0]
            for df in dataframes[1:]:
                result = result.unionByName(df, allowMissingColumns=False)
        
        logger.info(f"Loaded {result.count()} {entity_name} records")
        return result
    
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
    
    def _load_locations(self) -> Optional[DataFrame]:
        """
        Load location reference data if configured.
        
        Returns:
            Location DataFrame or None
        """
        for source_name, source_config in self.config.data_sources.items():
            if "locations" in source_name.lower() and source_config.enabled:
                try:
                    logger.info(f"Loading location reference data: {source_name}")
                    df = self.location_loader.load(source_config.path)
                    
                    if self.location_loader.validate(df):
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
    
    def get_location_broadcast(self):
        """
        Get the broadcast variable containing location reference data.
        
        Returns:
            Broadcast variable with location data or None
        """
        return self._location_broadcast
    
    def _log_summary(self, entity_dataframes: Dict[str, DataFrame]) -> None:
        """
        Log summary statistics for loaded data.
        
        Args:
            entity_dataframes: Dictionary of entity type to DataFrame
        """
        total = 0
        entity_counts = {}
        
        # Count records per entity type
        for entity_type, df in entity_dataframes.items():
            if df is not None:
                count = df.count()
                entity_counts[entity_type] = count
                total += count
        
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Data Loading Complete: {total:,} total records")
        logger.info("=" * 60)
        
        # Log counts by entity type
        for entity_type, count in entity_counts.items():
            logger.info(f"  {entity_type}: {count:,} records")
        
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