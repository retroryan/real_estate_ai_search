"""
Search pipeline runner for processing and indexing documents to Elasticsearch.

This module receives DataFrames from the pipeline fork and processes them
for Elasticsearch indexing using the Spark connector with best practices.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, lit, current_timestamp

from search_pipeline.models.config import SearchPipelineConfig
from search_pipeline.models.results import SearchIndexResult, SearchPipelineResult

logger = logging.getLogger(__name__)


class SearchPipelineRunner:
    """
    Runs the search pipeline to process and index documents to Elasticsearch.
    
    This class receives DataFrames from the pipeline fork after text processing
    and prepares them for Elasticsearch indexing. It follows current best practices
    for Spark-Elasticsearch integration.
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
            error_msg = f"Search pipeline failed: {e}"
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
            # Prepare DataFrame for indexing
            prepared_df = self._prepare_dataframe(entity_type, df)
            
            # Get row count before indexing
            doc_count = prepared_df.count()
            logger.info(f"Indexing {doc_count:,} {entity_type} documents")
            
            # Write to Elasticsearch using Spark connector
            self._write_to_elasticsearch(prepared_df, index_name)
            
            # Record success
            result.documents_indexed = doc_count
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            logger.info(
                f"Successfully indexed {doc_count:,} {entity_type} documents "
                f"in {result.duration_seconds:.2f} seconds "
                f"({result.documents_per_second:.0f} docs/sec)"
            )
            
        except Exception as e:
            error_msg = f"Failed to index {entity_type}: {e}"
            logger.error(error_msg)
            result.error_messages.append(error_msg)
            
            # Try to get document count for failed records
            try:
                result.documents_failed = df.count()
            except:
                pass
        
        return result
    
    def _prepare_dataframe(self, entity_type: str, df: DataFrame) -> DataFrame:
        """
        Prepare DataFrame for Elasticsearch indexing.
        
        Args:
            entity_type: Type of entity
            df: Raw DataFrame from pipeline
        
        Returns:
            DataFrame ready for indexing
        """
        # Add metadata fields
        prepared_df = df.withColumn("_entity_type", lit(entity_type)) \
                       .withColumn("_indexed_at", current_timestamp()) \
                       .withColumn("_pipeline_id", lit(self.pipeline_id))
        
        # Entity-specific preparation
        if entity_type == "properties":
            prepared_df = self._prepare_properties(prepared_df)
        elif entity_type == "neighborhoods":
            prepared_df = self._prepare_neighborhoods(prepared_df)
        elif entity_type == "wikipedia":
            prepared_df = self._prepare_wikipedia(prepared_df)
        
        return prepared_df
    
    def _prepare_properties(self, df: DataFrame) -> DataFrame:
        """
        Prepare property documents for indexing.
        
        Args:
            df: Property DataFrame
        
        Returns:
            Prepared DataFrame
        """
        # Ensure required fields exist
        required_fields = ["listing_id", "price", "embedding_text"]
        existing_fields = df.columns
        
        for field in required_fields:
            if field not in existing_fields:
                logger.warning(f"Property field '{field}' not found in DataFrame")
        
        # Use listing_id as document ID if configured
        if self.config.elasticsearch.mapping_id == "listing_id":
            df = df.withColumn("_id", col("listing_id"))
        
        return df
    
    def _prepare_neighborhoods(self, df: DataFrame) -> DataFrame:
        """
        Prepare neighborhood documents for indexing.
        
        Args:
            df: Neighborhood DataFrame
        
        Returns:
            Prepared DataFrame
        """
        # Ensure required fields exist
        if "neighborhood_id" in df.columns and self.config.elasticsearch.mapping_id == "neighborhood_id":
            df = df.withColumn("_id", col("neighborhood_id"))
        
        return df
    
    def _prepare_wikipedia(self, df: DataFrame) -> DataFrame:
        """
        Prepare Wikipedia documents for indexing.
        
        Args:
            df: Wikipedia DataFrame
        
        Returns:
            Prepared DataFrame
        """
        # Ensure required fields exist
        if "page_id" in df.columns and self.config.elasticsearch.mapping_id == "page_id":
            df = df.withColumn("_id", col("page_id"))
        
        return df
    
    def _write_to_elasticsearch(self, df: DataFrame, index_name: str) -> None:
        """
        Write DataFrame to Elasticsearch using Spark connector.
        
        Args:
            df: Prepared DataFrame
            index_name: Target Elasticsearch index
        """
        # Get Spark configuration for Elasticsearch
        es_conf = self.config.elasticsearch.get_spark_conf()
        
        # Add index-specific configuration
        es_conf["es.resource"] = index_name
        
        # Log configuration for debugging
        logger.debug(f"Elasticsearch write configuration: {es_conf}")
        
        # Write DataFrame to Elasticsearch
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
                [("test", datetime.now())],
                ["message", "timestamp"]
            )
            
            # Try to write to a test index
            test_index = f"{self.config.elasticsearch.index_prefix}_connection_test"
            
            es_conf = self.config.elasticsearch.get_spark_conf()
            es_conf["es.resource"] = test_index
            
            # Attempt write with single document
            test_df.write \
                  .format("org.elasticsearch.spark.sql") \
                  .options(**es_conf) \
                  .mode("overwrite") \
                  .save()
            
            logger.info("Elasticsearch connection validated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Elasticsearch connection validation failed: {e}")
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