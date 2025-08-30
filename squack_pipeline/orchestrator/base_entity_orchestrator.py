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
from squack_pipeline.models.data_types import EntityMetrics
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
        self.metrics = EntityMetrics()
        
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
    
    def write_outputs(self, gold_table: ProcessedTable) -> int:
        """Write Gold data to all configured outputs (Parquet, Elasticsearch, etc).
        
        Args:
            gold_table: Identifier for Gold table
            
        Returns:
            Number of records written
        """
        from squack_pipeline.writers.orchestrator import WriterOrchestrator
        
        writer = WriterOrchestrator(self.settings)
        
        # Write using the new entity-specific method
        result = writer.write_entity(
            entity_type=self.entity_type,
            table_name=gold_table.table_name,
            connection=self.connection_manager.get_connection()
        )
        
        # Update embedding count in metrics
        self.metrics.embeddings_generated = result.embeddings_count
        
        # Log results for each destination
        total_written = 0
        for dest, dest_results in result.destinations.items():
            if dest_results.results:
                for write_result in dest_results.results:
                    if write_result.success:
                        self.logger.success(
                            f"Wrote {write_result.record_count} {self.entity_type.value} records to {dest.value}"
                        )
                        total_written = max(total_written, write_result.record_count)
                    else:
                        self.logger.error(f"Failed to write to {dest.value}: {write_result.error}")
        
        return total_written
    
    def write_to_elasticsearch(self, gold_table: ProcessedTable) -> int:
        """Legacy method for backward compatibility - calls write_outputs."""
        return self.write_outputs(gold_table)
    
    def run(self, sample_size: Optional[int] = None) -> EntityMetrics:
        """Run the complete pipeline for this entity.
        
        Args:
            sample_size: Optional number of records to process
            
        Returns:
            Dictionary of metrics from the run
        """
        try:
            self.logger.info(f"Starting {self.entity_type.value} pipeline")
            
            # Bronze tier
            self.logger.info(f"Loading {self.entity_type.value} Bronze tier")
            bronze_table = self.load_bronze(sample_size)
            self.metrics.bronze_records = bronze_table.record_count
            self.logger.success(f"Bronze tier complete: {bronze_table.table_name}")
            
            # Silver tier
            self.logger.info(f"Processing {self.entity_type.value} Silver tier")
            silver_table = self.process_silver(bronze_table)
            self.metrics.silver_records = silver_table.record_count
            self.logger.success(f"Silver tier complete: {silver_table.table_name}")
            
            # Gold tier
            self.logger.info(f"Processing {self.entity_type.value} Gold tier")
            gold_table = self.process_gold(silver_table)
            self.metrics.gold_records = gold_table.record_count
            self.logger.success(f"Gold tier complete: {gold_table.table_name}")
            
            # Write to all configured outputs (Parquet, Elasticsearch, etc)
            self.logger.info(f"Writing {self.entity_type.value} to configured outputs")
            written_count = self.write_outputs(gold_table)
            self.metrics.elasticsearch_records = written_count  # For backward compatibility
            
            self.logger.success(
                f"Completed {self.entity_type.value} pipeline: "
                f"{self.metrics.bronze_records} → "
                f"{self.metrics.silver_records} → "
                f"{self.metrics.gold_records} records"
            )
            
            return self.metrics
            
        except Exception as e:
            self.logger.error(f"Pipeline failed for {self.entity_type.value}: {e}")
            raise