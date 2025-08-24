"""
Wikipedia data loader using pure Python SQLite approach.

This module provides a clean, focused loader specifically for Wikipedia data,
using pandas and sqlite3 for simple, dependency-free SQLite access and
using common property_finder_models for validation.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    array,
    col,
    current_timestamp,
    lit,
    split,
    struct,
    to_json,
    when,
)
from pyspark.sql.types import ArrayType, DoubleType, StringType, StructType

# Import shared models from common package
from common.property_finder_models.entities import EnrichedWikipediaArticle
from common.property_finder_models.geographic import LocationInfo

logger = logging.getLogger(__name__)


class WikipediaLoader:
    """Loads Wikipedia data from SQLite database into Spark DataFrames."""
    
    def __init__(self, spark: SparkSession):
        """
        Initialize the Wikipedia loader.
        
        Args:
            spark: Active SparkSession
        """
        self.spark = spark
    
    def load(self, db_path: str) -> DataFrame:
        """
        Load Wikipedia data from SQLite database.
        
        Args:
            db_path: Path to SQLite database file
            
        Returns:
            DataFrame with Wikipedia data in unified schema
        """
        logger.info(f"Loading Wikipedia data from: {db_path}")
        
        # Verify database exists
        if not Path(db_path).exists():
            raise FileNotFoundError(f"Wikipedia database not found: {db_path}")
        
        # Load data using pandas (pure Python approach)
        pandas_df = self._load_with_pandas(db_path)
        
        if pandas_df.empty:
            logger.warning("No Wikipedia articles found in database")
            return self.spark.createDataFrame([], schema=self._get_empty_schema())
        
        # Convert to Spark DataFrame
        raw_df = self.spark.createDataFrame(pandas_df)
        
        # Transform to unified schema
        unified_df = self._transform_to_unified(raw_df, db_path)
        
        record_count = unified_df.count()
        logger.info(f"Successfully loaded {record_count} Wikipedia articles")
        
        return unified_df
    
    def _load_with_pandas(self, db_path: str) -> pd.DataFrame:
        """
        Load Wikipedia data using pandas and sqlite3.
        
        Args:
            db_path: Path to SQLite database
            
        Returns:
            Pandas DataFrame with Wikipedia data
        """
        query = """
            SELECT 
                a.pageid as page_id,
                a.title,
                a.url,
                a.extract as full_text,
                a.relevance_score,
                a.latitude,
                a.longitude,
                s.short_summary as summary,
                s.key_topics,
                s.best_city,
                s.best_state,
                s.overall_confidence
            FROM articles a 
            LEFT JOIN page_summaries s ON a.pageid = s.page_id
            ORDER BY a.relevance_score DESC
        """
        
        try:
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Handle NULL values appropriately
            df = df.fillna({
                'summary': '',
                'key_topics': '',
                'best_city': '',
                'best_state': '',
                'overall_confidence': 0.0,
                'latitude': 0.0,
                'longitude': 0.0
            })
            
            logger.info(f"Loaded {len(df)} Wikipedia articles from SQLite")
            return df
            
        except Exception as e:
            logger.error(f"Error loading Wikipedia data: {e}")
            raise
    
    def _transform_to_unified(self, df: DataFrame, source_path: str) -> DataFrame:
        """
        Transform raw Wikipedia data to unified schema.
        
        Args:
            df: Raw Wikipedia DataFrame
            source_path: Source database path for tracking
            
        Returns:
            DataFrame conforming to unified schema
        """
        return df.select(
            # Core entity fields
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
            
            # Property fields (not applicable for Wikipedia)
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
            # Parse key_topics as array if present
            when(col("key_topics").isNotNull() & (col("key_topics") != ""),
                 split(col("key_topics"), ","))
                .otherwise(array()).alias("features"),
            array().cast(ArrayType(StringType())).alias("features_normalized"),
            col("full_text").alias("content"),
            col("summary"),
            col("key_topics"),
            
            # Embedding fields (populated later in pipeline)
            lit(None).cast("string").alias("embedding_text"),
            array().cast(ArrayType(DoubleType())).alias("embedding"),
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
            lit(source_path).alias("source_file"),
            lit("SQLITE").alias("source_type"),
            col("url"),
            
            # Processing timestamps
            current_timestamp().alias("ingested_at"),
            lit(None).cast("timestamp").alias("processed_at"),
            lit(None).cast("timestamp").alias("embedding_generated_at"),
        )
    
    def _get_empty_schema(self) -> StructType:
        """
        Get empty schema for when no data is found.
        
        Returns:
            Empty StructType matching unified schema
        """
        from data_pipeline.schemas.unified_schema import UnifiedDataSchema
        return UnifiedDataSchema.get_schema()
    
    def validate(self, df: DataFrame) -> bool:
        """
        Validate loaded Wikipedia data.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if data is valid
        """
        # Check for required fields
        null_ids = df.filter(col("entity_id").isNull()).count()
        if null_ids > 0:
            logger.error(f"Found {null_ids} Wikipedia articles with null page_id")
            return False
        
        # Check content quality
        empty_content = df.filter(
            col("content").isNull() | (col("content") == "")
        ).count()
        if empty_content > 0:
            logger.warning(f"Found {empty_content} Wikipedia articles with empty content")
        
        # Check confidence scores
        low_confidence = df.filter(
            col("confidence_score") < 0.5
        ).count()
        if low_confidence > 0:
            logger.info(f"Found {low_confidence} articles with low confidence scores")
        
        return True