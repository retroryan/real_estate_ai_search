"""Property-specific pipeline orchestrator."""

import time
from typing import Optional
from pathlib import Path

from squack_pipeline.orchestrator.base_entity_orchestrator import BaseEntityOrchestrator
from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.loaders.connection import DuckDBConnectionManager
from squack_pipeline.loaders.property_loader import PropertyLoader
from squack_pipeline.processors.property_silver_processor import PropertySilverProcessor
from squack_pipeline.processors.property_gold_processor import PropertyGoldProcessor
from squack_pipeline.models import (
    EntityType, MedallionTier, ProcessingStage,
    ProcessingContext, TableIdentifier, ProcessingResult
)
from squack_pipeline.models.pipeline_models import ProcessedTable


class PropertyPipelineOrchestrator(BaseEntityOrchestrator):
    """Orchestrator for property data pipeline."""
    
    def __init__(self, settings: PipelineSettings, connection_manager: DuckDBConnectionManager):
        """Initialize property pipeline orchestrator."""
        super().__init__(settings, connection_manager)
        
        # Initialize property-specific components
        self.loader = PropertyLoader(settings)
        self.loader.set_connection(connection_manager.get_connection())
        
        self.silver_processor = PropertySilverProcessor(settings)
        self.silver_processor.set_connection(connection_manager.get_connection())
        
        self.gold_processor = PropertyGoldProcessor(settings)
        self.gold_processor.set_connection(connection_manager.get_connection())
    
    @property
    def entity_type(self) -> EntityType:
        """Return the entity type."""
        return EntityType.PROPERTY
    
    def load_bronze(self, sample_size: Optional[int] = None) -> ProcessedTable:
        """Load property data into Bronze tier.
        
        Args:
            sample_size: Optional number of records to load
            
        Returns:
            TableIdentifier for the created Bronze table
        """
        # Create table identifier
        timestamp = int(time.time())
        table_id = TableIdentifier(
            entity_type=EntityType.PROPERTY,
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
            self.logger.info("Sample property data:")
            for i, prop in enumerate(sample_data, 1):
                self.logger.info(
                    f"  {i}. {prop['listing_id']}: ${prop['listing_price']:,.0f} "
                    f"({prop['bedrooms']}bed/{prop['bathrooms']}bath in {prop['city']})"
                )
        
        # Return ProcessedTable
        return ProcessedTable(
            table_name=table_name,
            entity_type=EntityType.PROPERTY,
            tier=MedallionTier.BRONZE,
            record_count=record_count,
            timestamp=timestamp
        )
    
    def process_silver(self, bronze_table: ProcessedTable) -> ProcessedTable:
        """Process property Bronze data into Silver tier.
        
        Args:
            bronze_table: Identifier for Bronze table
            
        Returns:
            TableIdentifier for the created Silver table
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
            entity_type=EntityType.PROPERTY,
            tier=MedallionTier.SILVER,
            record_count=record_count,
            timestamp=timestamp
        )
    
    def process_gold(self, silver_table: ProcessedTable) -> ProcessedTable:
        """Process property Silver data into Gold tier.
        
        Args:
            silver_table: Identifier for Silver table
            
        Returns:
            TableIdentifier for the created Gold table
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
            entity_type=EntityType.PROPERTY,
            tier=MedallionTier.GOLD,
            record_count=record_count,
            timestamp=timestamp
        )
