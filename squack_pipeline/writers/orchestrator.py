"""Writer orchestrator for managing multiple output destinations."""

import time
from typing import Dict, List, Optional, Any

import duckdb

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.writers.parquet_writer import ParquetWriter
from squack_pipeline.writers.elasticsearch import ElasticsearchWriter, EntityType, WriteResult
from squack_pipeline.models.duckdb_models import TableIdentifier
from squack_pipeline.utils.logging import PipelineLogger


class WriterOrchestrator:
    """Orchestrates writing data to multiple output destinations."""
    
    def __init__(self, settings: PipelineSettings):
        """
        Initialize the writer orchestrator.
        
        Args:
            settings: Pipeline settings with output configuration
        """
        self.settings = settings
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        
        # Initialize writers based on enabled destinations
        self.parquet_writer: Optional[ParquetWriter] = None
        self.es_writer: Optional[ElasticsearchWriter] = None
        
        self._initialize_writers()
    
    def _initialize_writers(self):
        """Initialize writers based on enabled destinations."""
        destinations = self.settings.output.enabled_destinations
        
        # Always initialize Parquet writer if enabled
        if "parquet" in destinations:
            self.parquet_writer = ParquetWriter(self.settings)
            self.logger.info("Initialized Parquet writer")
        
        # Initialize Elasticsearch writer if enabled
        if "elasticsearch" in destinations:
            if self.settings.output.elasticsearch:
                self.es_writer = ElasticsearchWriter(self.settings.output.elasticsearch)
                # Verify connection
                if self.es_writer.verify_connection():
                    self.logger.info("Initialized Elasticsearch writer")
                else:
                    self.logger.error("Failed to connect to Elasticsearch")
                    self.es_writer = None
            else:
                self.logger.error("Elasticsearch enabled but configuration missing")
    
    def write_all(
        self,
        connection: duckdb.DuckDBPyConnection,
        tables: Dict[str, str]
    ) -> Dict[str, List[Any]]:
        """
        Write all entities to all configured destinations.
        
        Args:
            connection: DuckDB connection
            tables: Mapping of entity types to table names
            
        Returns:
            Dictionary of results by destination
        """
        results = {}
        
        # Write to Parquet
        if self.parquet_writer and "parquet" in self.settings.output.enabled_destinations:
            self.logger.info("Writing to Parquet files...")
            parquet_results = self._write_parquet(connection, tables)
            results['parquet'] = parquet_results
        
        # Write to Elasticsearch
        if self.es_writer and "elasticsearch" in self.settings.output.enabled_destinations:
            self.logger.info("Writing to Elasticsearch...")
            es_results = self._write_elasticsearch(connection, tables)
            results['elasticsearch'] = es_results
        
        return results
    
    def _write_parquet(
        self,
        connection: duckdb.DuckDBPyConnection,
        tables: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Write entities to Parquet files using existing ParquetWriter.
        
        Args:
            connection: DuckDB connection
            tables: Mapping of entity types to table names
            
        Returns:
            List of write results
        """
        results = []
        
        if not self.parquet_writer:
            return results
        
        # Set connection for ParquetWriter
        self.parquet_writer.set_connection(connection)
        
        # Write each entity type
        for entity_type, table_name in tables.items():
            if not table_name:
                continue
            
            try:
                # Generate output filename
                timestamp = int(time.time())
                output_filename = f"{entity_type}_{self.settings.environment}_{timestamp}.parquet"
                output_path = self.settings.data.output_path / output_filename
                
                # Write using ParquetWriter's existing method
                written_path = self.parquet_writer.write_with_schema(
                    table_name,
                    output_path
                )
                
                # Get record count safely
                safe_table = TableIdentifier(name=table_name)
                record_count = connection.execute(
                    f"SELECT COUNT(*) FROM {safe_table.qualified_name}"
                ).fetchone()[0]
                
                results.append({
                    'entity_type': entity_type,
                    'path': str(written_path),
                    'record_count': record_count,
                    'success': True
                })
                
                self.logger.success(f"Wrote {record_count} {entity_type} records to {written_path}")
                
            except Exception as e:
                self.logger.error(f"Failed to write {entity_type} to Parquet: {str(e)}")
                results.append({
                    'entity_type': entity_type,
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def _write_elasticsearch(
        self,
        connection: duckdb.DuckDBPyConnection,
        tables: Dict[str, str]
    ) -> List[WriteResult]:
        """
        Extract data from DuckDB and write to Elasticsearch.
        
        Args:
            connection: DuckDB connection
            tables: Mapping of entity types to table names
            
        Returns:
            List of WriteResult objects
        """
        results = []
        
        if not self.es_writer:
            return results
        
        # Map string entity types to EntityType enum
        entity_mapping = {
            "properties": EntityType.PROPERTIES,
            "neighborhoods": EntityType.NEIGHBORHOODS,
            "wikipedia": EntityType.WIKIPEDIA,
            "locations": EntityType.NEIGHBORHOODS,  # Use neighborhoods type for locations
        }
        
        for entity_type_str, table_name in tables.items():
            if not table_name:
                continue
            
            # Get enum value
            entity_type = entity_mapping.get(entity_type_str)
            if not entity_type:
                self.logger.warning(f"Unknown entity type: {entity_type_str}")
                continue
            
            try:
                self.logger.info(f"Extracting {entity_type_str} from {table_name}...")
                
                # Extract data from DuckDB as DataFrame safely
                safe_table = TableIdentifier(name=table_name)
                df = connection.execute(f"SELECT * FROM {safe_table.qualified_name}").df()
                
                # Convert DataFrame to list of dictionaries
                data = df.to_dict('records')
                
                self.logger.info(f"Writing {len(data)} {entity_type_str} records to Elasticsearch...")
                
                # Write to Elasticsearch
                result = self.es_writer.write_entity(entity_type, data)
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Failed to write {entity_type_str} to Elasticsearch: {str(e)}")
                results.append(WriteResult(
                    success=False,
                    entity_type=entity_type,
                    record_count=0,
                    failed_count=0,
                    index_name=f"{self.es_writer.config.index_prefix}_{entity_type.value}",
                    error=str(e)
                ))
        
        return results
    
    def close(self):
        """Close all writer connections."""
        if self.es_writer:
            self.es_writer.close()
            self.logger.info("Closed Elasticsearch writer")
        
        # ParquetWriter doesn't need explicit closing