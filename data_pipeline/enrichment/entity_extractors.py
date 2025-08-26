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
    
