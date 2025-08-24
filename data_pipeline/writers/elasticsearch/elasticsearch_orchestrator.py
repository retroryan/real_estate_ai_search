"""
Elasticsearch writer orchestrator.

This module coordinates entity-specific Elasticsearch writers to index
all entity types with appropriate mappings and configurations.
"""

import logging
from typing import Any, Dict

from pyspark.sql import DataFrame, SparkSession

from data_pipeline.config.models import ElasticsearchConfig
from data_pipeline.writers.base import DataWriter
from data_pipeline.writers.elasticsearch.elasticsearch_properties import PropertyElasticsearchWriter
from data_pipeline.writers.elasticsearch.elasticsearch_neighborhoods import NeighborhoodElasticsearchWriter
from data_pipeline.writers.elasticsearch.elasticsearch_wikipedia import WikipediaElasticsearchWriter

logger = logging.getLogger(__name__)


class ElasticsearchOrchestrator(DataWriter):
    """
    Orchestrator for entity-specific Elasticsearch writers.
    
    This writer coordinates the entity-specific writers to index all
    entity types to their respective Elasticsearch indices.
    """
    
    def __init__(self, config: ElasticsearchConfig, spark: SparkSession):
        """
        Initialize the Elasticsearch orchestrator.
        
        Args:
            config: Elasticsearch configuration
            spark: SparkSession instance
        """
        super().__init__(config)
        self.config = config
        self.spark = spark
        self.logger = logging.getLogger(__name__)
        
        # Initialize entity-specific writers
        self.property_writer = PropertyElasticsearchWriter(config, spark)
        self.neighborhood_writer = NeighborhoodElasticsearchWriter(config, spark)
        self.wikipedia_writer = WikipediaElasticsearchWriter(config, spark)
    
    def validate_connection(self) -> bool:
        """
        Validate the connection to Elasticsearch.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Test connection with one of the writers
            success = self.property_writer.validate_connection()
            if success:
                self.logger.info(f"Successfully validated Elasticsearch connection to {','.join(self.config.hosts)}")
            return success
            
        except Exception as e:
            self.logger.error(f"Elasticsearch connection validation failed: {e}")
            return False
    
    def write(self, data: Dict[str, DataFrame], metadata: Dict[str, Any]) -> bool:
        """
        Write all entity types to Elasticsearch using entity-specific writers.
        
        Args:
            data: Dictionary with keys 'properties', 'neighborhoods', 'wikipedia' mapped to DataFrames
            metadata: Metadata about the data being written
            
        Returns:
            True if all writes successful, False otherwise
        """
        try:
            return self._write_entities(data, metadata)
            
        except Exception as e:
            self.logger.error(f"Failed to write to Elasticsearch: {e}")
            return False
    
    def _write_entities(self, data: Dict[str, DataFrame], metadata: Dict[str, Any]) -> bool:
        """
        Write entities to their respective indices.
        
        Args:
            data: Dictionary with entity DataFrames
            metadata: Metadata about the data
            
        Returns:
            True if all writes successful
        """
        success = True
        
        # Write properties to properties index
        if "properties" in data:
            self.logger.info("Writing properties to Elasticsearch...")
            if not self.property_writer.write(data["properties"], metadata):
                self.logger.error("Failed to write properties to Elasticsearch")
                success = False
        
        # Write neighborhoods to neighborhoods index
        if "neighborhoods" in data:
            self.logger.info("Writing neighborhoods to Elasticsearch...")
            if not self.neighborhood_writer.write(data["neighborhoods"], metadata):
                self.logger.error("Failed to write neighborhoods to Elasticsearch")
                success = False
        
        # Write Wikipedia articles to wikipedia index
        if "wikipedia" in data:
            self.logger.info("Writing Wikipedia articles to Elasticsearch...")
            if not self.wikipedia_writer.write(data["wikipedia"], metadata):
                self.logger.error("Failed to write Wikipedia articles to Elasticsearch")
                success = False
        
        if success:
            self.logger.info("Elasticsearch indexing completed successfully")
        return success
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "elasticsearch_orchestrator"