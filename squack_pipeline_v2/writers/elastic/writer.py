"""Unified Elasticsearch writer for all entity types."""

import logging
from typing import Dict, Any

from squack_pipeline_v2.writers.elastic.property import PropertyWriter
from squack_pipeline_v2.writers.elastic.neighborhood import NeighborhoodWriter
from squack_pipeline_v2.writers.elastic.wikipedia import WikipediaWriter
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import log_stage
from squack_pipeline_v2.core.settings import PipelineSettings

logger = logging.getLogger(__name__)


class ElasticsearchWriter:
    """Unified Elasticsearch writer for all entity types."""
    
    def __init__(
        self,
        connection_manager: DuckDBConnectionManager,
        settings: PipelineSettings
    ):
        """Initialize unified writer with all entity writers.
        
        Args:
            connection_manager: DuckDB connection manager
            settings: Pipeline settings
        """
        self.connection_manager = connection_manager
        self.settings = settings
        
        # Initialize entity-specific writers
        self.property_writer = PropertyWriter(connection_manager, settings)
        self.neighborhood_writer = NeighborhoodWriter(connection_manager, settings)
        self.wikipedia_writer = WikipediaWriter(connection_manager, settings)
        
        # Track total documents indexed
        self.documents_indexed = 0
    
    @log_stage("Elasticsearch: Index properties")
    def index_properties(
        self,
        table_name: str = "gold_properties",
        index_name: str = "properties",
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """Index properties to Elasticsearch.
        
        Args:
            table_name: DuckDB table containing properties
            index_name: Target Elasticsearch index
            batch_size: Number of documents per batch
            
        Returns:
            Indexing statistics
        """
        stats = self.property_writer.index_properties(table_name, index_name, batch_size)
        self.documents_indexed += stats.get('indexed', 0)
        return stats
    
    @log_stage("Elasticsearch: Index neighborhoods")
    def index_neighborhoods(
        self,
        table_name: str = "gold_neighborhoods",
        index_name: str = "neighborhoods",
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """Index neighborhoods to Elasticsearch.
        
        Args:
            table_name: DuckDB table containing neighborhoods
            index_name: Target Elasticsearch index
            batch_size: Number of documents per batch
            
        Returns:
            Indexing statistics
        """
        stats = self.neighborhood_writer.index_neighborhoods(table_name, index_name, batch_size)
        self.documents_indexed += stats.get('indexed', 0)
        return stats
    
    @log_stage("Elasticsearch: Index Wikipedia")
    def index_wikipedia(
        self,
        table_name: str = "gold_wikipedia",
        index_name: str = "wikipedia",
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """Index Wikipedia articles to Elasticsearch.
        
        Args:
            table_name: DuckDB table containing Wikipedia articles
            index_name: Target Elasticsearch index
            batch_size: Number of documents per batch
            
        Returns:
            Indexing statistics
        """
        stats = self.wikipedia_writer.index_wikipedia(table_name, index_name, batch_size)
        self.documents_indexed += stats.get('indexed', 0)
        return stats
    
    @log_stage("Elasticsearch: Index all entities")
    def index_all(self) -> Dict[str, Any]:
        """Index all entity types to Elasticsearch.
        
        Returns:
            Combined indexing statistics
        """
        stats = {}
        
        # Define tables to index
        tables = [
            ("gold_properties", "properties", self.index_properties),
            ("gold_neighborhoods", "neighborhoods", self.index_neighborhoods),
            ("gold_wikipedia", "wikipedia", self.index_wikipedia)
        ]
        
        # Index each table if it exists
        for table_name, index_name, index_method in tables:
            if self.connection_manager.table_exists(table_name):
                logger.info(f"Indexing {table_name} to {index_name}")
                stats[index_name] = index_method()
            else:
                logger.warning(f"Table {table_name} does not exist, skipping")
        
        # Return combined statistics
        return {
            "total_indexed": self.documents_indexed,
            "entities": stats
        }