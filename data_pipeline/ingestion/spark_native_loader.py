"""
Simplified data loading using Spark's native capabilities.

This module leverages Spark's built-in DataFrameReader for JSON files
and provides clean SQLite integration options.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
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
from pyspark.sql.types import (
    ArrayType,
    DecimalType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

from data_pipeline.config.models import DataSourceConfig, PipelineConfig
from data_pipeline.schemas.unified_schema import UnifiedDataSchema

logger = logging.getLogger(__name__)


class SparkNativeLoader:
    """
    Data loader using Spark's native capabilities.
    
    This loader uses Spark's built-in DataFrameReader for JSON files
    and provides flexible SQLite loading options.
    """
    
    def __init__(self, spark: SparkSession, config: PipelineConfig):
        """
        Initialize the native loader.
        
        Args:
            spark: SparkSession instance
            config: Pipeline configuration
        """
        self.spark = spark
        self.config = config
        self.schema = UnifiedDataSchema()
    
    def load_json_properties(self, path: str) -> DataFrame:
        """
        Load property data using Spark's native JSON reader.
        
        Args:
            path: Path to JSON file(s), can use wildcards
            
        Returns:
            DataFrame with property data in unified schema
        """
        logger.info(f"Loading properties from JSON: {path}")
        
        # Define expected schema for better performance and consistency
        property_schema = StructType([
            StructField("listing_id", StringType(), False),
            StructField("property_type", StringType(), True),
            StructField("price", DecimalType(12, 2), True),
            StructField("bedrooms", IntegerType(), True),
            StructField("bathrooms", DoubleType(), True),
            StructField("square_feet", IntegerType(), True),
            StructField("year_built", IntegerType(), True),
            StructField("lot_size", IntegerType(), True),
            StructField("features", ArrayType(StringType()), True),
            StructField("description", StringType(), True),
            StructField("address", StructType([
                StructField("street", StringType(), True),
                StructField("city", StringType(), True),
                StructField("state", StringType(), True),
                StructField("zip_code", StringType(), True),
            ]), True),
        ])
        
        # Use Spark's native JSON reader with options
        df = self.spark.read \
            .schema(property_schema) \
            .option("multiLine", True) \
            .option("mode", "PERMISSIVE") \
            .option("columnNameOfCorruptRecord", "_corrupt_record") \
            .json(path)
        
        # Transform to unified schema using select (more efficient than withColumn)
        return df.select(
            col("listing_id").alias("entity_id"),
            lit("PROPERTY").alias("entity_type"),
            lit(None).cast("string").alias("correlation_uuid"),
            
            # Location fields
            col("address.city").alias("city"),
            col("address.state").alias("state"),
            lit(None).cast("string").alias("city_normalized"),
            lit(None).cast("string").alias("state_normalized"),
            lit(None).cast("double").alias("latitude"),
            lit(None).cast("double").alias("longitude"),
            
            # Property fields
            col("property_type"),
            col("price"),
            col("bedrooms"),
            col("bathrooms"),
            col("square_feet"),
            lit(None).cast("decimal(10,4)").alias("price_per_sqft"),
            col("year_built"),
            col("lot_size"),
            
            # Content fields
            lit(None).cast("string").alias("title"),
            col("description"),
            col("features"),
            lit(None).alias("features_normalized"),
            lit(None).cast("string").alias("content"),
            lit(None).cast("string").alias("summary"),
            lit(None).cast("string").alias("key_topics"),
            
            # Embedding fields (to be populated later)
            lit(None).cast("string").alias("embedding_text"),
            lit(None).alias("embedding"),
            lit(None).cast("string").alias("embedding_model"),
            lit(None).cast("int").alias("embedding_dimension"),
            lit(None).cast("long").alias("chunk_index"),
            
            # Metadata fields
            lit(None).cast("string").alias("content_hash"),
            lit(None).cast("double").alias("data_quality_score"),
            lit("pending").alias("validation_status"),
            lit(None).cast("double").alias("confidence_score"),
            
            # Source tracking
            to_json(struct("*")).alias("raw_data"),
            lit(path).alias("source_file"),
            lit("JSON").alias("source_type"),
            lit(None).cast("string").alias("url"),
            
            # Timestamps
            current_timestamp().alias("ingested_at"),
            lit(None).cast("timestamp").alias("processed_at"),
            lit(None).cast("timestamp").alias("embedding_generated_at"),
        )
    
    def load_json_neighborhoods(self, path: str) -> DataFrame:
        """
        Load neighborhood data using Spark's native JSON reader.
        
        Args:
            path: Path to JSON file(s), can use wildcards
            
        Returns:
            DataFrame with neighborhood data in unified schema
        """
        logger.info(f"Loading neighborhoods from JSON: {path}")
        
        # Define expected schema
        neighborhood_schema = StructType([
            StructField("neighborhood_id", StringType(), False),
            StructField("name", StringType(), True),
            StructField("city", StringType(), True),
            StructField("state", StringType(), True),
            StructField("description", StringType(), True),
            StructField("amenities", ArrayType(StringType()), True),
            StructField("demographics", StructType([
                StructField("population", IntegerType(), True),
                StructField("median_income", DecimalType(10, 2), True),
                StructField("median_age", DoubleType(), True),
            ]), True),
        ])
        
        # Use Spark's native JSON reader
        df = self.spark.read \
            .schema(neighborhood_schema) \
            .option("multiLine", True) \
            .option("mode", "PERMISSIVE") \
            .json(path)
        
        # Transform to unified schema
        return df.select(
            col("neighborhood_id").alias("entity_id"),
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
            
            # Content fields
            col("name").alias("title"),
            col("description"),
            col("amenities").alias("features"),
            lit(None).alias("features_normalized"),
            lit(None).cast("string").alias("content"),
            lit(None).cast("string").alias("summary"),
            lit(None).cast("string").alias("key_topics"),
            
            # Embedding fields
            lit(None).cast("string").alias("embedding_text"),
            lit(None).alias("embedding"),
            lit(None).cast("string").alias("embedding_model"),
            lit(None).cast("int").alias("embedding_dimension"),
            lit(None).cast("long").alias("chunk_index"),
            
            # Metadata fields
            lit(None).cast("string").alias("content_hash"),
            lit(None).cast("double").alias("data_quality_score"),
            lit("pending").alias("validation_status"),
            lit(None).cast("double").alias("confidence_score"),
            
            # Source tracking
            to_json(struct("*")).alias("raw_data"),
            lit(path).alias("source_file"),
            lit("JSON").alias("source_type"),
            lit(None).cast("string").alias("url"),
            
            # Timestamps
            current_timestamp().alias("ingested_at"),
            lit(None).cast("timestamp").alias("processed_at"),
            lit(None).cast("timestamp").alias("embedding_generated_at"),
        )
    
    def load_sqlite_wikipedia(
        self, 
        db_path: str, 
        use_jdbc: bool = False
    ) -> DataFrame:
        """
        Load Wikipedia data from SQLite database.
        
        Args:
            db_path: Path to SQLite database file
            use_jdbc: If True, use JDBC (requires driver); if False, use pandas
            
        Returns:
            DataFrame with Wikipedia data in unified schema
        """
        logger.info(f"Loading Wikipedia from SQLite: {db_path}")
        
        if use_jdbc:
            return self._load_sqlite_with_jdbc(db_path)
        else:
            return self._load_sqlite_with_pandas(db_path)
    
    def _load_sqlite_with_pandas(self, db_path: str) -> DataFrame:
        """
        Load SQLite data using pandas (pure Python approach).
        
        Args:
            db_path: Path to SQLite database
            
        Returns:
            Spark DataFrame with Wikipedia data
        """
        logger.info("Using pandas to load SQLite (pure Python approach)")
        
        # SQL query to get data
        query = """
            SELECT 
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
            LEFT JOIN page_summaries s ON a.page_id = s.page_id
        """
        
        # Read with pandas
        conn = sqlite3.connect(db_path)
        pdf = pd.read_sql_query(query, conn)
        conn.close()
        
        # Convert to Spark DataFrame
        df = self.spark.createDataFrame(pdf)
        
        # Transform to unified schema
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
            
            # Content fields
            col("title"),
            lit(None).cast("string").alias("description"),
            when(col("key_topics").isNotNull(), 
                 array(*[lit(t.strip()) for t in col("key_topics").str.split(",")]))
                .otherwise(array()).alias("features"),
            lit(None).alias("features_normalized"),
            col("full_text").alias("content"),
            col("summary"),
            col("key_topics"),
            
            # Embedding fields
            lit(None).cast("string").alias("embedding_text"),
            lit(None).alias("embedding"),
            lit(None).cast("string").alias("embedding_model"),
            lit(None).cast("int").alias("embedding_dimension"),
            lit(None).cast("long").alias("chunk_index"),
            
            # Metadata fields
            lit(None).cast("string").alias("content_hash"),
            lit(None).cast("double").alias("data_quality_score"),
            lit("pending").alias("validation_status"),
            col("overall_confidence").cast("double").alias("confidence_score"),
            
            # Source tracking
            to_json(struct(
                "page_id", "title", "url", "relevance_score",
                "summary", "key_topics", "best_city", "best_state"
            )).alias("raw_data"),
            lit(db_path).alias("source_file"),
            lit("SQLITE").alias("source_type"),
            col("url"),
            
            # Timestamps
            current_timestamp().alias("ingested_at"),
            lit(None).cast("timestamp").alias("processed_at"),
            lit(None).cast("timestamp").alias("embedding_generated_at"),
        )
    
    def _load_sqlite_with_jdbc(self, db_path: str) -> DataFrame:
        """
        Load SQLite data using JDBC (requires Java driver).
        
        Args:
            db_path: Path to SQLite database
            
        Returns:
            Spark DataFrame with Wikipedia data
        """
        logger.info("Using JDBC to load SQLite (requires Java driver)")
        
        # Check if SQLite JDBC driver is available
        jdbc_jar = Path("data_pipeline/lib/sqlite-jdbc-3.43.0.0.jar")
        if not jdbc_jar.exists():
            logger.warning(
                f"SQLite JDBC driver not found at {jdbc_jar}. "
                "Please download from https://repo1.maven.org/maven2/org/xerial/sqlite-jdbc/"
            )
            raise FileNotFoundError(f"SQLite JDBC driver not found: {jdbc_jar}")
        
        # SQL query wrapped for JDBC
        query = """
            (SELECT 
                CAST(a.page_id AS TEXT) as page_id,
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
        
        # Load with JDBC
        df = self.spark.read \
            .format("jdbc") \
            .option("url", f"jdbc:sqlite:{db_path}") \
            .option("driver", "org.sqlite.JDBC") \
            .option("dbtable", query) \
            .load()
        
        # Transform to unified schema (same as pandas approach)
        return self._transform_wikipedia_to_unified(df, db_path)
    
    def _transform_wikipedia_to_unified(
        self, 
        df: DataFrame, 
        source_path: str
    ) -> DataFrame:
        """
        Transform Wikipedia DataFrame to unified schema.
        
        Args:
            df: Raw Wikipedia DataFrame
            source_path: Source file path for tracking
            
        Returns:
            DataFrame in unified schema
        """
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
            
            # Content fields
            col("title"),
            lit(None).cast("string").alias("description"),
            lit(array()).alias("features"),  # Will parse key_topics if needed
            lit(None).alias("features_normalized"),
            col("full_text").alias("content"),
            col("summary"),
            col("key_topics"),
            
            # Embedding fields
            lit(None).cast("string").alias("embedding_text"),
            lit(None).alias("embedding"),
            lit(None).cast("string").alias("embedding_model"),
            lit(None).cast("int").alias("embedding_dimension"),
            lit(None).cast("long").alias("chunk_index"),
            
            # Metadata fields
            lit(None).cast("string").alias("content_hash"),
            lit(None).cast("double").alias("data_quality_score"),
            lit("pending").alias("validation_status"),
            col("overall_confidence").cast("double").alias("confidence_score"),
            
            # Source tracking
            to_json(struct(
                "page_id", "title", "url", "relevance_score",
                "summary", "key_topics", "best_city", "best_state"
            )).alias("raw_data"),
            lit(source_path).alias("source_file"),
            lit("SQLITE").alias("source_type"),
            col("url"),
            
            # Timestamps
            current_timestamp().alias("ingested_at"),
            lit(None).cast("timestamp").alias("processed_at"),
            lit(None).cast("timestamp").alias("embedding_generated_at"),
        )