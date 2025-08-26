"""
County extraction from location data.

Simple module to extract county nodes from location hierarchy.
"""

import logging
from typing import List, Optional
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    collect_set,
    count,
    avg,
    lit,
    concat,
    lower,
    regexp_replace
)

from data_pipeline.models.graph_models import CountyNode

logger = logging.getLogger(__name__)


class CountyExtractor:
    """Extract county nodes from location data."""
    
    def __init__(self, spark: SparkSession):
        """
        Initialize the county extractor.
        
        Args:
            spark: Active SparkSession
        """
        self.spark = spark
    
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
            neighborhoods_df: Optional neighborhoods DataFrame for statistics
            
        Returns:
            DataFrame of CountyNode records
        """
        logger.info("Extracting counties from location data")
        
        # Extract unique counties from locations
        counties = locations_df.select(
            col("county").alias("name"),
            col("state")
        ).filter(
            col("county").isNotNull()
        ).distinct()
        
        # Add city count per county
        city_counts = locations_df.groupBy("county", "state").agg(
            count("city").alias("city_count")
        )
        
        counties = counties.join(
            city_counts,
            (counties["name"] == city_counts["county"]) & 
            (counties["state"] == city_counts["state"]),
            "left"
        ).select(
            counties["name"],
            counties["state"],
            city_counts["city_count"]
        )
        
        # Calculate median home price if properties available
        if properties_df:
            county_prices = properties_df.groupBy("county", "state").agg(
                avg("listing_price").alias("median_home_price")
            )
            
            counties = counties.join(
                county_prices,
                (counties["name"] == county_prices["county"]) & 
                (counties["state"] == county_prices["state"]),
                "left"
            ).select(
                counties["*"],
                county_prices["median_home_price"]
            )
        else:
            counties = counties.withColumn("median_home_price", lit(None))
        
        # Create CountyNode records
        county_nodes = []
        try:
            for row in counties.collect():
                if not row.get("name") or not row.get("state"):
                    logger.warning(f"Skipping county with missing name or state: {row}")
                    continue
                    
                county_id = f"county:{row['name'].lower().replace(' ', '_')}_{row['state'].lower()}"
                
                county_node = CountyNode(
                    id=county_id,
                    name=row["name"],
                    state=row["state"],
                    city_count=row.get("city_count", 0) if row.get("city_count") is not None else 0,
                    median_home_price=int(row["median_home_price"]) if row.get("median_home_price") else None
                )
                county_nodes.append(county_node.model_dump())
        except Exception as e:
            logger.error(f"Error creating county nodes: {e}")
        
        # Convert to DataFrame
        if county_nodes:
            return self.spark.createDataFrame(county_nodes)
        else:
            # Return empty DataFrame with correct schema
            return self.spark.createDataFrame([], CountyNode.spark_schema())
    
    def create_county_relationships(
        self,
        cities_df: Optional[DataFrame] = None,
        neighborhoods_df: Optional[DataFrame] = None
    ) -> DataFrame:
        """
        Create IN_COUNTY relationships for cities and neighborhoods.
        
        Args:
            cities_df: DataFrame with city data
            neighborhoods_df: DataFrame with neighborhood data
            
        Returns:
            DataFrame of IN_COUNTY relationships
        """
        logger.info("Creating IN_COUNTY relationships")
        
        relationships = []
        
        # Create city to county relationships
        if cities_df and "county" in cities_df.columns:
            city_county_rels = cities_df.filter(
                col("county").isNotNull()
            ).select(
                col("id").alias("from_id"),
                concat(
                    lit("county:"),
                    regexp_replace(lower(col("county")), " ", "_"),
                    lit("_"),
                    lower(col("state"))
                ).alias("to_id"),
                lit("IN_COUNTY").alias("relationship_type")
            )
            relationships.append(city_county_rels)
        
        # Create neighborhood to county relationships
        if neighborhoods_df and "county" in neighborhoods_df.columns:
            neighborhood_county_rels = neighborhoods_df.filter(
                col("county").isNotNull()
            ).select(
                col("neighborhood_id").alias("from_id"),
                concat(
                    lit("county:"),
                    regexp_replace(lower(col("county")), " ", "_"),
                    lit("_"),
                    lower(col("state"))
                ).alias("to_id"),
                lit("IN_COUNTY").alias("relationship_type")
            )
            relationships.append(neighborhood_county_rels)
        
        # Union all relationships
        if relationships:
            result = relationships[0]
            for rel_df in relationships[1:]:
                result = result.union(rel_df)
            return result
        else:
            # Return empty DataFrame with correct schema
            schema = ["from_id", "to_id", "relationship_type"]
            return self.spark.createDataFrame([], schema)