"""
Wikipedia data loader with proper typing and entity-specific schema.

This loader creates properly typed Wikipedia DataFrames without
using clean Wikipedia-specific schemas.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, current_timestamp, lit

from data_pipeline.models.spark_models import WikipediaArticle
from .base_loader import BaseLoader

logger = logging.getLogger(__name__)


class WikipediaLoader(BaseLoader):
    """Loads Wikipedia data into strongly-typed DataFrames."""
    
    def _define_schema(self):
        """
        Define the expected schema for Wikipedia data.
        
        Returns:
            Spark schema generated from WikipediaArticle SparkModel
        """
        return WikipediaArticle.spark_schema()
    
    def load(self, db_path: str, sample_size: Optional[int] = None) -> DataFrame:
        """
        Load Wikipedia data from SQLite database with optional sampling.
        
        Args:
            db_path: Path to SQLite database file
            sample_size: Optional number of records to sample
            
        Returns:
            DataFrame with Wikipedia articles following a clean schema, optionally sampled
        """
        logger.info(f"Loading Wikipedia data from: {db_path}")
        
        # Verify database exists
        if not Path(db_path).exists():
            raise FileNotFoundError(f"Wikipedia database not found: {db_path}")
        
        # Load data using pandas for simplicity
        pandas_df = self._load_from_database(db_path)
        
        if pandas_df.empty:
            logger.warning("No Wikipedia articles found in database")
            # Return empty DataFrame with proper schema
            return self.spark.createDataFrame([], schema=self.schema)
        
        # Convert to Spark DataFrame
        spark_df = self.spark.createDataFrame(pandas_df)
        
        # Transform to entity-specific schema
        result_df = self._transform_to_entity_schema(spark_df, db_path)
        
        # Apply sampling if requested
        if sample_size is not None and sample_size > 0:
            result_df = result_df.limit(sample_size)
            logger.info(f"Applied sampling: limited to {sample_size} Wikipedia articles")
        
        return result_df
    
    def _transform_to_entity_schema(self, df: DataFrame, source_path: str) -> DataFrame:
        """
        Transform raw Wikipedia data to entity-specific schema.
        
        Args:
            df: Raw Wikipedia DataFrame from SQLite
            source_path: Source database path for tracking
            
        Returns:
            DataFrame conforming to Wikipedia entity schema
        """
        return df.select(
            col("page_id").cast("long"),
            col("title"),
            col("url"),
            col("categories"),  # Already parsed as array
            col("best_city"),
            col("best_state"),
            col("latitude").cast("double"),
            col("longitude").cast("double"),
            col("short_summary"),
            col("long_summary"),
            col("key_topics"),  # Already parsed as array
            col("relevance_score").cast("double"),
            # Embedding fields will be populated by embedding generator
            lit(None).cast("string").alias("embedding_text"),
            lit(None).cast("array<double>").alias("embedding"),
            lit(None).cast("string").alias("embedding_model"),
            lit(None).cast("int").alias("embedding_dimension"),
            # Timestamps
            current_timestamp().alias("ingested_at"),
            lit(None).cast("timestamp").alias("embedded_at"),
            # Source tracking
            lit(source_path).alias("source_file")
        )
    
    def _load_from_database(self, db_path: str) -> pd.DataFrame:
        """
        Load Wikipedia data from SQLite database.
        
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
                a.relevance_score,
                a.latitude,
                a.longitude,
                a.categories,
                s.short_summary,
                s.long_summary,
                s.key_topics,
                s.best_city,
                s.best_state
            FROM articles a 
            INNER JOIN page_summaries s ON a.pageid = s.page_id
            WHERE s.long_summary IS NOT NULL 
              AND s.long_summary != ''
            ORDER BY a.relevance_score DESC
        """
        
        try:
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Handle NULL values with appropriate defaults
            df = df.fillna({
                'short_summary': '',
                'categories': '[]',
                'key_topics': '',
                'best_city': '',
                'best_state': '',
                'relevance_score': 0.0,
                'latitude': 0.0,
                'longitude': 0.0
            })
            
            # Parse key_topics from comma-separated string to list
            def parse_key_topics(topics_str):
                if pd.isna(topics_str) or topics_str == '':
                    return []
                return [topic.strip() for topic in topics_str.split(',') if topic.strip()]
            
            # Parse categories from JSON string to list
            def parse_categories(categories_str):
                if pd.isna(categories_str) or categories_str == '' or categories_str == '[]':
                    return []
                try:
                    return json.loads(categories_str)
                except (json.JSONDecodeError, TypeError):
                    return []
            
            df['key_topics'] = df['key_topics'].apply(parse_key_topics)
            df['categories'] = df['categories'].apply(parse_categories)
            
            # Filter out any rows with empty long_summary (shouldn't happen with WHERE clause)
            df = df[df['long_summary'].str.len() > 0]
            
            logger.info(f"Loaded {len(df)} Wikipedia articles from SQLite")
            return df
            
        except Exception as e:
            logger.error(f"Error loading Wikipedia data: {e}")
            raise
    
    
    def validate(self, df: DataFrame) -> bool:
        """
        Validate loaded Wikipedia data.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if data is valid
        """
        # Check for required fields
        null_ids = df.filter(col("page_id").isNull()).count()
        if null_ids > 0:
            logger.error(f"Found {null_ids} Wikipedia articles with null page_id")
            return False
        
        # Check content quality
        empty_content = df.filter(
            col("long_summary").isNull() | (col("long_summary") == "")
        ).count()
        if empty_content > 0:
            logger.warning(f"Found {empty_content} Wikipedia articles with empty content")
        
        return True