"""
Neo4j writer for Neighborhood entities.

This module provides a Neo4j writer specifically for Neighborhood entities,
creating Neighborhood nodes and their relationships in the graph database.
"""

import logging
from typing import Any, Dict, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, when, lit, array, concat_ws, avg

from data_pipeline.config.models import Neo4jConfig
from data_pipeline.writers.base import DataWriter
from data_pipeline.graph_models import NeighborhoodNode, GraphConfiguration
from data_pipeline.schemas.entity_schemas import NeighborhoodSchema

logger = logging.getLogger(__name__)


class NeighborhoodNeo4jWriter(DataWriter):
    """
    Neo4j writer specifically for Neighborhood entities.
    
    Creates Neighborhood nodes with demographics and characteristics,
    establishes LOCATED_IN relationships to cities, and CONTAINS
    relationships from neighborhoods to properties.
    """
    
    def __init__(self, config: Neo4jConfig, spark: SparkSession):
        """
        Initialize the Neighborhood Neo4j writer.
        
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
        
        # Graph configuration
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
            self.logger.info(f"Successfully validated Neo4j connection for NeighborhoodWriter")
            return True
            
        except Exception as e:
            self.logger.error(f"Neighborhood Neo4j connection validation failed: {e}")
            return False
    
    def write(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write Neighborhood nodes and relationships to Neo4j.
        
        Args:
            df: DataFrame containing neighborhood data (must match NeighborhoodSchema)
            metadata: Metadata about the data being written
            
        Returns:
            True if write was successful, False otherwise
        """
        try:
            # Validate DataFrame has required columns
            if not self._validate_dataframe(df):
                return False
            
            # Transform DataFrame for Neo4j
            neighborhoods_df = self._prepare_neighborhood_nodes(df)
            
            # Write Neighborhood nodes
            self._write_neighborhood_nodes(neighborhoods_df)
            
            # Create City nodes from neighborhoods
            cities_df = self._extract_cities(neighborhoods_df)
            if cities_df.count() > 0:
                self._write_city_nodes(cities_df)
                self._create_located_in_relationships(neighborhoods_df, cities_df)
            
            # Create State nodes from cities
            if cities_df.count() > 0:
                states_df = self._extract_states(cities_df)
                if states_df.count() > 0:
                    self._write_state_nodes(states_df)
                    self._create_part_of_relationships(cities_df, states_df)
            
            self.logger.info(f"Successfully wrote {neighborhoods_df.count()} Neighborhood nodes to Neo4j")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write neighborhoods to Neo4j: {e}")
            return False
    
    def _validate_dataframe(self, df: DataFrame) -> bool:
        """
        Validate that DataFrame contains required neighborhood columns.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_columns = {"neighborhood_id", "name", "city", "state"}
        df_columns = set(df.columns)
        
        missing = required_columns - df_columns
        if missing:
            self.logger.error(f"Missing required columns for Neighborhood nodes: {missing}")
            return False
        
        return True
    
    def _prepare_neighborhood_nodes(self, df: DataFrame) -> DataFrame:
        """
        Prepare DataFrame for Neighborhood node creation.
        
        Args:
            df: Raw neighborhood DataFrame
            
        Returns:
            Transformed DataFrame ready for Neo4j
        """
        # Create node ID and ensure all required fields
        prepared_df = df.select(
            col("neighborhood_id").alias("id"),
            col("neighborhood_id"),
            col("name"),
            col("city"),
            col("state"),
            when(col("latitude").isNotNull(), col("latitude")).otherwise(0.0).alias("latitude"),
            when(col("longitude").isNotNull(), col("longitude")).otherwise(0.0).alias("longitude"),
            when(col("description").isNotNull(), col("description")).otherwise("").alias("description"),
            when(col("population").isNotNull(), col("population")).otherwise(0).alias("population"),
            when(col("median_income").isNotNull(), col("median_income")).otherwise(0).alias("median_household_income"),
            when(col("amenities").isNotNull(), col("amenities")).otherwise(array()).alias("amenities"),
            when(col("points_of_interest").isNotNull(), col("points_of_interest")).otherwise(array()).alias("points_of_interest")
        )
        
        # Add optional fields if they exist
        optional_fields = {
            "walkability_score": 0,
            "transit_score": 0,
            "school_rating": 0,
            "safety_rating": 0,
            "median_home_price": 0,
            "price_trend": "",
            "lifestyle_tags": array(),
            "vibe": ""
        }
        
        for field, default_value in optional_fields.items():
            if field in df.columns:
                prepared_df = prepared_df.withColumn(
                    field,
                    when(col(field).isNotNull(), col(field)).otherwise(default_value)
                )
            else:
                prepared_df = prepared_df.withColumn(field, lit(default_value))
        
        return prepared_df
    
    def _write_neighborhood_nodes(self, df: DataFrame) -> None:
        """
        Write Neighborhood nodes to Neo4j.
        
        Args:
            df: DataFrame containing prepared neighborhood nodes
        """
        count = df.count()
        if count == 0:
            self.logger.warning("No Neighborhood nodes to write")
            return
        
        self.logger.info(f"Writing {count} Neighborhood nodes to Neo4j...")
        
        (df.write
         .format(self.format_string)
         .mode("append")
         .option("url", self.config.uri)
         .option("authentication.basic.username", self.config.username)
         .option("authentication.basic.password", self.config.get_password() or "")
         .option("database", self.config.database)
         .option("labels", ":Neighborhood")
         .option("node.keys", "id")
         .option("batch.size", str(self.config.transaction_size))
         .save())
    
    def _extract_cities(self, neighborhoods_df: DataFrame) -> DataFrame:
        """
        Extract unique cities from neighborhoods.
        
        Args:
            neighborhoods_df: DataFrame with neighborhood data
            
        Returns:
            DataFrame with unique city nodes
        """
        cities_df = neighborhoods_df.groupBy("city", "state").agg(
            avg("latitude").alias("latitude"),
            avg("longitude").alias("longitude")
        ).select(
            concat_ws("_", col("city"), col("state")).alias("id"),
            concat_ws("_", col("city"), col("state")).alias("city_id"),
            col("city").alias("name"),
            col("state"),
            col("latitude"),
            col("longitude")
        )
        
        return cities_df
    
    def _extract_states(self, cities_df: DataFrame) -> DataFrame:
        """
        Extract unique states from cities.
        
        Args:
            cities_df: DataFrame with city data
            
        Returns:
            DataFrame with unique state nodes
        """
        states_df = cities_df.select("state").distinct().select(
            col("state").alias("id"),
            col("state").alias("state_id"),
            col("state").alias("abbreviation"),
            when(col("state") == "CA", "California")
            .when(col("state") == "UT", "Utah")
            .when(col("state") == "NY", "New York")
            .when(col("state") == "TX", "Texas")
            .when(col("state") == "FL", "Florida")
            .otherwise(col("state")).alias("name")
        )
        
        return states_df
    
    def _write_city_nodes(self, df: DataFrame) -> None:
        """
        Write City nodes to Neo4j.
        
        Args:
            df: DataFrame containing city nodes
        """
        count = df.count()
        if count == 0:
            return
        
        self.logger.info(f"Writing {count} City nodes to Neo4j...")
        
        (df.write
         .format(self.format_string)
         .mode("append")
         .option("url", self.config.uri)
         .option("authentication.basic.username", self.config.username)
         .option("authentication.basic.password", self.config.get_password() or "")
         .option("database", self.config.database)
         .option("labels", ":City")
         .option("node.keys", "id")
         .option("batch.size", str(self.config.transaction_size))
         .save())
    
    def _write_state_nodes(self, df: DataFrame) -> None:
        """
        Write State nodes to Neo4j.
        
        Args:
            df: DataFrame containing state nodes
        """
        count = df.count()
        if count == 0:
            return
        
        self.logger.info(f"Writing {count} State nodes to Neo4j...")
        
        (df.write
         .format(self.format_string)
         .mode("append")
         .option("url", self.config.uri)
         .option("authentication.basic.username", self.config.username)
         .option("authentication.basic.password", self.config.get_password() or "")
         .option("database", self.config.database)
         .option("labels", ":State")
         .option("node.keys", "id")
         .option("batch.size", str(self.config.transaction_size))
         .save())
    
    def _create_located_in_relationships(self, neighborhoods_df: DataFrame, cities_df: DataFrame) -> None:
        """
        Create LOCATED_IN relationships between Neighborhoods and Cities.
        
        Args:
            neighborhoods_df: DataFrame with neighborhood data
            cities_df: DataFrame with city data
        """
        # Join neighborhoods with cities to create relationships
        relationships_df = neighborhoods_df.join(
            cities_df,
            (neighborhoods_df.city == cities_df.name) & 
            (neighborhoods_df.state == cities_df.state),
            "inner"
        ).select(
            col("neighborhood_id").alias("from_id"),
            col("city_id").alias("to_id")
        ).distinct()
        
        count = relationships_df.count()
        if count == 0:
            return
        
        self.logger.info(f"Creating {count} Neighborhood LOCATED_IN City relationships...")
        
        cypher = """
        MATCH (n:Neighborhood {id: from_id})
        MATCH (c:City {id: to_id})
        MERGE (n)-[:LOCATED_IN]->(c)
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
    
    def _create_part_of_relationships(self, cities_df: DataFrame, states_df: DataFrame) -> None:
        """
        Create PART_OF relationships between Cities and States.
        
        Args:
            cities_df: DataFrame with city data
            states_df: DataFrame with state data
        """
        # Join cities with states to create relationships
        relationships_df = cities_df.join(
            states_df,
            cities_df.state == states_df.abbreviation,
            "inner"
        ).select(
            col("city_id").alias("from_id"),
            col("state_id").alias("to_id")
        ).distinct()
        
        count = relationships_df.count()
        if count == 0:
            return
        
        self.logger.info(f"Creating {count} City PART_OF State relationships...")
        
        cypher = """
        MATCH (c:City {id: from_id})
        MATCH (s:State {id: to_id})
        MERGE (c)-[:PART_OF]->(s)
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
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "neo4j_neighborhoods"