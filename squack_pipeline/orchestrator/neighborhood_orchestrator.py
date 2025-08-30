"""Neighborhood-specific pipeline orchestrator."""

import time
from typing import Optional
from pathlib import Path

from squack_pipeline.orchestrator.base_entity_orchestrator import BaseEntityOrchestrator
from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.loaders.connection import DuckDBConnectionManager
from squack_pipeline.loaders.neighborhood_loader import NeighborhoodLoader
from squack_pipeline.processors.neighborhood_silver_processor import NeighborhoodSilverProcessor
from squack_pipeline.processors.neighborhood_gold_processor import NeighborhoodGoldProcessor
from squack_pipeline.models import (
    EntityType, MedallionTier, ProcessingStage,
    ProcessingContext, TableIdentifier, ProcessingResult
)
from squack_pipeline.models.pipeline_models import ProcessedTable


class NeighborhoodPipelineOrchestrator(BaseEntityOrchestrator):
    """Orchestrator for neighborhood data pipeline."""
    
    def __init__(self, settings: PipelineSettings, connection_manager: DuckDBConnectionManager):
        """Initialize neighborhood pipeline orchestrator."""
        super().__init__(settings, connection_manager)
        
        # Initialize neighborhood-specific components
        self.loader = NeighborhoodLoader(settings)
        self.loader.set_connection(connection_manager.get_connection())
        
        self.silver_processor = NeighborhoodSilverProcessor(settings)
        self.silver_processor.set_connection(connection_manager.get_connection())
        
        self.gold_processor = NeighborhoodGoldProcessor(settings)
        self.gold_processor.set_connection(connection_manager.get_connection())
    
    @property
    def entity_type(self) -> EntityType:
        """Return the entity type."""
        return EntityType.NEIGHBORHOOD
    
    def load_bronze(self, sample_size: Optional[int] = None) -> ProcessedTable:
        """Load neighborhood data into Bronze tier.
        
        Args:
            sample_size: Optional number of records to load
            
        Returns:
            ProcessedTable for the created Bronze table
        """
        # Create table identifier
        timestamp = int(time.time())
        table_id = TableIdentifier(
            entity_type=EntityType.NEIGHBORHOOD,
            tier=MedallionTier.BRONZE,
            timestamp=0
        )
        
        # Load data with the correct table name
        actual_sample = sample_size or self.settings.data.sample_size
        table_name = self.loader.load(
            table_name=table_id.table_name,
            sample_size=actual_sample
        )
        
        # Validate
        if not self.loader.validate(table_name):
            raise ValueError(f"Bronze validation failed for {table_name}")
        
        # Update metrics
        record_count = self.loader.count_records(table_name)
        self.metrics.bronze_records = record_count
        
        # Log sample data
        sample_data = self.loader.get_sample_data(table_name, limit=3)
        if sample_data:
            self.logger.info("Sample neighborhood data:")
            for i, hood in enumerate(sample_data, 1):
                self.logger.info(f"  {i}. {hood.get('name', 'N/A')} in {hood.get('city', 'N/A')}")
        
        # Return ProcessedTable
        return ProcessedTable(
            table_name=table_name,
            entity_type=EntityType.NEIGHBORHOOD,
            tier=MedallionTier.BRONZE,
            record_count=record_count,
            timestamp=timestamp
        )
    
    def process_silver(self, bronze_table: ProcessedTable) -> ProcessedTable:
        """Process neighborhood Bronze data into Silver tier.
        
        Args:
            bronze_table: ProcessedTable for Bronze table
            
        Returns:
            ProcessedTable for the created Silver table
        """
        timestamp = int(time.time())
        
        # Process using the base TransformationProcessor interface
        output_table = self.silver_processor.process(
            input_table=bronze_table.table_name
        )
        
        # Get record count from the created table
        count_query = f"SELECT COUNT(*) as cnt FROM {output_table}"
        result = self.connection_manager.get_connection().execute(count_query).fetchone()
        record_count = result[0] if result else 0
        
        # Update metrics
        self.metrics.silver_records = record_count
        
        self.logger.info(
            f"Silver processing: {bronze_table.record_count} → {record_count} records"
        )
        
        # Return ProcessedTable
        return ProcessedTable(
            table_name=output_table,
            entity_type=EntityType.NEIGHBORHOOD,
            tier=MedallionTier.SILVER,
            record_count=record_count,
            timestamp=timestamp
        )
    
    def process_gold(self, silver_table: ProcessedTable) -> ProcessedTable:
        """Process neighborhood Silver data into Gold tier.
        
        Args:
            silver_table: ProcessedTable for Silver table
            
        Returns:
            ProcessedTable for the created Gold table
        """
        timestamp = int(time.time())
        
        # Process using the base TransformationProcessor interface
        output_table = self.gold_processor.process(
            input_table=silver_table.table_name
        )
        
        # Get record count from the created table
        count_query = f"SELECT COUNT(*) as cnt FROM {output_table}"
        result = self.connection_manager.get_connection().execute(count_query).fetchone()
        record_count = result[0] if result else 0
        
        # Update metrics
        self.metrics.gold_records = record_count
        
        self.logger.info(
            f"Gold processing: {silver_table.record_count} → {record_count} records"
        )
        
        # Return ProcessedTable
        return ProcessedTable(
            table_name=output_table,
            entity_type=EntityType.NEIGHBORHOOD,
            tier=MedallionTier.GOLD,
            record_count=record_count,
            timestamp=timestamp
        )