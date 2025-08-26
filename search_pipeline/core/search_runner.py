"""
Search pipeline runner for processing and indexing documents to Elasticsearch.

This module receives DataFrames from the pipeline fork and transforms them
into search documents using document builders before indexing to Elasticsearch.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from pyspark.sql import DataFrame, SparkSession

from search_pipeline.models.config import SearchPipelineConfig
from search_pipeline.models.results import SearchIndexResult, SearchPipelineResult
from search_pipeline.transformers import (
    PropertyDataFrameTransformer,
    NeighborhoodDataFrameTransformer,
    WikipediaDataFrameTransformer
)

logger = logging.getLogger(__name__)

# Import existing embedding generators - these MUST be available for embeddings to work
from data_pipeline.processing.entity_embeddings import (
    PropertyEmbeddingGenerator,
    NeighborhoodEmbeddingGenerator, 
    WikipediaEmbeddingGenerator
)


def truncate_message(msg: str, max_length: int = 200) -> str:
    """
    Truncate a message to a maximum length.
    
    Args:
        msg: Message to truncate
        max_length: Maximum length (default 200)
    
    Returns:
        Truncated message
    """
    msg_str = str(msg)
    if len(msg_str) > max_length:
        return msg_str[:max_length] + f"... (truncated {len(msg_str) - max_length} chars)"
    return msg_str


class SearchPipelineRunner:
    """
    Runs the search pipeline to process and index documents to Elasticsearch.
    
    This class receives DataFrames from the pipeline fork, transforms them
    into search documents using document builders, and indexes them to Elasticsearch.
    """
    
    def __init__(self, spark: SparkSession, config: SearchPipelineConfig):
        """
        Initialize the search pipeline runner.
        
        Args:
            spark: Active Spark session
            config: Search pipeline configuration
        """
        self.spark = spark
        self.config = config
        self.pipeline_id = str(uuid.uuid4())
        
        # Initialize DataFrame transformers
        self.transformers = {
            "properties": PropertyDataFrameTransformer(),
            "neighborhoods": NeighborhoodDataFrameTransformer(),
            "wikipedia": WikipediaDataFrameTransformer(),
        }
        
        # Initialize embedding generators if configured
        self.embedding_generators = {}
        if self.config.embedding_config:
            self.embedding_generators = {
                "properties": PropertyEmbeddingGenerator(spark, self.config.embedding_config),
                "neighborhoods": NeighborhoodEmbeddingGenerator(spark, self.config.embedding_config),
                "wikipedia": WikipediaEmbeddingGenerator(spark, self.config.embedding_config),
            }
            logger.info(f"Embedding generators initialized with {self.config.embedding_config.provider.value} provider")
        else:
            logger.info("Embedding generation disabled - no embedding config provided")
        
        logger.info(f"Search pipeline runner initialized (ID: {self.pipeline_id})")
        
        # Validate configuration on initialization
        if self.config.enabled and self.config.validate_connection:
            self._validate_configuration()
    
    def _validate_configuration(self) -> None:
        """
        Validate the Elasticsearch configuration.
        
        Checks for common configuration issues based on best practices.
        """
        # Check Spark version compatibility
        spark_version = self.spark.version
        major, minor = spark_version.split(".")[:2]
        spark_version_num = float(f"{major}.{minor}")
        
        if spark_version_num >= 3.5:
            logger.warning(
                f"Spark {spark_version} detected. Spark 3.5+ may not be fully supported "
                "by Elasticsearch connector. Consider using Spark 3.4.x if issues occur."
            )
        elif spark_version_num < 3.0:
            logger.warning(
                f"Spark {spark_version} detected. Spark 3.0+ is recommended "
                "for Elasticsearch connector."
            )
        
        # Log configuration for debugging
        logger.info(f"Elasticsearch nodes: {self.config.elasticsearch.nodes}")
        logger.info(f"Index prefix: {self.config.elasticsearch.index_prefix}")
        logger.info(f"Bulk batch size: {self.config.elasticsearch.bulk.batch_size_entries} docs")
        logger.info(f"Node discovery: {self.config.elasticsearch.nodes_discovery}")
    
    def process(self, dataframes: Dict[str, DataFrame]) -> SearchPipelineResult:
        """
        Process DataFrames and index them to Elasticsearch.
        
        Args:
            dataframes: Dictionary of entity type to DataFrame
                       Expected keys: properties, neighborhoods, wikipedia
        
        Returns:
            SearchPipelineResult with indexing statistics
        """
        logger.info(f"Starting search pipeline processing (ID: {self.pipeline_id})")
        
        result = SearchPipelineResult(
            pipeline_id=self.pipeline_id,
            start_time=datetime.now()
        )
        
        if not self.config.enabled:
            logger.info("Search pipeline is disabled")
            result.complete(success=True)
            return result
        
        try:
            # Process each entity type
            for entity_type, df in dataframes.items():
                if df is not None and self.config.should_process(entity_type):
                    entity_result = self._process_entity(entity_type, df)
                    result.add_entity_result(entity_result)
            
            result.complete(success=True)
            logger.info(f"Search pipeline completed successfully\n{result.get_summary()}")
            
        except Exception as e:
            error_msg = f"Search pipeline failed: {truncate_message(str(e))}"
            logger.error(error_msg)
            result.complete(success=False, error=error_msg)
        
        return result
    
    def _process_entity(self, entity_type: str, df: DataFrame) -> SearchIndexResult:
        """
        Process and index a single entity type to Elasticsearch.
        
        Args:
            entity_type: Type of entity (properties, neighborhoods, wikipedia)
            df: DataFrame to index
        
        Returns:
            SearchIndexResult with indexing statistics
        """
        start_time = datetime.now()
        index_name = self.config.elasticsearch.get_index_name(entity_type)
        
        logger.info(f"Processing {entity_type} for index {index_name}")
        
        result = SearchIndexResult(
            entity_type=entity_type,
            index_name=index_name
        )
        
        try:
            # Get the appropriate transformer
            transformer = self.transformers.get(entity_type)
            if not transformer:
                raise ValueError(f"No DataFrame transformer found for entity type: {entity_type}")
            
            # Generate embeddings if configured and available
            processed_df = df
            if entity_type in self.embedding_generators:
                logger.info(f"Generating embeddings for {entity_type}")
                embedding_generator = self.embedding_generators[entity_type]
                
                # Prepare embedding text using existing logic
                df_with_text = embedding_generator.prepare_embedding_text(processed_df)
                
                # Generate embeddings
                processed_df = embedding_generator.generate_embeddings(df_with_text)
                
                logger.info(f"Embedding generation completed for {entity_type}")
            else:
                logger.info(f"Embedding generation skipped for {entity_type} - no generator available")
            
            # Transform DataFrame using transformer (stays distributed)
            logger.info(f"Transforming {entity_type} DataFrame")
            transformed_df = transformer.transform(processed_df)
            
            # Write DataFrame directly to Elasticsearch
            self._write_dataframe_to_elasticsearch(transformed_df, index_name)
            
            # Record success (simplified for demo)
            result.documents_indexed = 1  # Simplified for demo
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Successfully indexed {entity_type} documents")
            
        except Exception as e:
            error_msg = f"Failed to index {entity_type}: {truncate_message(str(e))}"
            logger.error(error_msg)
            result.error_messages.append(error_msg)
            
            # Record failure (simplified for demo)
            result.documents_failed = 1
        
        return result
    
    def _write_dataframe_to_elasticsearch(self, df: DataFrame, index_name: str) -> None:
        """
        Write DataFrame directly to Elasticsearch using Spark connector.
        
        Args:
            df: Transformed DataFrame ready for indexing
            index_name: Target Elasticsearch index
        """
        # Write to Elasticsearch using Spark connector
        es_conf = self.config.elasticsearch.get_spark_conf()
        es_conf["es.resource"] = index_name
        es_conf["es.mapping.id"] = "doc_id"  # Use the 'doc_id' field from transformed DataFrame
        
        # Log configuration for debugging (but truncate long values)
        debug_conf = {k: str(v)[:200] + "..." if len(str(v)) > 200 else v 
                      for k, v in es_conf.items()}
        logger.debug(f"Elasticsearch write configuration: {debug_conf}")
        
        # Write DataFrame directly to Elasticsearch
        df.write \
            .format("org.elasticsearch.spark.sql") \
            .options(**es_conf) \
            .mode("append") \
            .save()
    
    def validate_connection(self) -> bool:
        """
        Validate connection to Elasticsearch.
        
        Returns:
            True if connection is valid
        """
        try:
            # Create a simple test DataFrame
            test_df = self.spark.createDataFrame(
                [{"doc_id": "test-1", "entity_id": "test-1", "entity_type": "test", "message": "test", "timestamp": datetime.now()}]
            )
            
            # Try to write to a test index
            test_index = f"{self.config.elasticsearch.index_prefix}_connection_test"
            
            es_conf = self.config.elasticsearch.get_spark_conf()
            es_conf["es.resource"] = test_index
            es_conf["es.mapping.id"] = "doc_id"
            
            # Attempt write with single document
            test_df.write \
                  .format("org.elasticsearch.spark.sql") \
                  .options(**es_conf) \
                  .mode("overwrite") \
                  .save()
            
            logger.info("Elasticsearch connection validated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Elasticsearch connection validation failed: {truncate_message(str(e))}")
            return False
    
    def get_index_stats(self, entity_type: str) -> Optional[Dict]:
        """
        Get statistics for an Elasticsearch index.
        
        Args:
            entity_type: Entity type to get stats for
        
        Returns:
            Dictionary of index statistics or None
        """
        try:
            index_name = self.config.elasticsearch.get_index_name(entity_type)
            
            # Read from Elasticsearch to get count
            es_conf = self.config.elasticsearch.get_spark_conf()
            es_conf["es.resource"] = index_name
            
            df = self.spark.read \
                         .format("org.elasticsearch.spark.sql") \
                         .options(**es_conf) \
                         .load()
            
            count = df.count()
            
            return {
                "index_name": index_name,
                "document_count": count,
                "entity_type": entity_type
            }
            
        except Exception as e:
            logger.error(f"Failed to get index stats for {entity_type}: {e}")
            return None


# Alias for backward compatibility
SearchRunner = SearchPipelineRunner