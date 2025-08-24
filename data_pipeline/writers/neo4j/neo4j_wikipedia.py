"""
Neo4j writer for Wikipedia Article entities.

This module provides a Neo4j writer specifically for Wikipedia Article entities,
creating WikipediaArticle nodes and their relationships in the graph database.
"""

import logging
from typing import Any, Dict, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, when, lit, array, split, explode, concat_ws

from data_pipeline.config.models import Neo4jConfig
from data_pipeline.writers.base import DataWriter
from data_pipeline.graph_models import WikipediaArticleNode, GraphConfiguration
from data_pipeline.schemas.entity_schemas import WikipediaArticleSchema

logger = logging.getLogger(__name__)


class WikipediaNeo4jWriter(DataWriter):
    """
    Neo4j writer specifically for Wikipedia Article entities.
    
    Creates WikipediaArticle nodes with content and metadata,
    establishes DESCRIBES relationships to Cities, Neighborhoods,
    and other entities mentioned in the articles.
    """
    
    def __init__(self, config: Neo4jConfig, spark: SparkSession):
        """
        Initialize the Wikipedia Neo4j writer.
        
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
        
        # Graph configuration for confidence thresholds
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
            self.logger.info(f"Successfully validated Neo4j connection for WikipediaWriter")
            return True
            
        except Exception as e:
            self.logger.error(f"Wikipedia Neo4j connection validation failed: {e}")
            return False
    
    def write(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write WikipediaArticle nodes and relationships to Neo4j.
        
        Args:
            df: DataFrame containing Wikipedia article data (must match WikipediaArticleSchema)
            metadata: Metadata about the data being written
            
        Returns:
            True if write was successful, False otherwise
        """
        try:
            # Validate DataFrame has required columns
            if not self._validate_dataframe(df):
                return False
            
            # Transform DataFrame for Neo4j
            wikipedia_df = self._prepare_wikipedia_nodes(df)
            
            # Write WikipediaArticle nodes
            self._write_wikipedia_nodes(wikipedia_df)
            
            # Create DESCRIBES relationships to cities
            self._create_describes_city_relationships(wikipedia_df)
            
            # Create DESCRIBES relationships to neighborhoods (based on title matching)
            self._create_describes_neighborhood_relationships(wikipedia_df)
            
            # Extract and create Amenity nodes from articles
            if "key_topics" in df.columns:
                amenities_df = self._extract_amenities(wikipedia_df)
                if amenities_df.count() > 0:
                    self._write_amenity_nodes(amenities_df)
                    self._create_describes_amenity_relationships(wikipedia_df, amenities_df)
            
            self.logger.info(f"Successfully wrote {wikipedia_df.count()} WikipediaArticle nodes to Neo4j")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write Wikipedia articles to Neo4j: {e}")
            return False
    
    def _validate_dataframe(self, df: DataFrame) -> bool:
        """
        Validate that DataFrame contains required Wikipedia columns.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_columns = {"page_id", "title", "short_summary", "long_summary"}
        df_columns = set(df.columns)
        
        missing = required_columns - df_columns
        if missing:
            self.logger.error(f"Missing required columns for WikipediaArticle nodes: {missing}")
            return False
        
        return True
    
    def _prepare_wikipedia_nodes(self, df: DataFrame) -> DataFrame:
        """
        Prepare DataFrame for WikipediaArticle node creation.
        
        Args:
            df: Raw Wikipedia DataFrame
            
        Returns:
            Transformed DataFrame ready for Neo4j
        """
        # Create node ID using page_id
        prepared_df = df.select(
            col("page_id").cast("string").alias("id"),
            col("page_id").cast("string").alias("article_id"),
            col("page_id"),
            col("title"),
            when(col("url").isNotNull(), col("url")).otherwise("").alias("url"),
            col("short_summary"),
            col("long_summary"),
            when(col("key_topics").isNotNull(), col("key_topics")).otherwise("").alias("key_topics"),
            when(col("best_city").isNotNull(), col("best_city")).otherwise("").alias("best_city"),
            when(col("best_state").isNotNull(), col("best_state")).otherwise("").alias("best_state"),
            when(col("confidence_score").isNotNull(), col("confidence_score")).otherwise(0.5).alias("confidence"),
            when(col("relevance_score").isNotNull(), col("relevance_score")).otherwise(0.5).alias("relevance_score"),
            when(col("latitude").isNotNull(), col("latitude")).otherwise(0.0).alias("latitude"),
            when(col("longitude").isNotNull(), col("longitude")).otherwise(0.0).alias("longitude")
        )
        
        # Convert key_topics string to array if needed
        if "key_topics" in df.columns:
            prepared_df = prepared_df.withColumn(
                "key_topics_array",
                when(col("key_topics").isNotNull() & (col("key_topics") != ""),
                     split(col("key_topics"), ","))
                .otherwise(array())
            )
        else:
            prepared_df = prepared_df.withColumn("key_topics_array", array())
        
        return prepared_df
    
    def _write_wikipedia_nodes(self, df: DataFrame) -> None:
        """
        Write WikipediaArticle nodes to Neo4j.
        
        Args:
            df: DataFrame containing prepared Wikipedia nodes
        """
        count = df.count()
        if count == 0:
            self.logger.warning("No WikipediaArticle nodes to write")
            return
        
        self.logger.info(f"Writing {count} WikipediaArticle nodes to Neo4j...")
        
        (df.write
         .format(self.format_string)
         .mode("append")
         .option("url", self.config.uri)
         .option("authentication.basic.username", self.config.username)
         .option("authentication.basic.password", self.config.get_password() or "")
         .option("database", self.config.database)
         .option("labels", ":WikipediaArticle")
         .option("node.keys", "id")
         .option("batch.size", str(self.config.transaction_size))
         .save())
    
    def _create_describes_city_relationships(self, wikipedia_df: DataFrame) -> None:
        """
        Create DESCRIBES relationships between Wikipedia articles and Cities.
        
        Args:
            wikipedia_df: DataFrame with Wikipedia article data
        """
        # Filter articles with city references above confidence threshold
        city_relationships = wikipedia_df.filter(
            (col("best_city").isNotNull()) & 
            (col("best_city") != "") &
            (col("best_state").isNotNull()) &
            (col("confidence") >= self.graph_config.min_location_confidence)
        ).select(
            col("article_id").alias("from_id"),
            concat_ws("_", col("best_city"), col("best_state")).alias("to_id"),
            col("confidence")
        ).distinct()
        
        count = city_relationships.count()
        if count == 0:
            self.logger.info("No Wikipedia-City relationships to create")
            return
        
        self.logger.info(f"Creating {count} WikipediaArticle DESCRIBES City relationships...")
        
        cypher = """
        MATCH (w:WikipediaArticle {id: from_id})
        MATCH (c:City {id: to_id})
        MERGE (w)-[:DESCRIBES {confidence: confidence, match_type: 'location'}]->(c)
        """
        
        (city_relationships.write
         .format(self.format_string)
         .mode("append")
         .option("url", self.config.uri)
         .option("authentication.basic.username", self.config.username)
         .option("authentication.basic.password", self.config.get_password() or "")
         .option("database", self.config.database)
         .option("query", cypher)
         .option("batch.size", str(self.config.transaction_size))
         .save())
    
    def _create_describes_neighborhood_relationships(self, wikipedia_df: DataFrame) -> None:
        """
        Create DESCRIBES relationships between Wikipedia articles and Neighborhoods.
        
        This uses title matching to find neighborhood references.
        
        Args:
            wikipedia_df: DataFrame with Wikipedia article data
        """
        # This would require joining with neighborhood data
        # For now, we'll create relationships based on title matching
        # In a real implementation, this would be more sophisticated
        
        self.logger.info("Skipping neighborhood relationships (requires neighborhood data)")
        # Implementation would join with neighborhood nodes and match on title/content
    
    def _extract_amenities(self, wikipedia_df: DataFrame) -> DataFrame:
        """
        Extract amenity entities from Wikipedia articles.
        
        Args:
            wikipedia_df: DataFrame with Wikipedia article data
            
        Returns:
            DataFrame with extracted amenity nodes
        """
        # Extract amenities from key_topics
        amenities_df = wikipedia_df.filter(
            col("key_topics_array").isNotNull() & (col("key_topics_array") != array())
        ).select(
            col("article_id").alias("source_article_id"),
            col("best_city"),
            col("best_state"),
            explode(col("key_topics_array")).alias("amenity_name")
        ).filter(
            col("amenity_name").isNotNull() & (col("amenity_name") != "")
        ).select(
            concat_ws("_", col("amenity_name"), col("best_city"), col("best_state")).alias("id"),
            concat_ws("_", col("amenity_name"), col("best_city"), col("best_state")).alias("amenity_id"),
            col("amenity_name").alias("name"),
            lit("landmark").alias("amenity_type"),  # Default type
            col("best_city").alias("city"),
            col("best_state").alias("state"),
            col("source_article_id"),
            lit(0.7).alias("extraction_confidence")
        ).distinct()
        
        return amenities_df
    
    def _write_amenity_nodes(self, df: DataFrame) -> None:
        """
        Write Amenity nodes to Neo4j.
        
        Args:
            df: DataFrame containing amenity nodes
        """
        count = df.count()
        if count == 0:
            return
        
        self.logger.info(f"Writing {count} Amenity nodes extracted from Wikipedia...")
        
        (df.write
         .format(self.format_string)
         .mode("append")
         .option("url", self.config.uri)
         .option("authentication.basic.username", self.config.username)
         .option("authentication.basic.password", self.config.get_password() or "")
         .option("database", self.config.database)
         .option("labels", ":Amenity")
         .option("node.keys", "id")
         .option("batch.size", str(self.config.transaction_size))
         .save())
    
    def _create_describes_amenity_relationships(self, wikipedia_df: DataFrame, amenities_df: DataFrame) -> None:
        """
        Create DESCRIBES relationships between Wikipedia articles and Amenities.
        
        Args:
            wikipedia_df: DataFrame with Wikipedia article data
            amenities_df: DataFrame with amenity data
        """
        # Join to create relationships
        relationships_df = amenities_df.select(
            col("source_article_id").alias("from_id"),
            col("amenity_id").alias("to_id"),
            col("extraction_confidence").alias("confidence")
        ).distinct()
        
        count = relationships_df.count()
        if count == 0:
            return
        
        self.logger.info(f"Creating {count} WikipediaArticle DESCRIBES Amenity relationships...")
        
        cypher = """
        MATCH (w:WikipediaArticle {id: from_id})
        MATCH (a:Amenity {id: to_id})
        MERGE (w)-[:DESCRIBES {confidence: confidence, match_type: 'extraction'}]->(a)
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
        return "neo4j_wikipedia"