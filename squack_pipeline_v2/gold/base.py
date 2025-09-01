"""Base interface for Gold layer enrichment using DuckDB Relation API."""

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
        """Apply enrichment transformations using DuckDB Relation API.
        
        Args:
            input_table: Name of input table
            output_table: Name of output table
        """
        # Default implementation using Relation API - override in subclasses
        conn = self.connection_manager.get_connection()
        relation = conn.table(input_table)
        relation.create(output_table)
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
        
        Note: DuckDB ALTER TABLE ADD COLUMN AS is not fully supported for computed columns,
        so we recreate the table with the new computed field.
        
        Args:
            table_name: Table to update
            field_name: Name of the new field
            expression: SQL expression for computing the field
        """
        conn = self.connection_manager.get_connection()
        
        # Create new table with computed field using Relation API
        temp_table = f"{table_name}_with_{field_name}"
        enriched_relation = conn.sql(f"""
            SELECT *, ({expression}) AS {field_name}
            FROM {table_name}
        """)
        
        # Create new table
        enriched_relation.create(temp_table)
        
        # Replace original table
        self.connection_manager.drop_table(table_name)
        self.connection_manager.execute(f"ALTER TABLE {temp_table} RENAME TO {table_name}")
        
        self.enrichments_applied.append(f"computed_field:{field_name}")
    
    def join_dimension(self, base_table: str, dimension_table: str, 
                      join_key: str, fields: list[str], prefix: str = "") -> None:
        """Join a dimension table to enrich the base table using Relation API.
        
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
        
        conn = self.connection_manager.get_connection()
        
        # Build field list with optional prefix
        field_list = []
        for field in fields:
            alias = f"{prefix}{field}" if prefix else field
            field_list.append(f"d.{field} AS {alias}")
        
        fields_str = ", ".join(field_list)
        
        # Create enriched table with join using Relation API
        temp_table = f"{base_table}_enriched"
        enriched_relation = conn.sql(f"""
            SELECT b.*, {fields_str}
            FROM {base_table} b
            LEFT JOIN {dimension_table} d ON b.{join_key} = d.{join_key}
        """)
        
        # Create new table
        enriched_relation.create(temp_table)
        
        # Replace original table
        self.connection_manager.drop_table(base_table)
        self.connection_manager.execute(f"ALTER TABLE {temp_table} RENAME TO {base_table}")
        
        self.enrichments_applied.append(f"dimension_join:{dimension_table}")
    
    def create_embedding_text(self, table_name: str, text_field: str, 
                            source_fields: list[str], separator: str = " | ") -> None:
        """Create a text field for embedding generation using Relation API.
        
        Args:
            table_name: Table to update
            text_field: Name of the text field to create
            source_fields: Fields to combine for text
            separator: Separator between fields
        """
        conn = self.connection_manager.get_connection()
        
        # Build concatenation expression
        concat_parts = [f"COALESCE(CAST({field} AS VARCHAR), '')" for field in source_fields]
        concat_expr = f" || '{separator}' || ".join(concat_parts)
        
        # Create new table with embedding text field using Relation API
        temp_table = f"{table_name}_with_embedding"
        enriched_relation = conn.sql(f"""
            SELECT *, ({concat_expr}) AS {text_field}
            FROM {table_name}
        """)
        
        # Create new table
        enriched_relation.create(temp_table)
        
        # Replace original table
        self.connection_manager.drop_table(table_name)
        self.connection_manager.execute(f"ALTER TABLE {temp_table} RENAME TO {table_name}")
        
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