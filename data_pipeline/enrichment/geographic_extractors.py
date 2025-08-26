"""
Geographic entity extractors for City, County, and State nodes.

Clean, Pydantic-based extractors for creating geographic hierarchy nodes.
These extractors work with location data to build the geographic graph structure.
"""

import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col, count, avg, lit, concat_ws,
    lower, regexp_replace, when
)

from data_pipeline.models.graph_models import CityNode, CountyNode, StateNode
from data_pipeline.enrichment.id_generator import (
    generate_city_id, generate_county_id
)

logger = logging.getLogger(__name__)


class CityExtractor(BaseModel):
    """Extract city nodes from location data."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    spark: SparkSession
    
    def __init__(self, spark: SparkSession, **kwargs):
        """
        Initialize the city extractor.
        
        Args:
            spark: Active SparkSession
        """
        super().__init__(spark=spark, **kwargs)
    
    def extract_cities(
        self, 
        locations_df: DataFrame,
        properties_df: Optional[DataFrame] = None
    ) -> DataFrame:
        """
        Extract unique cities from location data.
        
        Args:
            locations_df: DataFrame with location hierarchy
            properties_df: Optional properties DataFrame for statistics
            
        Returns:
            DataFrame of CityNode records
        """
        logger.info("Extracting cities from location data")
        
        if locations_df is None:
            logger.warning("No locations DataFrame provided")
            return self.spark.createDataFrame([], CityNode.spark_schema())
        
        # Extract unique city-state combinations
        cities = locations_df.select(
            col("city").alias("name"),
            col("state"),
            col("county")
        ).filter(
            col("city").isNotNull() & col("state").isNotNull()
        ).distinct()
        
        # Generate city IDs
        cities = cities.withColumn(
            "id",
            concat_ws("_",
                lower(regexp_replace(col("name"), r"[^a-zA-Z0-9]", "")),
                lower(col("state"))
            )
        )
        
        # Add property statistics if available
        if properties_df:
            city_stats = properties_df.groupBy("city", "state").agg(
                count("*").alias("property_count"),
                avg("listing_price").alias("median_home_price")
            )
            
            cities = cities.join(
                city_stats,
                (cities["name"] == city_stats["city"]) & 
                (cities["state"] == city_stats["state"]),
                "left"
            ).drop("city")
        else:
            cities = cities.withColumn("property_count", lit(0))
            cities = cities.withColumn("median_home_price", lit(None))
        
        # Create CityNode records
        city_nodes = []
        try:
            for row in cities.collect():
                city_node = CityNode(
                    id=row["id"],
                    name=row["name"],
                    state=row["state"],
                    county=row["county"],
                    population=None,  # Not available in our data
                    median_home_price=row.get("median_home_price")
                )
                city_nodes.append(city_node.model_dump())
        except Exception as e:
            logger.error(f"Error creating city nodes: {e}")
        
        if city_nodes:
            logger.info(f"Created {len(city_nodes)} city nodes")
            return self.spark.createDataFrame(city_nodes, schema=CityNode.spark_schema())
        else:
            logger.warning("No city nodes created")
            return self.spark.createDataFrame([], CityNode.spark_schema())


class CountyExtractor(BaseModel):
    """Extract county nodes from location data."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    spark: SparkSession
    
    def __init__(self, spark: SparkSession, **kwargs):
        """
        Initialize the county extractor.
        
        Args:
            spark: Active SparkSession
        """
        super().__init__(spark=spark, **kwargs)
    
    def extract_counties(
        self,
        locations_df: DataFrame,
        properties_df: Optional[DataFrame] = None,
        neighborhoods_df: Optional[DataFrame] = None
    ) -> DataFrame:
        """
        Extract unique counties from location data.
        
        Args:
            locations_df: DataFrame with location hierarchy
            properties_df: Optional properties DataFrame for statistics
            neighborhoods_df: Optional neighborhoods DataFrame (not used)
            
        Returns:
            DataFrame of CountyNode records
        """
        logger.info("Extracting counties from location data")
        
        if locations_df is None:
            logger.warning("No locations DataFrame provided")
            return self.spark.createDataFrame([], CountyNode.spark_schema())
        
        # Extract unique county-state combinations
        counties = locations_df.select(
            col("county").alias("name"),
            col("state")
        ).filter(
            col("county").isNotNull() & col("state").isNotNull()
        ).distinct()
        
        # Generate county IDs
        counties = counties.withColumn(
            "id",
            concat_ws("_",
                lower(regexp_replace(col("name"), r"[^a-zA-Z0-9]", "")),
                lower(col("state"))
            )
        )
        
        # Add property statistics if available
        if properties_df and "county" in properties_df.columns:
            county_stats = properties_df.filter(col("county").isNotNull()).groupBy("county", "state").agg(
                count("*").alias("property_count"),
                avg("listing_price").alias("median_home_price")
            )
            
            counties = counties.join(
                county_stats,
                (counties["name"] == county_stats["county"]) & 
                (counties["state"] == county_stats["state"]),
                "left"
            ).drop("county")
        else:
            counties = counties.withColumn("property_count", lit(0))
            counties = counties.withColumn("median_home_price", lit(None))
        
        # Create CountyNode records
        county_nodes = []
        try:
            for row in counties.collect():
                county_node = CountyNode(
                    id=row["id"],
                    name=row["name"],
                    state=row["state"],
                    population=None,  # Not available in our data
                    median_home_price=row.get("median_home_price")
                )
                county_nodes.append(county_node.model_dump())
        except Exception as e:
            logger.error(f"Error creating county nodes: {e}")
        
        if county_nodes:
            logger.info(f"Created {len(county_nodes)} county nodes")
            return self.spark.createDataFrame(county_nodes, schema=CountyNode.spark_schema())
        else:
            logger.warning("No county nodes created")
            return self.spark.createDataFrame([], CountyNode.spark_schema())


