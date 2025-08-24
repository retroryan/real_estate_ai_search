"""
Location data enrichment engine.

This module provides location enhancement capabilities for all entity types,
including hierarchy resolution, name standardization, and relationship mapping.
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    broadcast,
    col,
    coalesce,
    lit,
    trim,
    upper,
    when,
    concat_ws,
    expr,
)
from pyspark.sql.types import StringType

logger = logging.getLogger(__name__)


class LocationEnrichmentConfig(BaseModel):
    """Configuration for location enrichment operations."""
    
    enable_hierarchy_resolution: bool = Field(
        default=True,
        description="Resolve complete geographic hierarchy for locations"
    )
    
    enable_name_standardization: bool = Field(
        default=True,
        description="Standardize location names using canonical forms"
    )
    
    enable_neighborhood_linking: bool = Field(
        default=True,
        description="Link entities to neighborhoods via neighborhood_id"
    )
    
    enable_parent_relationships: bool = Field(
        default=True,
        description="Establish parent location relationships"
    )
    
    state_name_mappings: Dict[str, str] = Field(
        default_factory=lambda: {
            "CA": "California",
            "UT": "Utah",
            "NY": "New York",
            "TX": "Texas",
            "FL": "Florida",
            "WA": "Washington",
            "OR": "Oregon",
            "NV": "Nevada",
            "AZ": "Arizona",
            "CO": "Colorado"
        },
        description="State abbreviation to full name mappings"
    )


class LocationEnricher:
    """
    Provides location enhancement capabilities for all entity types.
    
    Uses broadcast location reference data to enhance entities with proper
    geographic hierarchy, standardized names, and relationship mapping.
    """
    
    def __init__(self, spark: SparkSession, location_broadcast: Any, 
                 config: Optional[LocationEnrichmentConfig] = None):
        """
        Initialize the location enricher.
        
        Args:
            spark: Active SparkSession
            location_broadcast: Broadcast variable containing location reference data
            config: Location enrichment configuration
        """
        self.spark = spark
        self.location_broadcast = location_broadcast
        self.config = config or LocationEnrichmentConfig()
        
        # Create location lookup DataFrames from broadcast data
        if location_broadcast is not None:
            self._create_location_lookups()
    
    def _create_location_lookups(self):
        """Create efficient lookup DataFrames from broadcast location data."""
        try:
            # Convert broadcast data to DataFrame for efficient joins
            location_data = self.location_broadcast.value
            
            if location_data:
                # Create DataFrame from broadcast data
                self.location_df = self.spark.createDataFrame(location_data)
                
                # Create specific lookup tables
                self._create_neighborhood_lookup()
                self._create_city_lookup() 
                self._create_state_lookup()
                
                logger.info(f"Created location lookups from {len(location_data)} reference records")
            else:
                logger.warning("Location broadcast data is empty")
                self._create_empty_lookups()
                
        except Exception as e:
            logger.error(f"Failed to create location lookups: {e}")
            self._create_empty_lookups()
    
    def _create_empty_lookups(self):
        """Create empty lookup DataFrames as fallback."""
        empty_schema = self.spark.createDataFrame([], "state string, county string, city string, neighborhood string")
        self.location_df = empty_schema
        self.neighborhood_lookup_df = empty_schema
        self.city_lookup_df = empty_schema
        self.state_lookup_df = empty_schema
    
    def _create_neighborhood_lookup(self):
        """Create neighborhood-specific lookup DataFrame."""
        self.neighborhood_lookup_df = self.location_df.filter(
            col("neighborhood").isNotNull()
        ).select(
            col("neighborhood"),
            col("city"),
            col("county"),
            col("state")
        ).distinct()
    
    def _create_city_lookup(self):
        """Create city-specific lookup DataFrame.""" 
        self.city_lookup_df = self.location_df.filter(
            col("city").isNotNull()
        ).select(
            col("city"),
            col("county"), 
            col("state")
        ).distinct()
    
    def _create_state_lookup(self):
        """Create state-specific lookup DataFrame."""
        self.state_lookup_df = self.location_df.filter(
            col("state").isNotNull()
        ).select(
            col("state")
        ).distinct()
    
    def enhance_with_hierarchy(self, df: DataFrame, 
                             city_col: str = "city", 
                             state_col: str = "state") -> DataFrame:
        """
        Enhance DataFrame with complete geographic hierarchy.
        
        Args:
            df: DataFrame to enhance
            city_col: Name of city column 
            state_col: Name of state column
            
        Returns:
            DataFrame with enhanced location hierarchy
        """
        if not self.config.enable_hierarchy_resolution:
            return df
        
        try:
            # Join with city lookup to add county information
            # Alias the lookup DataFrame to avoid column name conflicts
            city_lookup_aliased = self.city_lookup_df.alias("lookup")
            enhanced_df = df.alias("main").join(
                broadcast(city_lookup_aliased),
                (col(f"main.{city_col}") == col("lookup.city")) & 
                (col(f"main.{state_col}") == col("lookup.state")),
                "left"
            ).select(
                col("main.*"),
                coalesce(col("lookup.county"), lit(None)).alias("county_resolved")
            )
            
            logger.info("Enhanced DataFrame with location hierarchy")
            return enhanced_df
            
        except Exception as e:
            logger.error(f"Failed to enhance with hierarchy: {e}")
            return df
    
    def link_to_neighborhood(self, df: DataFrame,
                           neighborhood_col: str = "neighborhood_name",
                           city_col: str = "city",
                           state_col: str = "state") -> DataFrame:
        """
        Link DataFrame records to neighborhoods and add neighborhood_id.
        
        Args:
            df: DataFrame to enhance
            neighborhood_col: Name of neighborhood column
            city_col: Name of city column  
            state_col: Name of state column
            
        Returns:
            DataFrame with neighborhood linking
        """
        if not self.config.enable_neighborhood_linking:
            return df
        
        try:
            # Create neighborhood_id from neighborhood + city + state
            neighborhood_enhanced = self.neighborhood_lookup_df.withColumn(
                "neighborhood_id",
                concat_ws("_",
                    upper(trim(col("neighborhood"))),
                    upper(trim(col("city"))), 
                    upper(trim(col("state")))
                )
            )
            
            # Join with neighborhood lookup
            # Alias DataFrames to avoid column name conflicts  
            neighborhood_aliased = neighborhood_enhanced.alias("nbh")
            enhanced_df = df.alias("main").join(
                broadcast(neighborhood_aliased),
                (trim(col(f"main.{neighborhood_col}")) == trim(col("nbh.neighborhood"))) &
                (trim(col(f"main.{city_col}")) == trim(col("nbh.city"))) &
                (trim(col(f"main.{state_col}")) == trim(col("nbh.state"))),
                "left"
            ).select(
                col("main.*"),
                col("nbh.neighborhood_id")
            )
            
            logger.info("Linked DataFrame records to neighborhoods")
            return enhanced_df
            
        except Exception as e:
            logger.error(f"Failed to link to neighborhoods: {e}")
            return df
    
    def standardize_location_names(self, df: DataFrame,
                                 city_col: str = "city",
                                 state_col: str = "state",
                                 neighborhood_col: Optional[str] = None) -> DataFrame:
        """
        Standardize location names using canonical reference data.
        
        Args:
            df: DataFrame to enhance
            city_col: Name of city column
            state_col: Name of state column
            neighborhood_col: Optional neighborhood column name
            
        Returns:
            DataFrame with standardized location names
        """
        if not self.config.enable_name_standardization:
            return df
        
        try:
            enhanced_df = df
            
            # Standardize city and state names
            city_state_lookup = self.city_lookup_df.select(
                col("city").alias("canonical_city"),
                col("state").alias("canonical_state")
            ).distinct()
            
            enhanced_df = enhanced_df.join(
                broadcast(city_state_lookup),
                (upper(trim(col(city_col))) == upper(trim(col("canonical_city")))) &
                (upper(trim(col(state_col))) == upper(trim(col("canonical_state")))),
                "left"
            ).withColumn(
                f"{city_col}_standardized",
                coalesce(col("canonical_city"), col(city_col))
            ).withColumn(
                f"{state_col}_standardized", 
                coalesce(col("canonical_state"), col(state_col))
            ).drop("canonical_city", "canonical_state")
            
            # Standardize neighborhood names if column provided
            if neighborhood_col:
                neighborhood_lookup = self.neighborhood_lookup_df.select(
                    col("neighborhood").alias("canonical_neighborhood"),
                    col("city").alias("neighborhood_city"),
                    col("state").alias("neighborhood_state")
                ).distinct()
                
                enhanced_df = enhanced_df.join(
                    broadcast(neighborhood_lookup),
                    (upper(trim(col(neighborhood_col))) == upper(trim(col("canonical_neighborhood")))) &
                    (upper(trim(col(f"{city_col}_standardized"))) == upper(trim(col("neighborhood_city")))) &
                    (upper(trim(col(f"{state_col}_standardized"))) == upper(trim(col("neighborhood_state")))),
                    "left"
                ).withColumn(
                    f"{neighborhood_col}_standardized",
                    coalesce(col("canonical_neighborhood"), col(neighborhood_col))
                ).drop("canonical_neighborhood", "neighborhood_city", "neighborhood_state")
            
            logger.info("Standardized location names using reference data")
            return enhanced_df
            
        except Exception as e:
            logger.error(f"Failed to standardize location names: {e}")
            return df
    
    def normalize_state_names(self, df: DataFrame, state_col: str = "state") -> DataFrame:
        """
        Normalize state names from abbreviations to full names.
        
        Args:
            df: DataFrame to process
            state_col: Name of state column
            
        Returns:
            DataFrame with normalized state names
        """
        if not self.config.enable_name_standardization:
            return df
        
        try:
            # Create a mapping DataFrame from config
            from pyspark.sql import Row
            mappings = [Row(state_abbr=k, state_full=v) for k, v in self.config.state_name_mappings.items()]
            mapping_df = self.spark.createDataFrame(mappings)
            
            # Join with mapping to get full state names
            enhanced_df = df.join(
                broadcast(mapping_df),
                upper(trim(col(state_col))) == upper(trim(col("state_abbr"))),
                "left"
            ).withColumn(
                f"{state_col}_normalized",
                coalesce(col("state_full"), col(state_col))
            ).drop("state_abbr", "state_full")
            
            # Replace original state column with normalized version
            enhanced_df = enhanced_df.drop(state_col).withColumnRenamed(f"{state_col}_normalized", state_col)
            
            logger.info(f"Normalized state names in {state_col} column")
            return enhanced_df
            
        except Exception as e:
            logger.error(f"Failed to normalize state names: {e}")
            return df
    
    def establish_parent_relationships(self, df: DataFrame) -> DataFrame:
        """
        Establish parent location relationships for geographic hierarchy.
        
        Args:
            df: DataFrame to enhance
            
        Returns:
            DataFrame with parent relationship fields
        """
        if not self.config.enable_parent_relationships:
            return df
        
        try:
            # Add hierarchy path and parent information
            # Check which columns exist to avoid ambiguity
            df_columns = df.columns
            
            # Build location hierarchy with available columns
            hierarchy_parts = []
            if "neighborhood" in df_columns:
                hierarchy_parts.append(when(df["neighborhood"].isNotNull(), df["neighborhood"]).otherwise(lit("")))
            if "city" in df_columns:
                hierarchy_parts.append(when(df["city"].isNotNull(), df["city"]).otherwise(lit("")))
            if "county_resolved" in df_columns:
                hierarchy_parts.append(when(df["county_resolved"].isNotNull(), df["county_resolved"]).otherwise(lit("")))
            if "state" in df_columns:
                hierarchy_parts.append(when(df["state"].isNotNull(), df["state"]).otherwise(lit("")))
            
            enhanced_df = df
            
            if hierarchy_parts:
                enhanced_df = enhanced_df.withColumn(
                    "location_hierarchy",
                    concat_ws(" > ", *hierarchy_parts)
                )
            
            # Add parent relationship columns if source columns exist
            if "neighborhood" in df_columns and "city" in df_columns:
                enhanced_df = enhanced_df.withColumn(
                    "parent_city",
                    when(df["neighborhood"].isNotNull(), df["city"]).otherwise(lit(None))
                )
            
            if "city" in df_columns and "county_resolved" in df_columns:
                enhanced_df = enhanced_df.withColumn(
                    "parent_county", 
                    when(df["city"].isNotNull(), df["county_resolved"]).otherwise(lit(None))
                )
            
            if "state" in df_columns and ("county_resolved" in df_columns or "city" in df_columns):
                state_condition = lit(False)
                if "county_resolved" in df_columns:
                    state_condition = state_condition | df["county_resolved"].isNotNull()
                if "city" in df_columns:
                    state_condition = state_condition | df["city"].isNotNull()
                    
                enhanced_df = enhanced_df.withColumn(
                    "parent_state",
                    when(state_condition, df["state"]).otherwise(lit(None))
                )
            
            logger.info("Established parent location relationships")
            return enhanced_df
            
        except Exception as e:
            logger.error(f"Failed to establish parent relationships: {e}")
            return df