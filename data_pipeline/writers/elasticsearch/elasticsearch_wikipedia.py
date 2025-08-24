"""
Wikipedia-specific Elasticsearch writer.

This module provides a writer for outputting Wikipedia article DataFrames to Elasticsearch
with article-specific mappings and optimizations for content search.
"""

import logging
from typing import Any, Dict, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, concat_ws, struct, when, length, lit

from data_pipeline.config.models import ElasticsearchConfig
from data_pipeline.writers.base import DataWriter

logger = logging.getLogger(__name__)


class WikipediaElasticsearchWriter(DataWriter):
    """
    Wikipedia-specific Elasticsearch writer.
    
    Writes Wikipedia article DataFrames to Elasticsearch with optimized mappings
    for content search and semantic retrieval.
    """
    
    INDEX_NAME = "wikipedia_articles"
    
    def __init__(self, config: ElasticsearchConfig, spark: SparkSession):
        """
        Initialize the Wikipedia Elasticsearch writer.
        
        Args:
            config: Elasticsearch writer configuration
            spark: SparkSession instance
        """
        super().__init__(config)
        self.config = config
        self.spark = spark
        self.logger = logging.getLogger(__name__)
        self.index_name = f"{config.index_prefix}_{self.INDEX_NAME}"
        
        # Build connection options
        self._build_connection_options()
    
    def _build_connection_options(self) -> None:
        """Build connection options for Elasticsearch."""
        self.base_options = {
            "es.nodes": ",".join(self.config.hosts),
            "es.batch.size.entries": str(self.config.bulk_size),
            "es.write.operation": "index",
            "es.index.auto.create": "true",
            "es.mapping.id": "page_id"  # Use page_id as document ID
        }
        
        # Add authentication if provided
        if self.config.username:
            self.base_options["es.net.http.auth.user"] = self.config.username
        
        password = self.config.get_password()
        if password:
            self.base_options["es.net.http.auth.pass"] = password
    
    def validate_connection(self) -> bool:
        """
        Validate the connection to Elasticsearch.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Create minimal test DataFrame
            test_df = self.spark.createDataFrame(
                [(12345, "Test Article", "Test content about a location", 0.95)], 
                ["page_id", "title", "long_summary", "relevance_score"]
            )
            
            # Attempt write to temporary test index
            test_options = self.base_options.copy()
            test_options["es.resource"] = "_test_wikipedia_connection/doc"
            
            test_df.write \
                .format("org.elasticsearch.spark.sql") \
                .mode("overwrite") \
                .options(**test_options) \
                .save()
            
            self.logger.info(f"Validated Wikipedia Elasticsearch connection to {','.join(self.config.hosts)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Wikipedia Elasticsearch connection validation failed: {e}")
            return False
    
    def write(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write Wikipedia DataFrame to Elasticsearch.
        
        Args:
            df: Wikipedia DataFrame to write
            metadata: Metadata about the data being written
            
        Returns:
            True if write was successful, False otherwise
        """
        try:
            record_count = df.count()
            self.logger.info(f"Writing {record_count} Wikipedia articles to Elasticsearch index {self.index_name}")
            
            # Transform Wikipedia data for Elasticsearch
            transformed_df = self._transform_for_elasticsearch(df)
            
            # Clear index if configured (demo mode)
            if self.config.clear_before_write:
                self._clear_index()
            
            # Build write options
            write_options = self.base_options.copy()
            write_options["es.resource"] = f"{self.index_name}/doc"
            
            # Write to Elasticsearch
            transformed_df.write \
                .format("org.elasticsearch.spark.sql") \
                .mode("append") \
                .options(**write_options) \
                .save()
            
            self.logger.info(f"Successfully wrote {record_count} Wikipedia articles to index {self.index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write Wikipedia articles to Elasticsearch: {e}")
            return False
    
    def _transform_for_elasticsearch(self, df: DataFrame) -> DataFrame:
        """
        Transform Wikipedia DataFrame for Elasticsearch indexing.
        
        Args:
            df: Input Wikipedia DataFrame
            
        Returns:
            Transformed DataFrame optimized for Elasticsearch
        """
        df_transformed = df
        
        # Add location fields as geo_point if coordinates exist
        if "latitude" in df.columns and "longitude" in df.columns:
            df_transformed = df_transformed.withColumn(
                "location",
                when(
                    col("latitude").isNotNull() & col("longitude").isNotNull(),
                    struct(
                        col("latitude").alias("lat"),
                        col("longitude").alias("lon")
                    )
                ).otherwise(lit(None))
            )
        
        # Create search text for full-text search
        # Wikipedia articles already have comprehensive text, but we'll create optimized search field
        text_fields = []
        
        if "title" in df.columns:
            text_fields.append(col("title"))
        if "short_summary" in df.columns:
            text_fields.append(col("short_summary"))
        
        if text_fields:
            df_transformed = df_transformed.withColumn(
                "search_text",
                concat_ws(" ", *text_fields)
            )
        
        # Ensure content fields are present and non-null
        if "long_summary" in df.columns:
            df_transformed = df_transformed.withColumn(
                "long_summary",
                when(col("long_summary").isNotNull(), col("long_summary")).otherwise("")
            )
            
            # Add content length for relevance scoring
            df_transformed = df_transformed.withColumn(
                "content_length",
                length(col("long_summary"))
            )
        
        # Structure location data if present
        location_fields = ["best_city", "best_state", "overall_confidence"]
        location_cols = [f for f in location_fields if f in df.columns]
        if location_cols:
            df_transformed = df_transformed.withColumn(
                "location_info",
                struct(*[col(f).alias(f) for f in location_cols])
            )
        
        # Ensure numeric fields are properly typed
        numeric_fields = [
            "relevance_score", "overall_confidence", 
            "latitude", "longitude", "content_length"
        ]
        
        for field in numeric_fields:
            if field in df.columns:
                df_transformed = df_transformed.withColumn(
                    field,
                    col(field).cast("double")
                )
        
        # Handle key_topics array if present
        if "key_topics" in df.columns:
            # Ensure it's an array type (already should be from processing)
            pass
        
        # Add created/updated timestamps if not present
        from pyspark.sql.functions import current_timestamp
        if "created_at" not in df.columns:
            df_transformed = df_transformed.withColumn(
                "created_at",
                current_timestamp()
            )
        if "updated_at" not in df.columns:
            df_transformed = df_transformed.withColumn(
                "updated_at",
                current_timestamp()
            )
        
        return df_transformed
    
    def _clear_index(self) -> None:
        """Clear the Wikipedia index by deleting and recreating it."""
        try:
            self.logger.info(f"Clearing Wikipedia index {self.index_name} (demo mode)")
            
            # Create empty DataFrame to trigger index deletion
            empty_df = self.spark.createDataFrame([], "page_id: integer")
            
            clear_options = self.base_options.copy()
            clear_options["es.resource"] = f"{self.index_name}/doc"
            clear_options["es.index.auto.create"] = "true"
            
            empty_df.write \
                .format("org.elasticsearch.spark.sql") \
                .mode("overwrite") \
                .options(**clear_options) \
                .save()
                
        except Exception as e:
            self.logger.debug(f"Could not clear Wikipedia index {self.index_name}: {e}")
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "elasticsearch_wikipedia"
    
    @staticmethod
    def get_mapping() -> Dict[str, Any]:
        """
        Get the Elasticsearch mapping for Wikipedia articles index.
        
        Returns:
            Dictionary containing the mapping configuration
        """
        return {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "1s",
                "analysis": {
                    "analyzer": {
                        "content_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "char_filter": ["html_strip"],
                            "filter": [
                                "lowercase",
                                "stop",
                                "snowball",
                                "shingle"
                            ]
                        },
                        "title_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "asciifolding",
                                "edge_ngram"
                            ]
                        }
                    },
                    "filter": {
                        "shingle": {
                            "type": "shingle",
                            "min_shingle_size": 2,
                            "max_shingle_size": 3
                        },
                        "edge_ngram": {
                            "type": "edge_ngram",
                            "min_gram": 2,
                            "max_gram": 15
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    # Identifiers
                    "page_id": {"type": "integer"},
                    "correlation_id": {"type": "keyword"},
                    "url": {"type": "keyword"},
                    
                    # Title and summaries
                    "title": {
                        "type": "text",
                        "analyzer": "title_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "short_summary": {"type": "text", "analyzer": "content_analyzer"},
                    "long_summary": {
                        "type": "text",
                        "analyzer": "content_analyzer",
                        "term_vector": "with_positions_offsets"  # For highlighting
                    },
                    
                    # Location data
                    "location": {"type": "geo_point"},
                    "latitude": {"type": "float"},
                    "longitude": {"type": "float"},
                    "location_info": {
                        "type": "object",
                        "properties": {
                            "best_city": {"type": "keyword"},
                            "best_state": {"type": "keyword"},
                            "overall_confidence": {"type": "float"}
                        }
                    },
                    
                    # Content analysis
                    "key_topics": {"type": "keyword"},
                    "relevance_score": {"type": "float"},
                    "content_length": {"type": "integer"},
                    
                    # Search and embedding fields
                    "search_text": {"type": "text", "analyzer": "content_analyzer"},
                    "embedding_text": {"type": "text"},
                    
                    # Embeddings (if present) - using dense_vector for similarity search
                    "embeddings": {
                        "type": "dense_vector",
                        "dims": 768,
                        "index": True,  # Enable kNN search
                        "similarity": "cosine"
                    },
                    
                    # Quality and metadata
                    "data_quality_score": {"type": "float"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"}
                }
            }
        }