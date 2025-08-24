"""
Neo4j writer for Property entities.

This module provides a Neo4j writer specifically for Property entities,
creating Property nodes and their relationships in the graph database.
"""

import logging
from typing import Any, Dict, List, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, when, lit, array, struct

from data_pipeline.config.models import Neo4jConfig
from data_pipeline.writers.base import DataWriter
from data_pipeline.graph_models import PropertyNode, GraphConfiguration
from data_pipeline.schemas.entity_schemas import PropertySchema

logger = logging.getLogger(__name__)


class PropertyNeo4jWriter(DataWriter):
    """
    Neo4j writer specifically for Property entities.
    
    Creates Property nodes with all relevant attributes and establishes
    LOCATED_IN relationships to neighborhoods and SIMILAR_TO relationships
    between similar properties.
    """
    
    def __init__(self, config: Neo4jConfig, spark: SparkSession):
        """
        Initialize the Property Neo4j writer.
        
        Args:
            config: Neo4j configuration
            spark: SparkSession instance
        """
        super().__init__(config)
        self.config = config
        self.spark = spark
        self.logger = logging.getLogger(__name__)
        
        # Neo4j Spark connector format
        self.format_string = "org.neo4j.spark.DataSource"
        
        # Graph configuration for similarity thresholds
        self.graph_config = GraphConfiguration()
    
    def validate_connection(self) -> bool:
        """
        Validate the connection to Neo4j.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            test_df = (self.spark.read
                      .format(self.format_string)
                      .option("url", self.config.uri)
                      .option("authentication.basic.username", self.config.username)
                      .option("authentication.basic.password", self.config.get_password() or "")
                      .option("database", self.config.database)
                      .option("query", "RETURN 1 as test")
                      .load())
            
            test_df.collect()
            self.logger.info(f"Successfully validated Neo4j connection for PropertyWriter")
            return True
            
        except Exception as e:
            self.logger.error(f"Property Neo4j connection validation failed: {e}")
            return False
    
    def write(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write Property nodes and relationships to Neo4j.
        
        Args:
            df: DataFrame containing property data (must match PropertySchema)
            metadata: Metadata about the data being written
            
        Returns:
            True if write was successful, False otherwise
        """
        try:
            # Validate DataFrame has required columns
            if not self._validate_dataframe(df):
                return False
            
            # Transform DataFrame for Neo4j
            properties_df = self._prepare_property_nodes(df)
            
            # Write Property nodes
            self._write_property_nodes(properties_df)
            
            # Create LOCATED_IN relationships to neighborhoods
            if "neighborhood_id" in df.columns:
                self._create_located_in_relationships(properties_df)
            
            # Create SIMILAR_TO relationships between properties
            if properties_df.count() > 1:
                self._create_similar_relationships(properties_df)
            
            self.logger.info(f"Successfully wrote {properties_df.count()} Property nodes to Neo4j")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write properties to Neo4j: {e}")
            return False
    
    def _validate_dataframe(self, df: DataFrame) -> bool:
        """
        Validate that DataFrame contains required property columns.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_columns = {"listing_id", "city", "state", "latitude", "longitude"}
        df_columns = set(df.columns)
        
        missing = required_columns - df_columns
        if missing:
            self.logger.error(f"Missing required columns for Property nodes: {missing}")
            return False
        
        return True
    
    def _prepare_property_nodes(self, df: DataFrame) -> DataFrame:
        """
        Prepare DataFrame for Property node creation.
        
        Args:
            df: Raw property DataFrame
            
        Returns:
            Transformed DataFrame ready for Neo4j
        """
        # Create node ID and ensure all required fields
        prepared_df = df.select(
            col("listing_id").alias("id"),
            col("listing_id").alias("property_id"),
            when(col("street").isNotNull(), col("street")).otherwise("").alias("address"),
            col("city"),
            col("state"),
            when(col("zip_code").isNotNull(), col("zip_code")).otherwise("").alias("zip_code"),
            col("latitude").cast("double"),
            col("longitude").cast("double"),
            when(col("property_type").isNotNull(), col("property_type")).otherwise("other").alias("property_type"),
            when(col("bedrooms").isNotNull(), col("bedrooms")).otherwise(0).alias("bedrooms"),
            when(col("bathrooms").isNotNull(), col("bathrooms")).otherwise(0.0).alias("bathrooms"),
            when(col("square_feet").isNotNull(), col("square_feet")).otherwise(0).alias("square_feet"),
            when(col("price").isNotNull(), col("price")).otherwise(0).alias("listing_price"),
            when(col("year_built").isNotNull(), col("year_built")).otherwise(0).alias("year_built"),
            when(col("description").isNotNull(), col("description")).otherwise("").alias("description"),
            when(col("features").isNotNull(), col("features")).otherwise(array()).alias("features")
        )
        
        # Add calculated fields
        prepared_df = prepared_df.withColumn(
            "price_per_sqft",
            when((col("listing_price") > 0) & (col("square_feet") > 0),
                 col("listing_price") / col("square_feet")
            ).otherwise(0.0)
        )
        
        # Add neighborhood reference if available
        if "neighborhood_id" in df.columns:
            prepared_df = prepared_df.join(
                df.select("listing_id", "neighborhood_id"),
                on="listing_id",
                how="left"
            )
        
        return prepared_df
    
    def _write_property_nodes(self, df: DataFrame) -> None:
        """
        Write Property nodes to Neo4j.
        
        Args:
            df: DataFrame containing prepared property nodes
        """
        count = df.count()
        if count == 0:
            self.logger.warning("No Property nodes to write")
            return
        
        self.logger.info(f"Writing {count} Property nodes to Neo4j...")
        
        (df.write
         .format(self.format_string)
         .mode("append")
         .option("url", self.config.uri)
         .option("authentication.basic.username", self.config.username)
         .option("authentication.basic.password", self.config.get_password() or "")
         .option("database", self.config.database)
         .option("labels", ":Property")
         .option("node.keys", "id")
         .option("batch.size", str(self.config.transaction_size))
         .save())
    
    def _create_located_in_relationships(self, df: DataFrame) -> None:
        """
        Create LOCATED_IN relationships between Properties and Neighborhoods.
        
        Args:
            df: DataFrame with property and neighborhood IDs
        """
        # Filter for properties with neighborhood assignments
        relationships_df = df.filter(col("neighborhood_id").isNotNull()).select(
            col("property_id").alias("from_id"),
            col("neighborhood_id").alias("to_id")
        ).distinct()
        
        count = relationships_df.count()
        if count == 0:
            self.logger.info("No Property-Neighborhood relationships to create")
            return
        
        self.logger.info(f"Creating {count} Property LOCATED_IN Neighborhood relationships...")
        
        cypher = """
        MATCH (p:Property {id: from_id})
        MATCH (n:Neighborhood {id: to_id})
        MERGE (p)-[:LOCATED_IN]->(n)
        """
        
        (relationships_df.write
         .format(self.format_string)
         .mode("append")
         .option("url", self.config.uri)
         .option("authentication.basic.username", self.config.username)
         .option("authentication.basic.password", self.config.get_password() or "")
         .option("database", self.config.database)
         .option("query", cypher)
         .option("batch.size", str(self.config.transaction_size))
         .save())
    
    def _create_similar_relationships(self, df: DataFrame) -> None:
        """
        Create SIMILAR_TO relationships between similar properties.
        
        Properties are considered similar if they:
        - Are in the same city
        - Have similar prices (within 20%)
        - Have similar sizes (within 20%)
        
        Args:
            df: DataFrame with property data
        """
        # Self-join to find similar properties
        p1 = df.alias("p1")
        p2 = df.alias("p2")
        
        # Define similarity thresholds
        price_threshold = 0.2  # 20% price difference
        size_threshold = 0.2   # 20% size difference
        
        similar_df = p1.join(
            p2,
            (p1.property_id < p2.property_id) &  # Avoid duplicates
            (p1.city == p2.city) &
            (p1.listing_price > 0) & (p2.listing_price > 0) &
            (p1.square_feet > 0) & (p2.square_feet > 0) &
            (((p1.listing_price - p2.listing_price).cast("double") / p1.listing_price).abs() < price_threshold) &
            (((p1.square_feet - p2.square_feet).cast("double") / p1.square_feet).abs() < size_threshold),
            "inner"
        ).select(
            p1.property_id.alias("from_id"),
            p2.property_id.alias("to_id"),
            lit(1.0).alias("similarity_score")  # Could calculate actual score
        ).distinct()
        
        # Limit similar properties per node
        count = similar_df.count()
        if count == 0:
            self.logger.info("No similar Property relationships found")
            return
        
        # Limit to reasonable number of relationships
        max_relationships = 1000
        if count > max_relationships:
            self.logger.info(f"Limiting similar relationships from {count} to {max_relationships}")
            similar_df = similar_df.limit(max_relationships)
            count = max_relationships
        
        self.logger.info(f"Creating {count} SIMILAR_TO relationships between properties...")
        
        cypher = """
        MATCH (p1:Property {id: from_id})
        MATCH (p2:Property {id: to_id})
        MERGE (p1)-[:SIMILAR_TO {similarity_score: similarity_score}]->(p2)
        """
        
        (similar_df.write
         .format(self.format_string)
         .mode("append")
         .option("url", self.config.uri)
         .option("authentication.basic.username", self.config.username)
         .option("authentication.basic.password", self.config.get_password() or "")
         .option("database", self.config.database)
         .option("query", cypher)
         .option("batch.size", str(self.config.transaction_size))
         .save())
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "neo4j_properties"