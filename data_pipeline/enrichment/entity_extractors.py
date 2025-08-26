"""
Entity extractors for PropertyType and PriceRange nodes.

Simple extractors for creating entity nodes from property data.
"""

import logging
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    count,
    when,
    lit,
    concat
)

from data_pipeline.models.graph_models import PropertyTypeNode, PriceRangeNode, ZipCodeNode
from data_pipeline.enrichment.id_generator import generate_property_type_id, generate_price_range_id

logger = logging.getLogger(__name__)


class PropertyTypeExtractor(BaseModel):
    """Extract property type nodes from property data."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    spark: SparkSession
    type_descriptions: Dict[str, str] = {

            "single_family": "Single-family detached home",
            "condo": "Condominium unit",
            "townhome": "Townhouse or row house",
            "multi_family": "Multi-family property (duplex, triplex, etc.)",
            "land": "Vacant land or lot",
            "other": "Other property type"
        }
    
    def __init__(self, spark: SparkSession, **kwargs):
        """
        Initialize the property type extractor.
        
        Args:
            spark: Active SparkSession
        """
        super().__init__(spark=spark, **kwargs)
    
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
                    category="residential",  # All our property types are residential
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
    


class PriceRangeExtractor(BaseModel):
    """Extract price range nodes from property data."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    spark: SparkSession
    price_ranges: List[Dict[str, Any]] = [
            {"min": 0, "max": 500000, "label": "Under 500K", "segment": "entry"},
            {"min": 500000, "max": 1000000, "label": "500K-1M", "segment": "mid"},
            {"min": 1000000, "max": 2000000, "label": "1M-2M", "segment": "upper-mid"},
            {"min": 2000000, "max": 5000000, "label": "2M-5M", "segment": "luxury"},
            {"min": 5000000, "max": None, "label": "5M+", "segment": "ultra-luxury"}
        ]
    
    def __init__(self, spark: SparkSession, **kwargs):
        """
        Initialize the price range extractor.
        
        Args:
            spark: Active SparkSession
        """
        super().__init__(spark=spark, **kwargs)
    
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


class ZipCodeExtractor(BaseModel):
    """Extract ZIP code nodes from property and location data."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    spark: SparkSession
    
    def __init__(self, spark: SparkSession, **kwargs):
        """
        Initialize the ZIP code extractor.
        
        Args:
            spark: Active SparkSession
        """
        super().__init__(spark=spark, **kwargs)
    
    def extract_zip_codes(self, properties_df: DataFrame, locations_df: DataFrame = None) -> DataFrame:
        """
        Extract unique ZIP codes from properties and locations.
        
        Args:
            properties_df: DataFrame with properties containing zip_code field
            locations_df: Optional DataFrame with location data containing neighborhood ZIP mappings
            
        Returns:
            DataFrame of ZipCodeNode records
        """
        logger.info("Extracting ZIP codes from properties and locations")
        
        # Extract ZIP codes from properties
        property_zips = properties_df.select("zip_code").distinct().filter(
            col("zip_code").isNotNull()
        )
        
        # Count properties per ZIP code
        zip_counts = properties_df.groupBy("zip_code").agg(
            count("*").alias("property_count")
        ).filter(
            col("zip_code").isNotNull()
        )
        
        # Create ZipCodeNode records
        zip_nodes = []
        try:
            for row in zip_counts.collect():
                zip_code = row["zip_code"]
                if not zip_code:
                    continue
                
                # Create node with ZIP as both id and code
                zip_node = ZipCodeNode(
                    id=zip_code,
                    code=zip_code,
                    property_count=row["property_count"]
                )
                zip_nodes.append(zip_node.model_dump())
                
        except Exception as e:
            logger.error(f"Error creating ZIP code nodes: {e}")
        
        # Convert to DataFrame with proper schema
        if zip_nodes:
            logger.info(f"Created {len(zip_nodes)} ZIP code nodes")
            return self.spark.createDataFrame(zip_nodes, schema=ZipCodeNode.spark_schema())
        else:
            logger.warning("No ZIP codes extracted")
            return self.spark.createDataFrame([], ZipCodeNode.spark_schema())
    
