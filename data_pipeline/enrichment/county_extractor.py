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
from data_pipeline.enrichment.id_generator import generate_county_id

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
            col("state").alias("county_state")
        ).filter(
            col("county").isNotNull()
        ).distinct()
        
        # Add city count per county
        city_counts = locations_df.groupBy("county", "state").agg(
            count("city").alias("city_count")
        ).select(
            col("county").alias("cc_county"),
            col("state").alias("cc_state"),
            col("city_count")
        )
        
        counties = counties.join(
            city_counts,
            (counties["name"] == city_counts["cc_county"]) & 
            (counties["county_state"] == city_counts["cc_state"]),
            "left"
        ).select(
            col("name"),
            col("county_state").alias("state"),
            col("city_count")
        )
        
        # Calculate median home price if properties available
        if properties_df:
            county_prices = properties_df.groupBy("county", "state").agg(
                avg("listing_price").alias("median_home_price")
            ).select(
                col("county").alias("cp_county"),
                col("state").alias("cp_state"),
                col("median_home_price")
            )
            
            counties = counties.join(
                county_prices,
                (counties["name"] == county_prices["cp_county"]) & 
                (counties["state"] == county_prices["cp_state"]),
                "left"
            ).select(
                col("name"),
                col("state"),
                col("city_count"),
                col("median_home_price")
            )
        else:
            counties = counties.withColumn("median_home_price", lit(None))
        
        # Create CountyNode records
        county_nodes = []
        try:
            for row in counties.collect():
                # Check for required fields using row indexing
                if not row["name"] or not row["state"]:
                    logger.warning(f"Skipping county with missing name or state: {row}")
                    continue
                    
                county_id = generate_county_id(row['name'], row['state'])
                
                # Handle optional fields safely
                city_count = row["city_count"] if row["city_count"] is not None else 0
                median_price = int(row["median_home_price"]) if row["median_home_price"] else None
                
                county_node = CountyNode(
                    id=county_id,
                    name=row["name"],
                    state=row["state"],
                    city_count=city_count,
                    median_home_price=median_price
                )
                county_nodes.append(county_node.model_dump())
        except Exception as e:
            logger.error(f"Error creating county nodes: {e}")
        
        # Convert to DataFrame
        if county_nodes:
            return self.spark.createDataFrame(county_nodes, schema=CountyNode.spark_schema())
        else:
            # Return empty DataFrame with correct schema
            return self.spark.createDataFrame([], CountyNode.spark_schema())
    
