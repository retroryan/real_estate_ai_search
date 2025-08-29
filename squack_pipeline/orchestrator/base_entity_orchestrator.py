"""Base orchestrator for entity-specific pipelines."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.loaders.connection import DuckDBConnectionManager
from squack_pipeline.models import (
    EntityType, MedallionTier, ProcessingStage, 
    ProcessingContext, TableIdentifier, ProcessingResult
)
from squack_pipeline.models.pipeline_models import ProcessedTable
from squack_pipeline.utils.logging import PipelineLogger


class BaseEntityOrchestrator(ABC):
    """Base class for entity-specific pipeline orchestrators."""
    
    def __init__(self, settings: PipelineSettings, connection_manager: DuckDBConnectionManager):
        """Initialize the entity orchestrator.
        
        Args:
            settings: Pipeline configuration settings
            connection_manager: Shared DuckDB connection manager
        """
        self.settings = settings
        self.connection_manager = connection_manager
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        self.metrics: Dict[str, Any] = {
            "bronze_records": 0,
            "silver_records": 0,
            "gold_records": 0,
            "elasticsearch_records": 0,
        }
        
    @property
    @abstractmethod
    def entity_type(self) -> EntityType:
        """Return the entity type this orchestrator handles."""
        pass
    
    @abstractmethod
    def load_bronze(self, sample_size: Optional[int] = None) -> ProcessedTable:
        """Load raw data into Bronze tier.
        
        Args:
            sample_size: Optional number of records to load
            
        Returns:
            ProcessedTable for the created Bronze table
        """
        pass
    
    @abstractmethod
    def process_silver(self, bronze_table: ProcessedTable) -> ProcessedTable:
        """Process Bronze data into Silver tier.
        
        Args:
            bronze_table: ProcessedTable for Bronze table
            
        Returns:
            ProcessedTable for the created Silver table
        """
        pass
    
    @abstractmethod
    def process_gold(self, silver_table: ProcessedTable) -> ProcessedTable:
        """Process Silver data into Gold tier.
        
        Args:
            silver_table: ProcessedTable for Silver table
            
        Returns:
            ProcessedTable for the created Gold table
        """
        pass
    
    def write_to_elasticsearch(self, gold_table: ProcessedTable) -> int:
        """Write Gold data to Elasticsearch.
        
        Args:
            gold_table: Identifier for Gold table
            
        Returns:
            Number of records written
        """
        # This can be implemented in base class as it's common
        from squack_pipeline.writers.orchestrator import WriterOrchestrator
        
        writer = WriterOrchestrator(self.settings)
        
        # Create tables dict for writer orchestrator
        # Map entity type to plural form for consistency
        entity_plural = {
            "property": "properties",
            "neighborhood": "neighborhoods", 
            "wikipedia": "wikipedia"
        }.get(self.entity_type.value, self.entity_type.value)
        
        tables = {entity_plural: gold_table.table_name}
        
        # Write using the write_all method
        results = writer.write_all(self.connection_manager.get_connection(), tables)
        
        # Check Elasticsearch results
        es_results = results.get('elasticsearch', [])
        if es_results and len(es_results) > 0:
            result = es_results[0]
            if result.success:
                self.logger.success(
                    f"Wrote {result.record_count} {self.entity_type.value} records to Elasticsearch"
                )
                return result.record_count
            else:
                self.logger.error(f"Failed to write to Elasticsearch: {result.error}")
                return 0
        else:
            self.logger.warning("No Elasticsearch results returned")
            return 0
    
    def run(self, sample_size: Optional[int] = None, skip_elasticsearch: bool = False) -> Dict[str, Any]:
        """Run the complete pipeline for this entity.
        
        Args:
            sample_size: Optional number of records to process
            skip_elasticsearch: Whether to skip writing to Elasticsearch
            
        Returns:
            Dictionary of metrics from the run
        """
        try:
            self.logger.info(f"Starting {self.entity_type.value} pipeline")
            
            # Bronze tier
            self.logger.info(f"Loading {self.entity_type.value} Bronze tier")
            bronze_table = self.load_bronze(sample_size)
            self.logger.success(f"Bronze tier complete: {bronze_table.table_name}")
            
            # Silver tier
            self.logger.info(f"Processing {self.entity_type.value} Silver tier")
            silver_table = self.process_silver(bronze_table)
            self.logger.success(f"Silver tier complete: {silver_table.table_name}")
            
            # Gold tier
            self.logger.info(f"Processing {self.entity_type.value} Gold tier")
            gold_table = self.process_gold(silver_table)
            self.logger.success(f"Gold tier complete: {gold_table.table_name}")
            
            # Elasticsearch
            if not skip_elasticsearch:
                self.logger.info(f"Writing {self.entity_type.value} to Elasticsearch")
                es_count = self.write_to_elasticsearch(gold_table)
                self.metrics["elasticsearch_records"] = es_count
            
            self.logger.success(
                f"Completed {self.entity_type.value} pipeline: "
                f"{self.metrics['bronze_records']} → "
                f"{self.metrics['silver_records']} → "
                f"{self.metrics['gold_records']} records"
            )
            
            return self.metrics
            
        except Exception as e:
            self.logger.error(f"Pipeline failed for {self.entity_type.value}: {e}")
            raise