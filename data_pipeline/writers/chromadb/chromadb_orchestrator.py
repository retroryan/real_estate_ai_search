"""
ChromaDB writer orchestrator.

This module coordinates entity-specific ChromaDB writers to store
embeddings for all entity types with proper metadata.
"""

import logging
from typing import Any, Dict

from pyspark.sql import DataFrame, SparkSession

from data_pipeline.writers.base import DataWriter
from .chromadb_config import ChromaDBWriterConfig
from .chromadb_properties import PropertyChromadbWriter
from .chromadb_neighborhoods import NeighborhoodChromadbWriter
from .chromadb_wikipedia import WikipediaChromadbWriter

logger = logging.getLogger(__name__)


class ChromadbOrchestrator(DataWriter):
    """
    Orchestrator for entity-specific ChromaDB writers.
    
    This writer coordinates the entity-specific writers to store embeddings
    for all entity types to their respective ChromaDB collections.
    """
    
    def __init__(self, config: ChromaDBWriterConfig, spark: SparkSession):
        """
        Initialize the ChromaDB orchestrator.
        
        Args:
            config: ChromaDB configuration
            spark: SparkSession instance
        """
        super().__init__(config)
        self.config = config
        self.spark = spark
        self.logger = logging.getLogger(__name__)
        
        # Initialize entity-specific writers
        self.property_writer = PropertyChromadbWriter(config, spark)
        self.neighborhood_writer = NeighborhoodChromadbWriter(config, spark)
        self.wikipedia_writer = WikipediaChromadbWriter(config, spark)
    
    def validate_connection(self) -> bool:
        """
        Validate the connection to ChromaDB.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Test connection with one of the writers
            success = self.property_writer.validate_connection()
            if success:
                self.logger.info(f"Successfully validated ChromaDB connection")
            return success
            
        except Exception as e:
            self.logger.error(f"ChromaDB connection validation failed: {e}")
            return False
    
    def write(self, data: Dict[str, DataFrame], metadata: Dict[str, Any]) -> bool:
        """
        Write all entity embeddings to ChromaDB using entity-specific writers.
        
        Args:
            data: Dictionary with keys 'properties', 'neighborhoods', 'wikipedia' mapped to DataFrames
            metadata: Metadata about the data being written
            
        Returns:
            True if all writes successful, False otherwise
        """
        try:
            return self._write_entities(data, metadata)
            
        except Exception as e:
            self.logger.error(f"Failed to write to ChromaDB: {e}")
            return False
    
    def _write_entities(self, data: Dict[str, DataFrame], metadata: Dict[str, Any]) -> bool:
        """
        Write entity embeddings to their respective collections.
        
        Args:
            data: Dictionary with entity DataFrames
            metadata: Metadata about the data
            
        Returns:
            True if all writes successful
        """
        success = True
        
        # Write properties to properties collection
        if "properties" in data:
            self.logger.info("Writing properties to ChromaDB...")
            if not self.property_writer.write(data["properties"], metadata):
                self.logger.error("Failed to write properties to ChromaDB")
                success = False
        
        # Write neighborhoods to neighborhoods collection
        if "neighborhoods" in data:
            self.logger.info("Writing neighborhoods to ChromaDB...")
            if not self.neighborhood_writer.write(data["neighborhoods"], metadata):
                self.logger.error("Failed to write neighborhoods to ChromaDB")
                success = False
        
        # Write Wikipedia articles to wikipedia collection
        if "wikipedia" in data:
            self.logger.info("Writing Wikipedia articles to ChromaDB...")
            if not self.wikipedia_writer.write(data["wikipedia"], metadata):
                self.logger.error("Failed to write Wikipedia articles to ChromaDB")
                success = False
        
        if success:
            self.logger.info("ChromaDB embedding storage completed successfully")
        return success
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "chromadb_orchestrator"