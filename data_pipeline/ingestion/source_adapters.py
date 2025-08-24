"""
Source adapters for different data formats.

This module provides adapters for loading data from various sources
(JSON files, SQLite databases) into standardized Spark DataFrames.
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    array,
    col,
    current_timestamp,
    lit,
    struct,
    to_json,
    when,
)

from data_pipeline.config.models import DataSourceConfig
from data_pipeline.ingestion.data_validation import DataValidator

logger = logging.getLogger(__name__)


class SourceAdapter(ABC):
    """Abstract base class for data source adapters."""
    
    def __init__(self, spark: SparkSession, config: DataSourceConfig):
        """
        Initialize source adapter.
        
        Args:
            spark: SparkSession instance
            config: Data source configuration
        """
        self.spark = spark
        self.config = config
        self.validator = DataValidator()
    
    @abstractmethod
    def load(self) -> DataFrame:
        """
        Load data from the source.
        
        Returns:
            DataFrame with loaded data
        """
        pass
    
    @abstractmethod
    def transform_to_unified(self, df: DataFrame) -> DataFrame:
        """
        Transform source data to unified schema.
        
        Args:
            df: Source DataFrame
            
        Returns:
            DataFrame conforming to unified schema
        """
        pass
    
    def validate_config(self) -> bool:
        """
        Validate source configuration.
        
        Returns:
            True if configuration is valid
        """
        if not self.config.path:
            logger.error("Source path is required")
            return False
        
        if not self.config.format:
            logger.error("Source format is required")
            return False
        
        return True


class PropertySourceAdapter(SourceAdapter):
    """Adapter for loading property data from JSON files."""
    
    def load(self) -> DataFrame:
        """
        Load property data from JSON files.
        
        Returns:
            DataFrame with property data
        """
        if not self.validate_config():
            raise ValueError("Invalid source configuration")
        
        logger.info(f"Loading property data from: {self.config.path}")
        
        try:
            # Load JSON file
            df = self.spark.read.option("multiLine", "true").json(self.config.path)
            
            # Log basic statistics
            count = df.count()
            logger.info(f"Loaded {count} property records")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to load property data: {e}")
            raise
    
    def transform_to_unified(self, df: DataFrame) -> DataFrame:
        """
        Transform property data to unified schema.
        
        Args:
            df: Property DataFrame
            
        Returns:
            DataFrame with unified schema
        """
        logger.info("Transforming property data to unified schema")
        
        return df.select(
            col("listing_id").cast("string").alias("entity_id"),
            lit("PROPERTY").alias("entity_type"),
            lit(None).cast("string").alias("correlation_uuid"),
            
            # Location fields
            col("address.city").alias("city"),
            col("address.state").alias("state"),
            lit(None).cast("string").alias("city_normalized"),
            lit(None).cast("string").alias("state_normalized"),
            lit(None).cast("double").alias("latitude"),
            lit(None).cast("double").alias("longitude"),
            
            # Property-specific fields
            col("property_type"),
            col("price").cast("decimal(12,2)"),
            col("bedrooms").cast("int"),
            col("bathrooms").cast("double"),
            col("square_feet").cast("int"),
            lit(None).cast("decimal(10,4)").alias("price_per_sqft"),
            col("year_built").cast("int"),
            col("lot_size").cast("int"),
            
            # Content and features
            lit(None).cast("string").alias("title"),
            col("description"),
            col("features"),
            lit(None).alias("features_normalized"),
            lit(None).cast("string").alias("content"),
            lit(None).cast("string").alias("summary"),
            lit(None).cast("string").alias("key_topics"),
            
            # Embeddings (to be filled later)
            lit(None).cast("string").alias("embedding_text"),
            lit(None).alias("embedding"),
            lit(None).cast("string").alias("embedding_model"),
            lit(None).cast("int").alias("embedding_dimension"),
            lit(None).cast("long").alias("chunk_index"),
            
            # Quality and metadata
            lit(None).cast("string").alias("content_hash"),
            lit(None).cast("double").alias("data_quality_score"),
            lit("pending").alias("validation_status"),
            lit(None).cast("double").alias("confidence_score"),
            
            # Source tracking
            to_json(struct("*")).alias("raw_data"),
            lit(self.config.path).alias("source_file"),
            lit("JSON").alias("source_type"),
            lit(None).cast("string").alias("url"),
            
            # Timestamps
            current_timestamp().alias("ingested_at"),
            lit(None).cast("timestamp").alias("processed_at"),
            lit(None).cast("timestamp").alias("embedding_generated_at"),
        )


class NeighborhoodSourceAdapter(SourceAdapter):
    """Adapter for loading neighborhood data from JSON files."""
    
    def load(self) -> DataFrame:
        """
        Load neighborhood data from JSON files.
        
        Returns:
            DataFrame with neighborhood data
        """
        if not self.validate_config():
            raise ValueError("Invalid source configuration")
        
        logger.info(f"Loading neighborhood data from: {self.config.path}")
        
        try:
            # Load JSON file
            df = self.spark.read.option("multiLine", "true").json(self.config.path)
            
            # Log basic statistics
            count = df.count()
            logger.info(f"Loaded {count} neighborhood records")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to load neighborhood data: {e}")
            raise
    
    def transform_to_unified(self, df: DataFrame) -> DataFrame:
        """
        Transform neighborhood data to unified schema.
        
        Args:
            df: Neighborhood DataFrame
            
        Returns:
            DataFrame with unified schema
        """
        logger.info("Transforming neighborhood data to unified schema")
        
        return df.select(
            col("neighborhood_id").cast("string").alias("entity_id"),
            lit("NEIGHBORHOOD").alias("entity_type"),
            lit(None).cast("string").alias("correlation_uuid"),
            
            # Location fields
            col("city"),
            col("state"),
            lit(None).cast("string").alias("city_normalized"),
            lit(None).cast("string").alias("state_normalized"),
            lit(None).cast("double").alias("latitude"),
            lit(None).cast("double").alias("longitude"),
            
            # Property fields (not applicable)
            lit(None).cast("string").alias("property_type"),
            lit(None).cast("decimal(12,2)").alias("price"),
            lit(None).cast("int").alias("bedrooms"),
            lit(None).cast("double").alias("bathrooms"),
            lit(None).cast("int").alias("square_feet"),
            lit(None).cast("decimal(10,4)").alias("price_per_sqft"),
            lit(None).cast("int").alias("year_built"),
            lit(None).cast("int").alias("lot_size"),
            
            # Content and features
            col("name").alias("title"),
            col("description"),
            col("amenities").alias("features"),
            lit(None).alias("features_normalized"),
            lit(None).cast("string").alias("content"),
            lit(None).cast("string").alias("summary"),
            lit(None).cast("string").alias("key_topics"),
            
            # Embeddings (to be filled later)
            lit(None).cast("string").alias("embedding_text"),
            lit(None).alias("embedding"),
            lit(None).cast("string").alias("embedding_model"),
            lit(None).cast("int").alias("embedding_dimension"),
            lit(None).cast("long").alias("chunk_index"),
            
            # Quality and metadata
            lit(None).cast("string").alias("content_hash"),
            lit(None).cast("double").alias("data_quality_score"),
            lit("pending").alias("validation_status"),
            lit(None).cast("double").alias("confidence_score"),
            
            # Source tracking
            to_json(struct("*")).alias("raw_data"),
            lit(self.config.path).alias("source_file"),
            lit("JSON").alias("source_type"),
            lit(None).cast("string").alias("url"),
            
            # Timestamps
            current_timestamp().alias("ingested_at"),
            lit(None).cast("timestamp").alias("processed_at"),
            lit(None).cast("timestamp").alias("embedding_generated_at"),
        )


class WikipediaSourceAdapter(SourceAdapter):
    """Adapter for loading Wikipedia data from SQLite database."""
    
    def load(self) -> DataFrame:
        """
        Load Wikipedia data from SQLite database.
        
        Returns:
            DataFrame with Wikipedia data
        """
        if not self.validate_config():
            raise ValueError("Invalid source configuration")
        
        logger.info(f"Loading Wikipedia data from: {self.config.path}")
        
        try:
            # Build JDBC URL
            jdbc_url = self.config.options.get("url", f"jdbc:sqlite:{self.config.path}")
            
            # SQL query to load data
            query = """
                (SELECT 
                    a.page_id,
                    a.title,
                    a.url,
                    a.full_text,
                    a.relevance_score,
                    a.latitude,
                    a.longitude,
                    s.summary,
                    s.key_topics,
                    s.best_city,
                    s.best_state,
                    s.overall_confidence
                FROM articles a 
                LEFT JOIN page_summaries s ON a.page_id = s.page_id) t
            """
            
            # Load from SQLite
            df = self.spark.read \
                .format("jdbc") \
                .option("url", jdbc_url) \
                .option("dbtable", query) \
                .option("driver", "org.sqlite.JDBC") \
                .load()
            
            # Log basic statistics
            count = df.count()
            logger.info(f"Loaded {count} Wikipedia articles")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to load Wikipedia data: {e}")
            raise
    
    def transform_to_unified(self, df: DataFrame) -> DataFrame:
        """
        Transform Wikipedia data to unified schema.
        
        Args:
            df: Wikipedia DataFrame
            
        Returns:
            DataFrame with unified schema
        """
        logger.info("Transforming Wikipedia data to unified schema")
        
        return df.select(
            col("page_id").cast("string").alias("entity_id"),
            lit("WIKIPEDIA_ARTICLE").alias("entity_type"),
            lit(None).cast("string").alias("correlation_uuid"),
            
            # Location fields
            col("best_city").alias("city"),
            col("best_state").alias("state"),
            lit(None).cast("string").alias("city_normalized"),
            lit(None).cast("string").alias("state_normalized"),
            col("latitude").cast("double"),
            col("longitude").cast("double"),
            
            # Property fields (not applicable)
            lit(None).cast("string").alias("property_type"),
            lit(None).cast("decimal(12,2)").alias("price"),
            lit(None).cast("int").alias("bedrooms"),
            lit(None).cast("double").alias("bathrooms"),
            lit(None).cast("int").alias("square_feet"),
            lit(None).cast("decimal(10,4)").alias("price_per_sqft"),
            lit(None).cast("int").alias("year_built"),
            lit(None).cast("int").alias("lot_size"),
            
            # Content and features
            col("title"),
            lit(None).cast("string").alias("description"),
            when(col("key_topics").isNotNull(), 
                 array(*[lit(t.strip()) for t in col("key_topics").split(",")]))
                .otherwise(array()).alias("features"),
            lit(None).alias("features_normalized"),
            col("full_text").alias("content"),
            col("summary"),
            col("key_topics"),
            
            # Embeddings (to be filled later)
            lit(None).cast("string").alias("embedding_text"),
            lit(None).alias("embedding"),
            lit(None).cast("string").alias("embedding_model"),
            lit(None).cast("int").alias("embedding_dimension"),
            lit(None).cast("long").alias("chunk_index"),
            
            # Quality and metadata
            lit(None).cast("string").alias("content_hash"),
            lit(None).cast("double").alias("data_quality_score"),
            lit("pending").alias("validation_status"),
            col("overall_confidence").cast("double").alias("confidence_score"),
            
            # Source tracking
            to_json(struct(
                "page_id", "title", "url", "relevance_score", 
                "summary", "key_topics", "best_city", "best_state", 
                "overall_confidence"
            )).alias("raw_data"),
            lit(self.config.path).alias("source_file"),
            lit("SQLITE").alias("source_type"),
            col("url"),
            
            # Timestamps
            current_timestamp().alias("ingested_at"),
            lit(None).cast("timestamp").alias("processed_at"),
            lit(None).cast("timestamp").alias("embedding_generated_at"),
        )


class SourceAdapterFactory:
    """Factory for creating source adapters."""
    
    @staticmethod
    def create_adapter(
        spark: SparkSession,
        config: DataSourceConfig,
        source_name: str
    ) -> SourceAdapter:
        """
        Create appropriate source adapter based on configuration.
        
        Args:
            spark: SparkSession instance
            config: Data source configuration
            source_name: Name of the data source
            
        Returns:
            Appropriate SourceAdapter instance
            
        Raises:
            ValueError: If source type is unknown
        """
        # Determine adapter type based on source name and format
        if "properties" in source_name.lower():
            return PropertySourceAdapter(spark, config)
        elif "neighborhoods" in source_name.lower():
            return NeighborhoodSourceAdapter(spark, config)
        elif "wikipedia" in source_name.lower() or config.format == "jdbc":
            return WikipediaSourceAdapter(spark, config)
        else:
            raise ValueError(f"Unknown source type for: {source_name}")