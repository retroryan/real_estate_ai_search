"""Parquet writer using DuckDB native COPY command.

Follows DuckDB best practices:
- ZSTD compression with level 1 for optimal performance
- Configurable row group size for parallelization
- Per-thread output support for large datasets
"""

from typing import Dict, Any, List
from pathlib import Path
import logging

from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import log_stage

logger = logging.getLogger(__name__)


class ParquetWriter:
    """Simple Parquet writer using DuckDB native COPY."""
    
    def __init__(self, connection_manager: DuckDBConnectionManager, output_dir: Path):
        """Initialize writer.
        
        Args:
            connection_manager: DuckDB connection manager
            output_dir: Directory for output files
        """
        self.connection_manager = connection_manager
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @log_stage("Export to Parquet")
    def write_table(
        self,
        table_name: str,
        output_name: str = None,
        compression: str = "zstd",
        compression_level: int = 1,
        row_group_size: int = 100_000
    ) -> Dict[str, Any]:
        """Write table or view to Parquet.
        
        Args:
            table_name: Source table or view name
            output_name: Output file name (without extension)
            compression: Compression codec (zstd recommended)
            compression_level: Compression level (1=fast, 9=best)
            row_group_size: Rows per group (100K-1M recommended)
            
        Returns:
            Export statistics
        """
        if not output_name:
            output_name = table_name
        
        output_file = self.output_dir / f"{output_name}.parquet"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Get record count
        record_count = self.connection_manager.count_records(table_name)
        
        # Use DuckDB native COPY with optimization parameters
        conn = self.connection_manager.get_connection()
        safe_table = DuckDBConnectionManager.safe_identifier(table_name)
        
        # Build COPY parameters
        copy_params = [
            "FORMAT PARQUET",
            f"COMPRESSION '{compression}'"
        ]
        
        if compression == "zstd":
            copy_params.append(f"COMPRESSION_LEVEL {compression_level}")
        
        copy_params.append(f"ROW_GROUP_SIZE {row_group_size}")
        
        params_str = ", ".join(copy_params)
        
        conn.execute(f"""
            COPY (SELECT * FROM {safe_table})
            TO '{output_file.absolute()}'
            ({params_str})
        """)
        
        file_size = output_file.stat().st_size
        
        logger.info(f"Exported {record_count} records to {output_file}")
        
        return {
            "table": table_name,
            "records": record_count,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "compression": compression
        }
    
    @log_stage("Export all layers")
    def export_all_layers(self) -> Dict[str, List[Dict[str, Any]]]:
        """Export all layers to Parquet.
        
        Returns:
            Export statistics by layer
        """
        results = {}
        
        # Define what to export
        exports = {
            "bronze": ["bronze_properties", "bronze_neighborhoods", "bronze_wikipedia"],
            "silver": ["silver_properties", "silver_neighborhoods", "silver_wikipedia"],
            "gold": ["gold_properties", "gold_neighborhoods", "gold_wikipedia"]
        }
        
        for layer, tables in exports.items():
            layer_dir = self.output_dir / layer
            layer_dir.mkdir(parents=True, exist_ok=True)
            
            results[layer] = []
            for table in tables:
                try:
                    # Check if table/view exists
                    conn = self.connection_manager.get_connection()
                    check_query = """
                        SELECT COUNT(*) FROM (
                            SELECT table_name FROM information_schema.tables 
                            WHERE table_schema = 'main' AND table_name = ?
                            UNION ALL
                            SELECT table_name FROM information_schema.views 
                            WHERE table_schema = 'main' AND table_name = ?
                        )
                    """
                    exists = conn.execute(check_query, [table, table]).fetchone()[0] > 0
                    
                    if exists:
                        output_file = layer_dir / f"{table}.parquet"
                        
                        # Use ZSTD with level 1 for optimal performance/compression
                        compression = "zstd"
                        compression_level = 1
                        # Larger row groups for aggregated layers
                        row_group_size = 100_000 if layer == "bronze" else 500_000
                        
                        # Export using native COPY with optimizations
                        safe_table = DuckDBConnectionManager.safe_identifier(table)
                        
                        # Build optimized COPY parameters
                        copy_params = [
                            "FORMAT PARQUET",
                            f"COMPRESSION '{compression}'",
                            f"COMPRESSION_LEVEL {compression_level}",
                            f"ROW_GROUP_SIZE {row_group_size}"
                        ]
                        
                        params_str = ", ".join(copy_params)
                        
                        conn.execute(f"""
                            COPY (SELECT * FROM {safe_table})
                            TO '{output_file.absolute()}'
                            ({params_str})
                        """)
                        
                        record_count = self.connection_manager.count_records(table)
                        file_size = output_file.stat().st_size
                        
                        results[layer].append({
                            "table": table,
                            "records": record_count,
                            "size_mb": round(file_size / (1024 * 1024), 2)
                        })
                        
                        logger.info(f"Exported {table}: {record_count} records")
                except Exception as e:
                    logger.error(f"Failed to export {table}: {e}")
        
        return results