class StateExtractor(BaseModel):
    """Extract state nodes from location data."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    spark: SparkSession
    state_names: Dict[str, str] = {
        "CA": "California",
        "NY": "New York",
        "TX": "Texas",
        "FL": "Florida",
        "IL": "Illinois",
        "PA": "Pennsylvania",
        "OH": "Ohio",
        "GA": "Georgia",
        "NC": "North Carolina",
        "MI": "Michigan"
        # Add more as needed
    }
    
    def __init__(self, spark: SparkSession, **kwargs):
        """
        Initialize the state extractor.
        
        Args:
            spark: Active SparkSession
        """
        super().__init__(spark=spark, **kwargs)
    
    def extract_states(
        self,
        locations_df: DataFrame,
        properties_df: Optional[DataFrame] = None
    ) -> DataFrame:
        """
        Extract unique states from location data.
        
        Args:
            locations_df: DataFrame with location hierarchy
            properties_df: Optional properties DataFrame for statistics
            
        Returns:
            DataFrame of StateNode records
        """
        logger.info("Extracting states from location data")
        
        if locations_df is None:
            logger.warning("No locations DataFrame provided")
            return self.spark.createDataFrame([], StateNode.spark_schema())
        
        # Extract unique states
        states = locations_df.select("state").filter(
            col("state").isNotNull()
        ).distinct()
        
        # Add property statistics if available
        if properties_df:
            state_stats = properties_df.groupBy("state").agg(
                count("*").alias("property_count")
            )
            
            states = states.join(
                state_stats,
                states["state"] == state_stats["state"],
                "left"
            )
        else:
            states = states.withColumn("property_count", lit(0))
        
        # Create StateNode records
        state_nodes = []
        try:
            for row in states.collect():
                state_abbr = row["state"]
                state_node = StateNode(
                    id=state_abbr,
                    name=self.state_names.get(state_abbr, state_abbr),
                    abbreviation=state_abbr
                )
                state_nodes.append(state_node.model_dump())
        except Exception as e:
            logger.error(f"Error creating state nodes: {e}")
        
        if state_nodes:
            logger.info(f"Created {len(state_nodes)} state nodes")
            return self.spark.createDataFrame(state_nodes, schema=StateNode.spark_schema())
        else:
            logger.warning("No state nodes created")
            return self.spark.createDataFrame([], StateNode.spark_schema())