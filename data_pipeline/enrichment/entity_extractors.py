"""
Entity extractors for PropertyType and PriceRange nodes.

Simple extractors for creating entity nodes from property data.
"""

import logging
from typing import List, Dict
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    count,
    when,
    lit,
    concat
)

from data_pipeline.models.graph_models import PropertyTypeNode, PriceRangeNode
from data_pipeline.enrichment.id_generator import generate_property_type_id, generate_price_range_id

logger = logging.getLogger(__name__)


class PropertyTypeExtractor:
    """Extract property type nodes from property data."""
    
    def __init__(self, spark: SparkSession):
        """
        Initialize the property type extractor.
        
        Args:
            spark: Active SparkSession
        """
        self.spark = spark
        self.type_descriptions = {
            "single_family": "Single-family detached home",
            "condo": "Condominium unit",
            "townhome": "Townhouse or row house",
            "multi_family": "Multi-family property (duplex, triplex, etc.)",
            "land": "Vacant land or lot",
            "other": "Other property type"
        }
    
    def extract_property_types(self, properties_df: DataFrame) -> DataFrame:
        """
        Extract unique property types from properties.
        
        Args:
            properties_df: DataFrame with properties
            
        Returns:
            DataFrame of PropertyTypeNode records
        """
        logger.info("Extracting property types from properties")
        
        # Count properties by type
        type_counts = properties_df.groupBy("property_type").agg(
            count("*").alias("property_count")
        ).filter(
            col("property_type").isNotNull()
        )
        
        # Create PropertyType nodes
        type_nodes = []
        try:
            for row in type_counts.collect():
                prop_type = row["property_type"]
                if not prop_type:
                    logger.warning("Skipping property type with no value")
                    continue
                
                type_node = PropertyTypeNode(
                    id=generate_property_type_id(prop_type),
                    name=prop_type,
                    label=prop_type.replace("_", " ").title(),
                    description=self.type_descriptions.get(prop_type, f"{prop_type} property"),
                    property_count=row["property_count"]
                )
                type_nodes.append(type_node.model_dump())
        except Exception as e:
            logger.error(f"Error creating property type nodes: {e}")
        
        # Convert to DataFrame with proper schema
        if type_nodes:
            return self.spark.createDataFrame(type_nodes, schema=PropertyTypeNode.spark_schema())
        else:
            return self.spark.createDataFrame([], PropertyTypeNode.spark_schema())
    
    def create_property_type_relationships(self, properties_df: DataFrame) -> DataFrame:
        """
        Create OF_TYPE relationships between properties and property types.
        
        Args:
            properties_df: DataFrame with properties
            
        Returns:
            DataFrame of OF_TYPE relationships
        """
        logger.info("Creating OF_TYPE relationships")
        
        relationships = properties_df.filter(
            col("property_type").isNotNull()
        ).select(
            col("listing_id").alias("from_id"),
            # Note: Can't use generate_property_type_id in Spark SQL, so we replicate its logic
            concat(lit("property_type:"), col("property_type")).alias("to_id"),
            lit("OF_TYPE").alias("relationship_type")
        )
        
        return relationships


class PriceRangeExtractor:
    """Extract price range nodes from property data."""
    
    def __init__(self, spark: SparkSession):
        """
        Initialize the price range extractor.
        
        Args:
            spark: Active SparkSession
        """
        self.spark = spark
        self.price_ranges = [
            {"min": 0, "max": 500000, "label": "Under 500K", "segment": "entry"},
            {"min": 500000, "max": 1000000, "label": "500K-1M", "segment": "mid"},
            {"min": 1000000, "max": 2000000, "label": "1M-2M", "segment": "upper-mid"},
            {"min": 2000000, "max": 5000000, "label": "2M-5M", "segment": "luxury"},
            {"min": 5000000, "max": None, "label": "5M+", "segment": "ultra-luxury"}
        ]
    
    def extract_price_ranges(self, properties_df: DataFrame) -> DataFrame:
        """
        Extract price ranges and count properties in each.
        
        Args:
            properties_df: DataFrame with properties
            
        Returns:
            DataFrame of PriceRangeNode records
        """
        logger.info("Extracting price ranges from properties")
        
        # Create price range nodes
        range_nodes = []
        
        for range_def in self.price_ranges:
            # Count properties in this range
            if range_def["max"] is not None:
                condition = (col("listing_price") >= range_def["min"]) & \
                           (col("listing_price") < range_def["max"])
            else:
                condition = col("listing_price") >= range_def["min"]
            
            count_in_range = properties_df.filter(condition).count()
            
            range_node = PriceRangeNode(
                id=generate_price_range_id(range_def["label"]),
                label=range_def["label"],
                min_price=range_def["min"],
                max_price=range_def["max"],
                market_segment=range_def["segment"],
                property_count=count_in_range
            )
            range_nodes.append(range_node.model_dump())
        
        # Convert to DataFrame with proper schema
        return self.spark.createDataFrame(range_nodes, schema=PriceRangeNode.spark_schema())
    
    def create_price_range_relationships(self, properties_df: DataFrame) -> DataFrame:
        """
        Create IN_PRICE_RANGE relationships between properties and price ranges.
        
        Args:
            properties_df: DataFrame with properties
            
        Returns:
            DataFrame of IN_PRICE_RANGE relationships
        """
        logger.info("Creating IN_PRICE_RANGE relationships")
        
        # Add price range to each property
        df = properties_df.filter(col("listing_price").isNotNull())
        
        # Determine price range for each property
        df = df.withColumn(
            "price_range_id",
            # Note: Can't use generate_price_range_id in Spark SQL, so we replicate its logic
            when(col("listing_price") < 500000, "price_range:under_500k")
            .when((col("listing_price") >= 500000) & (col("listing_price") < 1000000), 
                  "price_range:500k_1m")
            .when((col("listing_price") >= 1000000) & (col("listing_price") < 2000000), 
                  "price_range:1m_2m")
            .when((col("listing_price") >= 2000000) & (col("listing_price") < 5000000), 
                  "price_range:2m_5m")
            .otherwise("price_range:5mplus")
        )
        
        # Create relationships
        relationships = df.select(
            col("listing_id").alias("from_id"),
            col("price_range_id").alias("to_id"),
            lit("IN_PRICE_RANGE").alias("relationship_type")
        )
        
        return relationships