"""Parquet writer using DuckDB COPY command with medallion architecture support.

Following DuckDB and medallion architecture best practices:
- Uses native COPY TO command with advanced options
- No data movement through Python
- Direct table-to-file export
- Supports medallion layer-specific exports
- Provides business-ready analytical exports
- Leverages DuckDB's compression and optimization features
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
from datetime import datetime
from squack_pipeline_v2.core.connection import DuckDBConnectionManager as ConnectionManager
from squack_pipeline_v2.core.logging import log_stage

logger = logging.getLogger(__name__)


class ParquetWriter:
    """Enhanced Parquet writer with medallion architecture support.
    
    Key features:
    - Layer-specific exports (Bronze, Silver, Gold)
    - Business-ready analytical datasets
    - Optimized compression settings
    - Partitioning strategies
    - Data quality reports
    - Direct table-to-file export (no Python data movement)
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
        self.export_stats = {}
    
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
            "gold": {}
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
            
            # Gold layer (contains embeddings following medallion architecture)
            ("gold_properties", "gold/properties", "gold"),
            ("gold_neighborhoods", "gold/neighborhoods", "gold"),
            ("gold_wikipedia", "gold/wikipedia", "gold")
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
                n.school_score as neighborhood_school_score,
                n.walkability_score as neighborhood_livability_score
            FROM gold_properties p
            LEFT JOIN gold_neighborhoods n
                ON p.neighborhood_id = n.neighborhood_id
            """
        else:
            query = "SELECT * FROM gold_properties"
        
        # Embeddings are now included in Gold tables following medallion architecture
        # No separate embedding tables needed
        
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
    
    @log_stage("Parquet: Export medallion layer")
    def export_medallion_layer(
        self,
        layer: str,
        compression: str = "snappy",
        row_group_size: int = 122880
    ) -> Dict[str, Any]:
        """Export all tables from a medallion layer with optimal settings.
        
        Args:
            layer: Medallion layer (bronze, silver, gold)
            compression: Compression codec (snappy, zstd, gzip)
            row_group_size: Row group size for Parquet files
            
        Returns:
            Export statistics by table
        """
        layer = layer.lower()
        if layer not in ["bronze", "silver", "gold"]:
            raise ValueError(f"Invalid layer: {layer}")
        
        # Get all tables for this layer
        conn = self.connection_manager.get_connection()
        tables_query = f"""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'main' 
        AND table_name LIKE '{layer}_%'
        """
        
        tables = conn.sql(tables_query).fetchall()
        layer_stats = {}
        
        for (table_name,) in tables:
            # Create layer-specific directory
            layer_dir = self.output_dir / layer
            layer_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine optimal settings based on layer
            if layer == "bronze":
                # Bronze: Raw data, prioritize storage efficiency
                compression = "zstd"  # Better compression for raw data
            elif layer == "silver":
                # Silver: Clean data, balance compression and speed
                compression = "snappy"
            else:  # gold
                # Gold: Business-ready, optimize for query performance
                compression = "snappy"
                # Add statistics for better query performance
                self._optimize_gold_table(table_name)
            
            # Export with optimal settings
            output_file = layer_dir / f"{table_name}.parquet"
            
            copy_query = f"""
            COPY (SELECT * FROM {table_name})
            TO '{output_file}'
            (FORMAT PARQUET, 
             COMPRESSION '{compression}',
             ROW_GROUP_SIZE {row_group_size})
            """
            
            start_time = datetime.now()
            self.connection_manager.execute(copy_query)
            duration = (datetime.now() - start_time).total_seconds()
            
            # Get statistics
            count = self.connection_manager.count_records(table_name)
            file_size = output_file.stat().st_size
            
            layer_stats[table_name] = {
                "records": count,
                "file": str(output_file),
                "size_mb": round(file_size / (1024 * 1024), 2),
                "compression": compression,
                "duration_seconds": round(duration, 2)
            }
            
            self.files_written.append(str(output_file))
            logger.info(f"Exported {table_name}: {count} records, {layer_stats[table_name]['size_mb']} MB")
        
        return layer_stats
    
    def _optimize_gold_table(self, table_name: str):
        """Optimize Gold table for export with statistics.
        
        Args:
            table_name: Gold table to optimize
        """
        # Analyze table to update statistics for better Parquet optimization
        try:
            self.connection_manager.execute(f"ANALYZE {table_name}")
        except Exception as e:
            logger.debug(f"Could not analyze {table_name}: {e}")
    
    @log_stage("Parquet: Create business analytics dataset")
    def create_business_analytics_dataset(self) -> Dict[str, Any]:
        """Create comprehensive business analytics dataset from Gold layer.
        
        This creates optimized analytical datasets for business intelligence:
        - Property analytics with full enrichment
        - Market analysis by neighborhood
        - Investment opportunity matrix
        - Geographic intelligence
        
        Returns:
            Export statistics
        """
        analytics_dir = self.output_dir / "analytics"
        analytics_dir.mkdir(parents=True, exist_ok=True)
        
        datasets = {}
        
        # 1. Property Investment Analytics
        if self.connection_manager.table_exists("gold_properties"):
            property_analytics_query = """
            WITH property_metrics AS (
                SELECT 
                    p.*,
                    -- Investment metrics based on price premium
                    CASE 
                        WHEN p.price_premium_pct >= 20 THEN 'Premium'
                        WHEN p.price_premium_pct >= 0 THEN 'Market'
                        WHEN p.price_premium_pct >= -20 THEN 'Value'
                        ELSE 'Deep Value'
                    END as investment_grade,
                    
                    -- Market positioning
                    PERCENT_RANK() OVER (PARTITION BY property_type ORDER BY price) as price_percentile,
                    
                    -- Embedding insights (if available)
                    CASE 
                        WHEN embedding_vector IS NOT NULL THEN 'ML-Ready'
                        ELSE 'Pending'
                    END as ml_status,
                    
                    -- Market velocity based on days_on_market if available
                    CASE 
                        WHEN p.days_on_market <= 7 THEN 'Hot'
                        WHEN p.days_on_market <= 30 THEN 'Active'
                        WHEN p.days_on_market <= 90 THEN 'Moderate'
                        ELSE 'Stale'
                    END as market_velocity
                FROM gold_properties p
            )
            SELECT * FROM property_metrics
            """
            
            datasets["property_investment_analytics"] = self._export_analytics_dataset(
                query=property_analytics_query,
                output_name="analytics/property_investment",
                partition_by=["market_segment", "property_type"]
            )
        
        # 2. Neighborhood Market Intelligence
        if self.connection_manager.table_exists("gold_neighborhoods"):
            neighborhood_analytics_query = """
            WITH neighborhood_insights AS (
                SELECT 
                    n.*,
                    -- Market tier classification
                    CASE 
                        WHEN n.estimated_median_home_price > 2000000 THEN 'Luxury'
                        WHEN n.estimated_median_home_price > 1000000 THEN 'Premium'
                        WHEN n.estimated_median_home_price > 500000 THEN 'Mid-Market'
                        ELSE 'Entry-Level'
                    END as market_tier,
                    
                    -- Livability index
                    (n.walkability_score + n.school_score + n.overall_livability_score) / 3 as composite_livability,
                    
                    -- Income-based growth potential
                    CASE 
                        WHEN n.median_income > 150000 THEN 'High Income'
                        WHEN n.median_income > 100000 THEN 'Upper Middle'
                        WHEN n.median_income > 50000 THEN 'Middle Income'
                        ELSE 'Lower Income'
                    END as income_tier
                FROM gold_neighborhoods n
            )
            SELECT * FROM neighborhood_insights
            """
            
            datasets["neighborhood_market_intelligence"] = self._export_analytics_dataset(
                query=neighborhood_analytics_query,
                output_name="analytics/neighborhood_intelligence",
                partition_by=["city", "market_tier"]
            )
        
        # 3. Cross-Entity Analytics (Properties + Neighborhoods)
        if (self.connection_manager.table_exists("gold_properties") and 
            self.connection_manager.table_exists("gold_neighborhoods")):
            
            cross_analytics_query = """
            WITH market_analysis AS (
                SELECT 
                    p.listing_id,
                    p.price,
                    p.property_type,
                    p.market_segment,
                    p.price_premium_pct,
                    p.days_on_market,
                    
                    n.name as neighborhood,
                    n.city,
                    n.income_category as neighborhood_income_tier,
                    n.estimated_median_home_price as area_median_price,
                    n.overall_livability_score as neighborhood_score,
                    
                    -- Price analysis
                    p.price / NULLIF(n.estimated_median_home_price, 0) as price_to_area_ratio,
                    
                    -- Combined opportunity score based on price premium and livability
                    (p.price_premium_pct * -0.3 + n.overall_livability_score * 0.7) as combined_opportunity_score,
                    
                    -- Market alignment
                    CASE 
                        WHEN p.price < n.estimated_median_home_price * 0.8 THEN 'Below Market'
                        WHEN p.price > n.estimated_median_home_price * 1.2 THEN 'Above Market'
                        ELSE 'Market Price'
                    END as price_position
                    
                FROM gold_properties p
                LEFT JOIN gold_neighborhoods n 
                    ON p.neighborhood_id = n.neighborhood_id
            )
            SELECT * FROM market_analysis
            ORDER BY combined_opportunity_score DESC
            """
            
            datasets["cross_entity_analytics"] = self._export_analytics_dataset(
                query=cross_analytics_query,
                output_name="analytics/market_opportunities",
                compression="zstd"  # Better compression for large analytical dataset
            )
        
        # 4. Geographic Intelligence (if Wikipedia data available)
        if self.connection_manager.table_exists("gold_wikipedia"):
            geo_intelligence_query = """
            SELECT 
                w.page_id,
                w.title,
                w.article_quality,
                w.relevance_score,
                w.geographic_relevance_score,
                w.key_topics,
                w.location,
                
                -- Content classification
                CASE 
                    WHEN w.article_quality = 'premium' THEN 'High Value'
                    WHEN w.article_quality = 'high' THEN 'Valuable'
                    ELSE 'Standard'
                END as content_value,
                
                -- Embedding status
                CASE 
                    WHEN w.embedding_vector IS NOT NULL THEN 'Searchable'
                    ELSE 'Not Indexed'
                END as search_status
                
            FROM gold_wikipedia w
            WHERE w.geographic_relevance_score > 0.5
            """
            
            datasets["geographic_intelligence"] = self._export_analytics_dataset(
                query=geo_intelligence_query,
                output_name="analytics/geographic_intelligence"
            )
        
        return {
            "datasets_created": len(datasets),
            "total_size_mb": sum(d.get("size_mb", 0) for d in datasets.values()),
            "datasets": datasets
        }
    
    def _export_analytics_dataset(
        self,
        query: str,
        output_name: str,
        compression: str = "snappy",
        partition_by: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Export an analytics dataset with optimal settings.
        
        Args:
            query: SQL query for the dataset
            output_name: Output file/directory name
            compression: Compression codec
            partition_by: Optional partitioning columns
            
        Returns:
            Export statistics
        """
        start_time = datetime.now()
        
        if partition_by:
            # Partitioned export
            output_path = self.output_dir / output_name
            output_path.mkdir(parents=True, exist_ok=True)
            
            copy_query = f"""
            COPY ({query})
            TO '{output_path}'
            (FORMAT PARQUET,
             COMPRESSION '{compression}',
             PARTITION_BY ({','.join(partition_by)}),
             ROW_GROUP_SIZE 122880)
            """
        else:
            # Single file export
            output_file = self.output_dir / f"{output_name}.parquet"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            copy_query = f"""
            COPY ({query})
            TO '{output_file}'
            (FORMAT PARQUET,
             COMPRESSION '{compression}',
             ROW_GROUP_SIZE 122880)
            """
        
        # Execute export
        self.connection_manager.execute(copy_query)
        duration = (datetime.now() - start_time).total_seconds()
        
        # Calculate statistics
        if partition_by:
            files = list((self.output_dir / output_name).glob("**/*.parquet"))
            total_size = sum(f.stat().st_size for f in files)
            self.files_written.extend(str(f) for f in files)
        else:
            output_file = self.output_dir / f"{output_name}.parquet"
            total_size = output_file.stat().st_size
            self.files_written.append(str(output_file))
        
        return {
            "output": output_name,
            "size_mb": round(total_size / (1024 * 1024), 2),
            "compression": compression,
            "partitioned": partition_by is not None,
            "duration_seconds": round(duration, 2)
        }
    
    @log_stage("Parquet: Generate data quality report")
    def generate_quality_report(self) -> Dict[str, Any]:
        """Generate data quality report for exported files.
        
        Returns:
            Quality metrics for all exported files
        """
        conn = self.connection_manager.get_connection()
        quality_report = {}
        
        for file_path in self.files_written:
            try:
                # Read file metadata
                stats_query = f"""
                SELECT 
                    COUNT(*) as row_count,
                    COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM read_parquet('{file_path}')), 0) as completeness,
                    pg_size_pretty(pg_column_size('{file_path}')) as file_size
                FROM read_parquet('{file_path}')
                """
                
                # Get column statistics
                schema_query = f"""
                SELECT 
                    column_name,
                    data_type
                FROM (DESCRIBE SELECT * FROM read_parquet('{file_path}'))
                """
                
                schema = conn.sql(schema_query).fetchall()
                
                quality_report[Path(file_path).name] = {
                    "columns": len(schema),
                    "column_types": {col: dtype for col, dtype in schema},
                    "file_valid": True
                }
                
            except Exception as e:
                quality_report[Path(file_path).name] = {
                    "file_valid": False,
                    "error": str(e)
                }
        
        return quality_report