"""Parquet writer using DuckDB COPY command.

Following DuckDB best practices:
- Uses native COPY TO command
- No data movement through Python
- Direct table-to-file export
- Supports partitioning
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
from datetime import datetime
from squack_pipeline_v2.core.connection import DuckDBConnectionManager as ConnectionManager
from squack_pipeline_v2.core.logging import log_stage

logger = logging.getLogger(__name__)


class ParquetWriter:
    """Write DuckDB tables to Parquet files using COPY command.
    
    This is the most efficient way to export data from DuckDB.
    No data passes through Python - direct table to file.
    """
    
    def __init__(self, connection_manager: ConnectionManager, output_dir: Path):
        """Initialize writer.
        
        Args:
            connection_manager: DuckDB connection manager
            output_dir: Directory for output files
        """
        self.connection_manager = connection_manager
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.files_written = []
    
    @log_stage("Parquet: Write table")
    def write_table(
        self,
        table_name: str,
        output_name: Optional[str] = None,
        partition_by: Optional[List[str]] = None,
        compression: str = "snappy"
    ) -> Dict[str, Any]:
        """Write a DuckDB table to Parquet file(s).
        
        Args:
            table_name: Source table name
            output_name: Output file name (without extension)
            partition_by: Columns to partition by
            compression: Compression codec (snappy, gzip, zstd)
            
        Returns:
            Write statistics
        """
        if not output_name:
            output_name = table_name
        
        # Check table exists
        if not self.connection_manager.table_exists(table_name):
            raise ValueError(f"Table {table_name} does not exist")
        
        # Get record count
        count_query = f"SELECT COUNT(*) FROM {table_name}"
        record_count = self.connection_manager.execute(count_query).fetchone()[0]
        
        logger.info(f"Writing {record_count} records from {table_name} to Parquet")
        
        start_time = datetime.now()
        
        if partition_by:
            # Partitioned write
            output_path = self.output_dir / output_name
            output_path.mkdir(parents=True, exist_ok=True)
            
            copy_query = f"""
            COPY (SELECT * FROM {table_name})
            TO '{output_path}'
            (FORMAT PARQUET, 
             COMPRESSION '{compression}',
             PARTITION_BY ({','.join(partition_by)}))
            """
        else:
            # Single file write
            output_file = self.output_dir / f"{output_name}.parquet"
            # Ensure parent directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            copy_query = f"""
            COPY (SELECT * FROM {table_name})
            TO '{output_file}'
            (FORMAT PARQUET, COMPRESSION '{compression}')
            """
        
        # Execute COPY command
        self.connection_manager.execute(copy_query)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Track written files
        if partition_by:
            # List partition files
            partition_files = list((self.output_dir / output_name).glob("**/*.parquet"))
            self.files_written.extend(str(f) for f in partition_files)
            file_count = len(partition_files)
            total_size = sum(f.stat().st_size for f in partition_files)
        else:
            output_file = self.output_dir / f"{output_name}.parquet"
            self.files_written.append(str(output_file))
            file_count = 1
            total_size = output_file.stat().st_size
        
        stats = {
            "table": table_name,
            "records": record_count,
            "files": file_count,
            "size_bytes": total_size,
            "size_mb": round(total_size / (1024 * 1024), 2),
            "duration_seconds": round(duration, 2),
            "records_per_second": round(record_count / duration) if duration > 0 else 0,
            "compression": compression,
            "partitioned": partition_by is not None
        }
        
        logger.info(f"Wrote {record_count} records to {file_count} file(s), {stats['size_mb']} MB")
        
        return stats
    
    @log_stage("Parquet: Write with join")
    def write_joined_table(
        self,
        query: str,
        output_name: str,
        compression: str = "snappy"
    ) -> Dict[str, Any]:
        """Write results of a join query to Parquet.
        
        Args:
            query: SQL query to execute
            output_name: Output file name
            compression: Compression codec
            
        Returns:
            Write statistics
        """
        output_file = self.output_dir / f"{output_name}.parquet"
        
        logger.info(f"Writing query results to {output_file}")
        
        start_time = datetime.now()
        
        # Use COPY with query
        copy_query = f"""
        COPY ({query})
        TO '{output_file}'
        (FORMAT PARQUET, COMPRESSION '{compression}')
        """
        
        self.connection_manager.execute(copy_query)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Get file stats
        file_size = output_file.stat().st_size
        self.files_written.append(str(output_file))
        
        # Get record count from file
        count_query = f"SELECT COUNT(*) FROM read_parquet('{output_file}')"
        record_count = self.connection_manager.execute(count_query).fetchone()[0]
        
        stats = {
            "output": output_name,
            "records": record_count,
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "duration_seconds": round(duration, 2),
            "compression": compression
        }
        
        logger.info(f"Wrote {record_count} records, {stats['size_mb']} MB")
        
        return stats
    
    @log_stage("Parquet: Export all layers")
    def export_all_layers(self) -> Dict[str, Any]:
        """Export all pipeline layers to Parquet.
        
        Returns:
            Export statistics
        """
        all_stats = {
            "bronze": {},
            "silver": {},
            "gold": {},
            "embeddings": {}
        }
        
        # Define export configuration
        exports = [
            # Bronze layer
            ("bronze_properties", "bronze/properties", "bronze"),
            ("bronze_neighborhoods", "bronze/neighborhoods", "bronze"),
            ("bronze_wikipedia", "bronze/wikipedia", "bronze"),
            
            # Silver layer
            ("silver_properties", "silver/properties", "silver"),
            ("silver_neighborhoods", "silver/neighborhoods", "silver"),
            ("silver_wikipedia", "silver/wikipedia", "silver"),
            
            # Gold layer
            ("gold_properties", "gold/properties", "gold"),
            ("gold_neighborhoods", "gold/neighborhoods", "gold"),
            ("gold_wikipedia", "gold/wikipedia", "gold"),
            
            # Embeddings
            ("embeddings_properties", "embeddings/properties", "embeddings"),
            ("embeddings_neighborhoods", "embeddings/neighborhoods", "embeddings"),
            ("embeddings_wikipedia", "embeddings/wikipedia", "embeddings")
        ]
        
        total_records = 0
        total_size = 0
        
        for table_name, output_path, layer in exports:
            if self.connection_manager.table_exists(table_name):
                try:
                    stats = self.write_table(table_name, output_path)
                    all_stats[layer][table_name] = stats
                    total_records += stats["records"]
                    total_size += stats["size_bytes"]
                except Exception as e:
                    logger.error(f"Failed to export {table_name}: {e}")
                    all_stats[layer][table_name] = {"error": str(e)}
            else:
                logger.debug(f"Skipping {table_name}: table does not exist")
        
        return {
            "layers": all_stats,
            "total_files": len(self.files_written),
            "total_records": total_records,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
    
    @log_stage("Parquet: Create denormalized export")
    def export_denormalized_properties(self) -> Dict[str, Any]:
        """Export denormalized property data with neighborhood info.
        
        This creates a single Parquet file with all property information
        joined with neighborhood data for easy analysis.
        
        Returns:
            Export statistics
        """
        # Check if required tables exist
        if not self.connection_manager.table_exists("gold_properties"):
            logger.warning("gold_properties table not found")
            return {"error": "gold_properties not found"}
        
        # Build denormalized query
        if self.connection_manager.table_exists("gold_neighborhoods"):
            query = """
            SELECT 
                p.*,
                n.name as neighborhood_name,
                n.city as neighborhood_city,
                n.population as neighborhood_population,
                n.median_income as neighborhood_median_income,
                n.walkability_score as neighborhood_walkability_score,
                n.school_rating as neighborhood_school_score,
                n.walkability_score as neighborhood_livability_score
            FROM gold_properties p
            LEFT JOIN gold_neighborhoods n
                ON p.neighborhood_id = n.neighborhood_id
            """
        else:
            query = "SELECT * FROM gold_properties"
        
        # Add embeddings if available
        if self.connection_manager.table_exists("embeddings_properties"):
            query = f"""
            WITH base AS ({query})
            SELECT 
                b.*,
                e.embedding,
                e.model_name as embedding_model,
                e.dimension as embedding_dimension
            FROM base b
            LEFT JOIN embeddings_properties e
                ON b.listing_id = e.listing_id
            """
        
        # Ensure denormalized directory exists
        denorm_dir = self.output_dir / "denormalized"
        denorm_dir.mkdir(parents=True, exist_ok=True)
        
        return self.write_joined_table(
            query=query,
            output_name="denormalized/properties_enriched",
            compression="snappy"
        )
    
    def verify_exports(self) -> Dict[str, Any]:
        """Verify all exported Parquet files.
        
        Returns:
            Verification results
        """
        results = {}
        
        for file_path in self.files_written:
            try:
                # Read back and check
                query = f"SELECT COUNT(*) as count FROM read_parquet('{file_path}')"
                count = self.connection_manager.execute(query).fetchone()[0]
                
                # Get schema
                schema_query = f"DESCRIBE SELECT * FROM read_parquet('{file_path}')"
                schema = self.connection_manager.execute(schema_query).fetchall()
                
                results[file_path] = {
                    "valid": True,
                    "records": count,
                    "columns": len(schema)
                }
            except Exception as e:
                results[file_path] = {
                    "valid": False,
                    "error": str(e)
                }
        
        return results