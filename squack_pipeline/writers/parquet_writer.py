"""Parquet writer implementation using DuckDB for optimized output."""

from pathlib import Path
from typing import Dict, List, Optional
import json
import time
import pyarrow.parquet as pq

from squack_pipeline.config.settings import PipelineSettings, ParquetConfig
from squack_pipeline.writers.base import BaseWriter
from squack_pipeline.models import EntityType
from squack_pipeline.models.duckdb_models import TableIdentifier
from squack_pipeline.models.writer_interface import (
    WriteRequest,
    WriteResponse,
    WriteMetrics,
    ValidationResult
)
from squack_pipeline.utils.logging import PipelineLogger, log_execution_time


class ParquetWriter(BaseWriter):
    """Writer for Parquet format with DuckDB optimizations."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize Parquet writer with configuration."""
        super().__init__(settings)
        self.parquet_config: ParquetConfig = settings.parquet
        self.written_files: Dict[str, Path] = {}  # Track written files by destination
        
    @log_execution_time
    def write(self, request: WriteRequest) -> WriteResponse:
        """Write table data to Parquet file using DuckDB.
        
        Args:
            request: Write request with table name and options
            
        Returns:
            WriteResponse with operation status and metrics
        """
        start_time = time.time()
        
        # Validate connection
        if not self.connection:
            return WriteResponse(
                success=False,
                entity_type=request.entity_type,
                destination="",
                metrics=WriteMetrics(
                    records_written=0,
                    records_failed=request.record_count,
                    duration_seconds=0
                ),
                error="No DuckDB connection available"
            )
        
        # Determine output path
        output_path = request.destination_path
        if not output_path:
            timestamp = int(time.time())
            filename = f"{request.entity_type.value}_{timestamp}.parquet"
            output_path = self.settings.data.output_path / filename
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build DuckDB COPY statement with Parquet options
        copy_options = self._build_copy_options()
        
        # Validate table name for safety
        safe_table = TableIdentifier(name=request.table_name)
        
        # Execute COPY TO PARQUET with options
        query = f"""
        COPY (SELECT * FROM {safe_table.qualified_name})
        TO '{output_path}' 
        (FORMAT PARQUET{copy_options})
        """
        
        try:
            self.logger.info(f"Writing {request.table_name} to {output_path}")
            self.connection.execute(query)
            
            # Track written file
            self.written_files[str(output_path)] = output_path
            
            # Get actual record count
            count_query = f"SELECT COUNT(*) FROM {safe_table.qualified_name}"
            actual_count = self.connection.execute(count_query).fetchone()[0]
            
            # Get file size
            file_size = output_path.stat().st_size
            duration = time.time() - start_time
            
            # Log success
            file_size_mb = file_size / (1024 * 1024)
            self.logger.success(
                f"Successfully wrote {output_path.name} ({file_size_mb:.2f} MB)"
            )
            
            return WriteResponse(
                success=True,
                entity_type=request.entity_type,
                destination=str(output_path),
                metrics=WriteMetrics(
                    records_written=actual_count,
                    records_failed=0,
                    bytes_written=file_size,
                    duration_seconds=duration
                )
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Failed to write Parquet file: {e}")
            
            return WriteResponse(
                success=False,
                entity_type=request.entity_type,
                destination=str(output_path),
                metrics=WriteMetrics(
                    records_written=0,
                    records_failed=request.record_count,
                    duration_seconds=duration
                ),
                error=str(e)
            )
    
    def validate(self, entity_type: EntityType, destination: str) -> ValidationResult:
        """Validate written Parquet file meets requirements.
        
        Args:
            entity_type: Type of entity that was written
            destination: Path to the Parquet file
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult(is_valid=True)
        output_path = Path(destination)
        
        # Check file exists
        if not output_path.exists():
            result.add_error(f"Output file does not exist: {output_path}")
            return result
        
        try:
            # Read Parquet file metadata
            parquet_file = pq.ParquetFile(output_path)
            metadata = parquet_file.metadata
            
            # Validate basic properties
            if metadata.num_rows == 0:
                result.add_warning(f"Parquet file is empty: {output_path}")
            
            # Check compression
            if self.parquet_config.compression:
                # Get compression from first row group
                if metadata.num_row_groups > 0:
                    row_group = metadata.row_group(0)
                    for i in range(row_group.num_columns):
                        column = row_group.column(i)
                        if column.compression.lower() != self.parquet_config.compression.lower():
                            result.add_warning(
                                f"Unexpected compression: {column.compression} "
                                f"(expected: {self.parquet_config.compression})"
                            )
                            break
            
            # Add metadata to result
            result.metadata = {
                "num_rows": metadata.num_rows,
                "num_columns": metadata.num_columns,
                "num_row_groups": metadata.num_row_groups,
                "format_version": metadata.format_version,
                "created_by": metadata.created_by or "Unknown"
            }
            
            self.logger.debug(
                f"Validated Parquet file: {metadata.num_rows} rows, "
                f"{metadata.num_row_groups} row groups, "
                f"{metadata.num_columns} columns"
            )
            
        except Exception as e:
            result.add_error(f"Failed to validate Parquet file: {e}")
        
        return result
    
    def get_metrics(self, entity_type: EntityType, destination: str) -> WriteMetrics:
        """Get metrics for written Parquet file.
        
        Args:
            entity_type: Type of entity
            destination: Path to the Parquet file
            
        Returns:
            WriteMetrics with file statistics
        """
        output_path = Path(destination)
        
        if not output_path.exists():
            return WriteMetrics(
                records_written=0,
                records_failed=0,
                bytes_written=0,
                duration_seconds=0
            )
        
        try:
            # Get file statistics
            parquet_file = pq.ParquetFile(output_path)
            metadata = parquet_file.metadata
            file_size = output_path.stat().st_size
            
            return WriteMetrics(
                records_written=metadata.num_rows,
                records_failed=0,
                bytes_written=file_size,
                duration_seconds=0  # Duration not available from file
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get metrics for {output_path}: {e}")
            return WriteMetrics(
                records_written=0,
                records_failed=0,
                bytes_written=0,
                duration_seconds=0
            )
    
    def _build_copy_options(self) -> str:
        """Build COPY options string from Parquet configuration."""
        options = []
        
        # Compression settings
        if self.parquet_config.compression:
            options.append(f"COMPRESSION '{self.parquet_config.compression}'")
        
        # Row group size
        if self.parquet_config.row_group_size:
            options.append(f"ROW_GROUP_SIZE {self.parquet_config.row_group_size}")
        
        # Dictionary encoding
        if not self.parquet_config.use_dictionary:
            options.append("ENABLE_DICTIONARY FALSE")
        
        # Per thread output for parallel writing
        if self.parquet_config.per_thread_output:
            options.append("PER_THREAD_OUTPUT TRUE")
        
        # Build options string
        if options:
            return ", " + ", ".join(options)
        return ""
    
    def write_with_schema(
        self, 
        table_name: str, 
        output_path: Path,
        schema_path: Optional[Path] = None
    ) -> Path:
        """Legacy method for backward compatibility.
        
        Args:
            table_name: Name of the table to export
            output_path: Path where the Parquet file should be written
            schema_path: Optional path for schema JSON file
            
        Returns:
            Path to the written Parquet file
        """
        # Create request for new interface
        request = WriteRequest(
            entity_type=EntityType.PROPERTY,  # Default to property for legacy calls
            table_name=table_name,
            record_count=0,  # Will be determined from table
            destination_path=output_path
        )
        
        # Write using new interface
        response = self.write(request)
        
        if not response.success:
            raise RuntimeError(f"Failed to write Parquet: {response.error}")
        
        # Write schema metadata if requested
        if schema_path or self.settings.validate_output:
            if not schema_path:
                schema_path = output_path.with_suffix('.schema.json')
            
            # Get schema from DuckDB
            safe_table = TableIdentifier(name=table_name)
            schema_query = f"DESCRIBE {safe_table.qualified_name}"
            schema_result = self.connection.execute(schema_query).fetchall()
            schema = {row[0]: row[1] for row in schema_result}
            
            with open(schema_path, 'w') as f:
                json.dump({
                    "table_name": table_name,
                    "parquet_file": str(output_path.name),
                    "schema": schema,
                    "row_group_size": self.parquet_config.row_group_size,
                    "compression": self.parquet_config.compression,
                    "metadata_version": self.settings.metadata_version
                }, f, indent=2)
            
            self.logger.info(f"Wrote schema metadata to {schema_path}")
        
        return output_path