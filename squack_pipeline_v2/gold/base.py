"""Base interface for Gold layer enrichment."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import PipelineLogger, log_execution_time
from squack_pipeline_v2.core.settings import PipelineSettings


class GoldMetadata(BaseModel):
    """Metadata for Gold layer processing."""
    
    model_config = ConfigDict(frozen=True)
    
    input_table: str = Field(description="Name of the Silver input table")
    output_table: str = Field(description="Name of the Gold output table")
    input_count: int = Field(ge=0, description="Number of input records")
    output_count: int = Field(ge=0, description="Number of output records")
    enrichments_applied: list[str] = Field(default_factory=list, description="List of enrichments applied")
    entity_type: str = Field(description="Type of entity")


class GoldEnricher:
    """Base class for Gold layer data enrichment."""
    
    def __init__(self, settings: PipelineSettings, connection_manager: DuckDBConnectionManager):
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
        """Enrich Silver data to Gold standard.
        
        Args:
            input_table: Name of Silver input table
            output_table: Name for Gold output table
            
        Returns:
            Metadata about the enrichment
        """
        # Reset enrichments list
        self.enrichments_applied = []
        
        # Validate input
        if not self.connection_manager.table_exists(input_table):
            raise ValueError(f"Input table {input_table} does not exist")
        
        input_count = self.connection_manager.count_records(input_table)
        
        # Drop output table if exists
        self.connection_manager.drop_table(output_table)
        
        # Apply enrichments
        self._apply_enrichments(input_table, output_table)
        
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
            f"Enriched {input_count} records -> {output_count} records "
            f"with {len(self.enrichments_applied)} enrichments"
        )
        
        return metadata
    
    def _apply_enrichments(self, input_table: str, output_table: str) -> None:
        """Apply enrichment transformations.
        
        Args:
            input_table: Name of input table
            output_table: Name of output table
        """
        # Default implementation - override in subclasses
        # This is a simple passthrough
        query = f"CREATE TABLE {output_table} AS SELECT * FROM {input_table}"
        self.connection_manager.execute(query)
        self.enrichments_applied.append("passthrough")
    
    def _get_entity_type(self) -> str:
        """Get the entity type for this enricher.
        
        Returns:
            Entity type string
        """
        # Default implementation - override in subclasses
        return "unknown"
    
    def add_computed_field(self, table_name: str, field_name: str, expression: str) -> None:
        """Add a computed field to the table.
        
        Args:
            table_name: Table to update
            field_name: Name of the new field
            expression: SQL expression for computing the field
        """
        query = f"ALTER TABLE {table_name} ADD COLUMN {field_name} AS ({expression})"
        self.connection_manager.execute(query)
        self.enrichments_applied.append(f"computed_field:{field_name}")
    
    def join_dimension(self, base_table: str, dimension_table: str, 
                      join_key: str, fields: list[str], prefix: str = "") -> None:
        """Join a dimension table to enrich the base table.
        
        Args:
            base_table: Base table to enrich
            dimension_table: Dimension table to join
            join_key: Column to join on
            fields: Fields to add from dimension table
            prefix: Optional prefix for new field names
        """
        if not self.connection_manager.table_exists(dimension_table):
            self.logger.warning(f"Dimension table {dimension_table} not found, skipping join")
            return
        
        # Build field list with optional prefix
        field_list = []
        for field in fields:
            alias = f"{prefix}{field}" if prefix else field
            field_list.append(f"d.{field} AS {alias}")
        
        fields_str = ", ".join(field_list)
        
        # Create enriched table with join
        temp_table = f"{base_table}_enriched"
        query = f"""
        CREATE TABLE {temp_table} AS
        SELECT b.*, {fields_str}
        FROM {base_table} b
        LEFT JOIN {dimension_table} d ON b.{join_key} = d.{join_key}
        """
        
        self.connection_manager.execute(query)
        
        # Replace original table
        self.connection_manager.drop_table(base_table)
        self.connection_manager.execute(f"ALTER TABLE {temp_table} RENAME TO {base_table}")
        
        self.enrichments_applied.append(f"dimension_join:{dimension_table}")
    
    def create_embedding_text(self, table_name: str, text_field: str, 
                            source_fields: list[str], separator: str = " | ") -> None:
        """Create a text field for embedding generation.
        
        Args:
            table_name: Table to update
            text_field: Name of the text field to create
            source_fields: Fields to combine for text
            separator: Separator between fields
        """
        # Build concatenation expression
        concat_parts = [f"COALESCE(CAST({field} AS VARCHAR), '')" for field in source_fields]
        concat_expr = f" || '{separator}' || ".join(concat_parts)
        
        query = f"ALTER TABLE {table_name} ADD COLUMN {text_field} VARCHAR AS ({concat_expr})"
        self.connection_manager.execute(query)
        
        self.enrichments_applied.append(f"embedding_text:{text_field}")
    
    def validate(self, table_name: str) -> bool:
        """Validate the enriched data.
        
        Args:
            table_name: Name of table to validate
            
        Returns:
            True if validation passes
        """
        # Check table exists
        if not self.connection_manager.table_exists(table_name):
            self.logger.error(f"Table {table_name} does not exist")
            return False
        
        # Check has records
        count = self.connection_manager.count_records(table_name)
        if count == 0:
            self.logger.error(f"Table {table_name} has no records after enrichment")
            return False
        
        # Check enrichments were applied
        if not self.enrichments_applied:
            self.logger.warning(f"No enrichments applied to {table_name}")
        
        self.logger.info(
            f"Validation passed for {table_name}: {count} records, "
            f"{len(self.enrichments_applied)} enrichments"
        )
        return True