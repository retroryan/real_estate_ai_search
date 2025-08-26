"""
Orchestrator for coordinating entity-specific data loaders.

This module provides a clean interface to load data from all sources
and returns them as separate DataFrames for each entity type.
"""

import logging
from typing import Optional

from pydantic import BaseModel
from pyspark.sql import DataFrame, SparkSession

from data_pipeline.config.models import PipelineConfig, DataSourceConfig
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
    
    def __init__(self, spark: SparkSession, data_config: DataSourceConfig):
        """
        Initialize the data loader orchestrator.
        
        Args:
            spark: Active SparkSession
            data_config: Data source configuration
        """
        self.spark = spark
        self.data_config = data_config
        
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
        if not self.data_config.properties_files:
            logger.info("No property files configured")
            return None
        
        dataframes = []
        for path in self.data_config.properties_files:
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
        
        logger.info("✓ Property data loaded and combined")
        return result
    
    def _load_neighborhoods(self) -> Optional[DataFrame]:
        """
        Load and union all neighborhood data files.
        
        Returns:
            Combined neighborhood DataFrame or None if no data
        """
        if not self.data_config.neighborhoods_files:
            logger.info("No neighborhood files configured")
            return None
        
        dataframes = []
        for path in self.data_config.neighborhoods_files:
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
        
        logger.info("✓ Neighborhood data loaded and combined")
        return result
    
    def _load_wikipedia(self) -> Optional[DataFrame]:
        """
        Load Wikipedia data if configured.
        
        Returns:
            Wikipedia DataFrame or None
        """
        if not self.data_config.wikipedia_db_path:
            logger.info("No Wikipedia database path configured")
            return None
        
        try:
            logger.info(f"Loading Wikipedia from: {self.data_config.wikipedia_db_path}")
            df = self.wikipedia_loader.load(self.data_config.wikipedia_db_path)
            
            if self.wikipedia_loader.validate(df):
                logger.info("✓ Successfully loaded Wikipedia data")
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
        if not self.data_config.locations_file:
            logger.info("No locations file configured")
            return None
        
        try:
            logger.info(f"Loading locations from: {self.data_config.locations_file}")
            df = self.location_loader.load(self.data_config.locations_file)
            
            if self.location_loader.validate(df):
                logger.info("✓ Successfully loaded location data")
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
        Log summary of loaded data without forcing evaluation.
        
        Args:
            loaded_data: LoadedData object containing all DataFrames
        """
        # Log what data types were loaded
        loaded_entities = []
        
        if loaded_data.properties is not None:
            loaded_entities.append("properties")
            
        if loaded_data.neighborhoods is not None:
            loaded_entities.append("neighborhoods")
            
        if loaded_data.wikipedia is not None:
            loaded_entities.append("wikipedia")
            
        if loaded_data.locations is not None:
            loaded_entities.append("locations")
        
        if loaded_entities:
            logger.info("")
            logger.info("=" * 60)
            logger.info("Data Loading Complete")
            logger.info("=" * 60)
            
            # Log loaded entity types
            for entity_type in loaded_entities:
                logger.info(f"  ✓ {entity_type} loaded")
            
            logger.info("=" * 60)
        else:
            logger.warning("No data loaded from any source")