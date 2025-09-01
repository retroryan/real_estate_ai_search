"""Base interface for Gold layer enrichment using DuckDB views."""

from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
import duckdb

from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import PipelineLogger, log_execution_time
from squack_pipeline_v2.core.settings import PipelineSettings


class GoldMetadata(BaseModel):
    """Metadata for Gold layer processing."""
    
    model_config = ConfigDict(frozen=True)
    
    input_table: str = Field(description="Name of the Silver input table")
    output_table: str = Field(description="Name of the Gold output view")
    input_count: int = Field(ge=0, description="Number of input records")
    output_count: int = Field(ge=0, description="Number of output records") 
    enrichments_applied: list[str] = Field(default_factory=list, description="List of enrichments applied")
    entity_type: str = Field(description="Type of entity")


class GoldEnricher(ABC):
    """Base class for Gold layer data enrichment using views."""
    
    def __init__(
        self, 
        settings: PipelineSettings, 
        connection_manager: DuckDBConnectionManager
    ):
        """Initialize the Gold enricher.
        
        Args:
            settings: Pipeline configuration settings
            connection_manager: DuckDB connection manager
        """
        self.settings = settings
        self.connection_manager = connection_manager
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        self.enrichments_applied = []
    
    @log_execution_time
    def enrich(self, input_table: str, output_table: str) -> GoldMetadata:
        """Create Gold view with enrichments.
        
        Args:
            input_table: Name of Silver input table
            output_table: Name for Gold output view (creates a view, not a table)
            
        Returns:
            Metadata about the enrichment
        """
        # Reset enrichments list
        self.enrichments_applied = []
        
        # Validate input
        if not self.connection_manager.table_exists(input_table):
            raise ValueError(f"Input table {input_table} does not exist")
        
        input_count = self.connection_manager.count_records(input_table)
        
        # Drop existing view if exists
        self.connection_manager.drop_view(output_table)
        
        # Create enriched view
        self._create_enriched_view(input_table, output_table)
        
        # Get output count
        output_count = self.connection_manager.count_records(output_table)
        
        # Create metadata
        metadata = GoldMetadata(
            input_table=input_table,
            output_table=output_table,
            input_count=input_count,
            output_count=output_count,
            enrichments_applied=self.enrichments_applied.copy(),
            entity_type=self._get_entity_type()
        )
        
        self.logger.info(
            f"Created Gold view with {input_count} -> {output_count} records "
            f"and {len(self.enrichments_applied)} enrichments"
        )
        
        return metadata
    
    @abstractmethod
    def _create_enriched_view(self, input_table: str, output_table: str) -> None:
        """Create enriched Gold view.
        
        Args:
            input_table: Name of input table
            output_table: Name of output view (creates a view, not a table)
        """
        pass
    
    @abstractmethod
    def _get_entity_type(self) -> str:
        """Get the entity type for this enricher.
        
        Returns:
            Entity type string
        """
        pass
    
    # Views are immutable - removed table manipulation methods
    
    def validate(self, view_name: str) -> bool:
        """Validate the enriched view.
        
        Args:
            view_name: Name of view to validate
            
        Returns:
            True if validation passes
        """
        conn = self.connection_manager.get_connection()
        
        # Check view exists using parameterized query
        result = conn.execute(
            "SELECT COUNT(*) FROM information_schema.views WHERE table_schema = ? AND view_name = ?",
            ["main", view_name]
        ).fetchone()
        
        if result[0] == 0:
            self.logger.error(f"View {view_name} does not exist")
            return False
        
        # Check has records
        count = self.connection_manager.count_records(view_name)
        if count == 0:
            self.logger.warning(f"View {view_name} has no records")
            return True  # Zero records might be valid
        
        self.logger.info(
            f"Validation passed for {view_name}: {count} records, "
            f"{len(self.enrichments_applied)} enrichments"
        )
        return True