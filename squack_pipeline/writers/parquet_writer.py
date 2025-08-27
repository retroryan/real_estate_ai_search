"""Parquet writer implementation using DuckDB for optimized output."""

from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import pyarrow.parquet as pq

from squack_pipeline.config.settings import PipelineSettings, ParquetConfig
from squack_pipeline.writers.base import BaseWriter, PartitionedWriter
from squack_pipeline.models.duckdb_models import TableIdentifier
from squack_pipeline.utils.logging import PipelineLogger, log_execution_time


class ParquetWriter(PartitionedWriter):
    """Writer for Parquet format with DuckDB optimizations."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize Parquet writer with configuration."""
        super().__init__(settings)
        self.parquet_config: ParquetConfig = settings.parquet
        self.schema_cache: Dict[str, Dict[str, str]] = {}
        
    @log_execution_time
    def write(self, table_name: str, output_path: Path) -> Path:
        """Write table data to Parquet file using DuckDB.
        
        Args:
            table_name: Name of the table to export
            output_path: Path where the Parquet file should be written
            
        Returns:
            Path to the written Parquet file
        """
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build DuckDB COPY statement with Parquet options
        copy_options = self._build_copy_options()
        
        # Validate table name for safety
        safe_table = TableIdentifier(name=table_name)
        
        # Execute COPY TO PARQUET with options
        query = f"""
        COPY (SELECT * FROM {safe_table.qualified_name})
        TO '{output_path}' 
        (FORMAT PARQUET{copy_options})
        """
        
        try:
            self.logger.info(f"Writing {table_name} to {output_path}")
            self.connection.execute(query)
            
            # Cache the schema for validation
            schema_query = f"DESCRIBE {safe_table.qualified_name}"
            schema_result = self.connection.execute(schema_query).fetchall()
            self.schema_cache[str(output_path)] = {
                row[0]: row[1] for row in schema_result
            }
            
            # Track written file
            self.written_files.append(output_path)
            
            # Log file size
            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            self.logger.success(
                f"Successfully wrote {output_path.name} ({file_size_mb:.2f} MB)"
            )
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to write Parquet file: {e}")
            raise
    
    def _build_copy_options(self) -> str:
        """Build COPY options string from Parquet configuration."""
        options = []
        
        # Compression settings
        if self.parquet_config.compression:
            options.append(f"COMPRESSION '{self.parquet_config.compression}'")
        
        # Row group size
        if self.parquet_config.row_group_size:
            options.append(f"ROW_GROUP_SIZE {self.parquet_config.row_group_size}")
        
        # Dictionary encoding (DuckDB uses ENABLE_DICTIONARY)
        if not self.parquet_config.use_dictionary:
            options.append("ENABLE_DICTIONARY FALSE")
        
        # Per thread output for parallel writing
        if self.parquet_config.per_thread_output:
            options.append("PER_THREAD_OUTPUT TRUE")
        
        # Build options string
        if options:
            return ", " + ", ".join(options)
        return ""
    
    @log_execution_time
    def write_partitioned(
        self, 
        table_name: str, 
        output_dir: Path,
        partition_columns: Optional[List[str]] = None
    ) -> List[Path]:
        """Write data with partitioning using DuckDB.
        
        Args:
            table_name: Name of the table to export
            output_dir: Directory where partitioned data should be written
            partition_columns: Columns to partition by
            
        Returns:
            List of paths to written partition files
        """
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        # Use default partition columns if not provided
        if partition_columns is None:
            partition_columns = self.get_partition_columns()
        
        if not partition_columns:
            # No partitioning, write single file
            output_path = output_dir / f"{table_name}.parquet"
            self.write(table_name, output_path)
            return [output_path]
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build partition clause
        partition_by = f"PARTITION_BY ({', '.join(partition_columns)})"
        
        # Build DuckDB COPY statement with partitioning
        copy_options = self._build_copy_options()
        
        query = f"""
        COPY (SELECT * FROM {table_name})
        TO '{output_dir}' 
        (FORMAT PARQUET{copy_options}, {partition_by})
        """
        
        try:
            self.logger.info(
                f"Writing partitioned {table_name} to {output_dir} "
                f"(partitions: {', '.join(partition_columns)})"
            )
            self.connection.execute(query)
            
            # Find all written partition files
            partition_files = list(output_dir.rglob("*.parquet"))
            self.written_files.extend(partition_files)
            
            self.logger.success(
                f"Wrote {len(partition_files)} partition files to {output_dir}"
            )
            
            return partition_files
            
        except Exception as e:
            self.logger.error(f"Failed to write partitioned Parquet: {e}")
            raise
    
    def validate_output(self, output_path: Path) -> bool:
        """Validate written Parquet file meets requirements.
        
        Args:
            output_path: Path to the Parquet file
            
        Returns:
            True if validation passes, False otherwise
        """
        if not output_path.exists():
            self.logger.error(f"Output file does not exist: {output_path}")
            return False
        
        try:
            # Read Parquet file metadata
            parquet_file = pq.ParquetFile(output_path)
            metadata = parquet_file.metadata
            
            # Validate basic properties
            if metadata.num_rows == 0:
                self.logger.warning(f"Parquet file is empty: {output_path}")
                return False
            
            # Check compression
            if self.parquet_config.compression:
                # Get compression from first row group
                if metadata.num_row_groups > 0:
                    row_group = metadata.row_group(0)
                    for i in range(row_group.num_columns):
                        column = row_group.column(i)
                        if column.compression.lower() != self.parquet_config.compression.lower():
                            self.logger.warning(
                                f"Unexpected compression: {column.compression} "
                                f"(expected: {self.parquet_config.compression})"
                            )
            
            # Validate schema if cached
            if str(output_path) in self.schema_cache:
                expected_schema = self.schema_cache[str(output_path)]
                parquet_schema = parquet_file.schema_arrow
                
                for field in parquet_schema:
                    if field.name not in expected_schema:
                        self.logger.warning(
                            f"Unexpected column in output: {field.name}"
                        )
            
            self.logger.debug(
                f"Validated Parquet file: {metadata.num_rows} rows, "
                f"{metadata.num_row_groups} row groups, "
                f"{metadata.num_columns} columns"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate Parquet file: {e}")
            return False
    
    def get_output_schema(self) -> Dict[str, str]:
        """Get the expected output schema for properties.
        
        Returns:
            Dictionary mapping column names to types
        """
        # Return the Gold tier schema for properties
        return {
            # Basic property fields
            "listing_id": "VARCHAR",
            "listing_price": "DOUBLE",
            "bedrooms": "INTEGER",
            "bathrooms": "DOUBLE",
            "square_feet": "INTEGER",
            "lot_size": "INTEGER",
            "year_built": "INTEGER",
            "property_type": "VARCHAR",
            
            # Address fields
            "street": "VARCHAR",
            "city": "VARCHAR",
            "state": "VARCHAR",
            "zipcode": "VARCHAR",
            "latitude": "DOUBLE",
            "longitude": "DOUBLE",
            
            # Enrichment fields
            "price_per_sqft": "DOUBLE",
            "price_per_bedroom": "DOUBLE",
            "property_age": "INTEGER",
            "is_luxury": "BOOLEAN",
            "size_category": "VARCHAR",
            "price_category": "VARCHAR",
            
            # Geographic enrichment
            "distance_to_downtown": "DOUBLE",
            "distance_to_coast": "DOUBLE",
            "region": "VARCHAR",
            "urban_accessibility": "DOUBLE",
            
            # Features and metadata
            "garage": "BOOLEAN",
            "pool": "BOOLEAN",
            "fireplace": "BOOLEAN",
            "basement": "BOOLEAN",
            "neighborhood_id": "VARCHAR",
            "listing_date": "DATE",
            "last_sale_date": "DATE",
            "last_sale_price": "DOUBLE",
            "description": "VARCHAR",
            
            # Timestamps
            "created_at": "TIMESTAMP",
            "updated_at": "TIMESTAMP"
        }
    
    def get_partition_columns(self) -> List[str]:
        """Get default columns to use for partitioning.
        
        Returns:
            List of column names for partitioning
        """
        # Default partitioning by city only (property_type may not exist in enriched data)
        return ["city"]
    
    def write_with_schema(
        self, 
        table_name: str, 
        output_path: Path,
        schema_path: Optional[Path] = None
    ) -> Path:
        """Write Parquet file and accompanying schema metadata.
        
        Args:
            table_name: Name of the table to export
            output_path: Path where the Parquet file should be written
            schema_path: Optional path for schema JSON file
            
        Returns:
            Path to the written Parquet file
        """
        # Write the Parquet file
        parquet_path = self.write(table_name, output_path)
        
        # Write schema metadata if requested
        if schema_path or self.settings.validate_output:
            if not schema_path:
                schema_path = output_path.with_suffix('.schema.json')
            
            schema = self.schema_cache.get(str(output_path), self.get_output_schema())
            
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
        
        return parquet_path
    
    def get_statistics(self, parquet_path: Path) -> Dict[str, Any]:
        """Get statistics about a written Parquet file.
        
        Args:
            parquet_path: Path to the Parquet file
            
        Returns:
            Dictionary with file statistics
        """
        if not parquet_path.exists():
            return {}
        
        try:
            parquet_file = pq.ParquetFile(parquet_path)
            metadata = parquet_file.metadata
            
            # Calculate compression ratio
            uncompressed_size = sum(
                metadata.row_group(i).total_byte_size 
                for i in range(metadata.num_row_groups)
            )
            compressed_size = parquet_path.stat().st_size
            compression_ratio = uncompressed_size / compressed_size if compressed_size > 0 else 1.0
            
            return {
                "file_path": str(parquet_path),
                "file_size_mb": compressed_size / (1024 * 1024),
                "num_rows": metadata.num_rows,
                "num_columns": metadata.num_columns,
                "num_row_groups": metadata.num_row_groups,
                "compression": self.parquet_config.compression,
                "compression_ratio": compression_ratio,
                "created_by": metadata.created_by or "SQUACK Pipeline"
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics for {parquet_path}: {e}")
            return {}