"""
Orchestrator for coordinating entity-specific data loaders.

This module provides a clean interface to load data from all sources
and returns them as separate DataFrames for each entity type.
"""

import logging
from typing import Optional

from pydantic import BaseModel
from pyspark.sql import DataFrame, SparkSession

from data_pipeline.config.models import PipelineConfig
from data_pipeline.loaders.location_loader import LocationLoader
from data_pipeline.loaders.neighborhood_loader import NeighborhoodLoader
from data_pipeline.loaders.property_loader import PropertyLoader
from data_pipeline.loaders.wikipedia_loader import WikipediaLoader

logger = logging.getLogger(__name__)


class LoadedData(BaseModel):
    """Container for all loaded DataFrames."""
    
    class Config:
        arbitrary_types_allowed = True
    
    properties: Optional[DataFrame] = None
    neighborhoods: Optional[DataFrame] = None
    wikipedia: Optional[DataFrame] = None
    locations: Optional[DataFrame] = None


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
        
        # Track broadcast variables
        self._location_broadcast = None
    
    def load_all_sources(self) -> LoadedData:
        """
        Load data from all configured sources and return as a LoadedData object.
        
        Returns:
            LoadedData object containing all loaded DataFrames
        """
        logger.info("=" * 60)
        logger.info("Starting data loading from all sources")
        logger.info("=" * 60)
        
        # Load locations first as reference data
        locations_df = self._load_locations()
        if locations_df is not None:
            # Create broadcast variable for efficient lookups
            self._location_broadcast = self.spark.sparkContext.broadcast(
                locations_df.collect()
            )
            logger.info("Created broadcast variable for location reference data")
        
        # Create result object with all loaded data
        result = LoadedData(
            locations=locations_df,
            properties=self._load_properties(),
            neighborhoods=self._load_neighborhoods(),
            wikipedia=self._load_wikipedia()
        )
        
        # Log summary statistics
        self._log_summary(result)
        
        return result
    
    def _load_properties(self) -> Optional[DataFrame]:
        """
        Load and union all property data files.
        
        Returns:
            Combined property DataFrame or None if no data
        """
        if not self.config.properties:
            logger.info("No property files configured")
            return None
        
        dataframes = []
        for path in self.config.properties:
            try:
                logger.info(f"Loading properties from: {path}")
                df = self.property_loader.load(path)
                
                if self.property_loader.validate(df):
                    dataframes.append(df)
                    logger.info(f"✓ Successfully loaded {path}")
                else:
                    logger.warning(f"✗ Validation failed for {path}")
                    
            except Exception as e:
                logger.error(f"✗ Failed to load {path}: {e}")
                # Continue with next file instead of failing
        
        if not dataframes:
            return None
        
        # Union all property DataFrames
        result = dataframes[0]
        for df in dataframes[1:]:
            result = result.unionByName(df, allowMissingColumns=False)
        
        logger.info(f"Loaded {result.count()} property records total")
        return result
    
    def _load_neighborhoods(self) -> Optional[DataFrame]:
        """
        Load and union all neighborhood data files.
        
        Returns:
            Combined neighborhood DataFrame or None if no data
        """
        if not self.config.neighborhoods:
            logger.info("No neighborhood files configured")
            return None
        
        dataframes = []
        for path in self.config.neighborhoods:
            try:
                logger.info(f"Loading neighborhoods from: {path}")
                df = self.neighborhood_loader.load(path)
                
                if self.neighborhood_loader.validate(df):
                    dataframes.append(df)
                    logger.info(f"✓ Successfully loaded {path}")
                else:
                    logger.warning(f"✗ Validation failed for {path}")
                    
            except Exception as e:
                logger.error(f"✗ Failed to load {path}: {e}")
                # Continue with next file instead of failing
        
        if not dataframes:
            return None
        
        # Union all neighborhood DataFrames
        result = dataframes[0]
        for df in dataframes[1:]:
            result = result.unionByName(df, allowMissingColumns=False)
        
        logger.info(f"Loaded {result.count()} neighborhood records total")
        return result
    
    def _load_wikipedia(self) -> Optional[DataFrame]:
        """
        Load Wikipedia data if configured.
        
        Returns:
            Wikipedia DataFrame or None
        """
        if not self.config.wikipedia.enabled:
            logger.info("Wikipedia loading disabled")
            return None
        
        try:
            logger.info(f"Loading Wikipedia from: {self.config.wikipedia.path}")
            df = self.wikipedia_loader.load(self.config.wikipedia.path)
            
            if self.wikipedia_loader.validate(df):
                logger.info(f"✓ Successfully loaded Wikipedia data with {df.count()} articles")
                return df
            else:
                logger.warning("✗ Wikipedia validation failed")
                return None
                
        except Exception as e:
            logger.error(f"✗ Failed to load Wikipedia: {e}")
            return None
    
    def _load_locations(self) -> Optional[DataFrame]:
        """
        Load location reference data if configured.
        
        Returns:
            Location DataFrame or None
        """
        if not self.config.locations.enabled:
            logger.info("Location loading disabled")
            return None
        
        try:
            logger.info(f"Loading locations from: {self.config.locations.path}")
            df = self.location_loader.load(self.config.locations.path)
            
            if self.location_loader.validate(df):
                logger.info(f"✓ Successfully loaded {df.count()} location records")
                return df
            else:
                logger.warning("✗ Location validation failed")
                return None
                
        except Exception as e:
            logger.error(f"✗ Failed to load locations: {e}")
            return None
    
    def get_location_broadcast(self):
        """
        Get the broadcast variable containing location reference data.
        
        Returns:
            Broadcast variable with location data or None
        """
        return self._location_broadcast
    
    def _log_summary(self, loaded_data: LoadedData) -> None:
        """
        Log summary statistics for loaded data.
        
        Args:
            loaded_data: LoadedData object containing all DataFrames
        """
        total = 0
        entity_counts = {}
        
        # Count records per entity type
        if loaded_data.properties is not None:
            count = loaded_data.properties.count()
            entity_counts["properties"] = count
            total += count
            
        if loaded_data.neighborhoods is not None:
            count = loaded_data.neighborhoods.count()
            entity_counts["neighborhoods"] = count
            total += count
            
        if loaded_data.wikipedia is not None:
            count = loaded_data.wikipedia.count()
            entity_counts["wikipedia"] = count
            total += count
            
        if loaded_data.locations is not None:
            count = loaded_data.locations.count()
            entity_counts["locations"] = count
            total += count
        
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Data Loading Complete: {total:,} total records")
        logger.info("=" * 60)
        
        # Log counts by entity type
        for entity_type, count in entity_counts.items():
            logger.info(f"  {entity_type}: {count:,} records")
        
        logger.info("=" * 60)