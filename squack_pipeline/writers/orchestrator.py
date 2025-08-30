"""Writer orchestrator for managing multiple output destinations.

This module provides the central orchestration point for all data writers.
To add a new output destination:
1. Add the destination to OutputDestination enum
2. Create a writer class extending BaseWriter
3. Add initialization logic in _initialize_writers()
4. Add write logic in write_all()
"""

import time
from typing import Dict, List, Optional, Any

import duckdb

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.writers.base import BaseWriter
from squack_pipeline.writers.parquet_writer import ParquetWriter
from squack_pipeline.writers.elasticsearch import ElasticsearchWriter
from squack_pipeline.models import EntityType
from squack_pipeline.models.duckdb_models import TableIdentifier
from squack_pipeline.models.data_types import OutputDestination
from squack_pipeline.models.writer_interface import WriteRequest, WriteResponse
from squack_pipeline.writers.elasticsearch.models import WriteResult
from squack_pipeline.models.writer_models import (
    WriteDestinationResults,
    WriteOperationResult
)
from squack_pipeline.utils.logging import PipelineLogger
from squack_pipeline.utils.duckdb_extractor import DuckDBExtractor


class WriterOrchestrator:
    """Orchestrates writing data to multiple output destinations.
    
    This class centralizes the management of all writers and provides
    a clean extension point for adding new output destinations.
    """
    
    def __init__(self, settings: PipelineSettings):
        """Initialize the writer orchestrator.
        
        Args:
            settings: Pipeline settings with output configuration
        """
        self.settings = settings
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        
        # Initialize data extractor for legacy compatibility
        self.extractor = DuckDBExtractor()
        
        # Dictionary to hold all initialized writers
        # Key: OutputDestination enum value
        # Value: Writer instance extending BaseWriter
        self.writers: Dict[OutputDestination, BaseWriter] = {}
        
        # Legacy writer references for backward compatibility
        self.parquet_writer: Optional[ParquetWriter] = None
        self.es_writer: Optional[ElasticsearchWriter] = None
        
        # Initialize all configured writers
        self._validate_configuration()
        self._initialize_writers()
    
    def _validate_configuration(self) -> None:
        """Validate that all enabled destinations have proper configuration.
        
        This ensures that each enabled destination has the necessary
        configuration before attempting to initialize its writer.
        """
        destinations = self.settings.output.enabled_destinations
        
        for destination in destinations:
            if destination == OutputDestination.ELASTICSEARCH:
                if not self.settings.output.elasticsearch:
                    raise ValueError(
                        f"Elasticsearch is enabled but configuration is missing. "
                        f"Please add 'elasticsearch' section to output config."
                    )
            # Add validation for other destinations as needed
            # elif destination == OutputDestination.CSV:
            #     if not self.settings.output.csv:
            #         raise ValueError("CSV enabled but configuration missing")
        
        self.logger.debug(f"Validated configuration for {len(destinations)} destinations")
    
    def _initialize_writers(self) -> None:
        """Initialize writers based on enabled destinations.
        
        EXTENSION POINT: To add a new writer, add a new if/elif block here.
        Follow the pattern of existing writers:
        1. Check if destination is enabled
        2. Initialize the writer with settings
        3. Add to self.writers dictionary
        4. Log the initialization
        """
        destinations = self.settings.output.enabled_destinations
        self.logger.info(f"Initializing writers for destinations: {[d.value for d in destinations]}")
        
        # ============================================================
        # PARQUET WRITER
        # ============================================================
        if OutputDestination.PARQUET in destinations:
            try:
                writer = ParquetWriter(self.settings)
                self.writers[OutputDestination.PARQUET] = writer
                self.parquet_writer = writer  # Legacy reference
                self.logger.info("✓ Initialized Parquet writer")
            except Exception as e:
                self.logger.error(f"Failed to initialize Parquet writer: {e}")
                raise
        
        # ============================================================
        # ELASTICSEARCH WRITER
        # ============================================================
        if OutputDestination.ELASTICSEARCH in destinations:
            try:
                writer = ElasticsearchWriter(self.settings)
                # Verify connection for network-based writers
                if writer.verify_connection():
                    self.writers[OutputDestination.ELASTICSEARCH] = writer
                    self.es_writer = writer  # Legacy reference
                    self.logger.info("✓ Initialized Elasticsearch writer with verified connection")
                else:
                    self.logger.error("Failed to verify Elasticsearch connection")
                    # Don't add to writers dict if connection failed
            except Exception as e:
                self.logger.error(f"Failed to initialize Elasticsearch writer: {e}")
                raise
        
        # ============================================================
        # ADD NEW WRITERS HERE
        # ============================================================
        # Example for adding a CSV writer:
        # if OutputDestination.CSV in destinations:
        #     try:
        #         writer = CSVWriter(self.settings)
        #         self.writers[OutputDestination.CSV] = writer
        #         self.logger.info("✓ Initialized CSV writer")
        #     except Exception as e:
        #         self.logger.error(f"Failed to initialize CSV writer: {e}")
        #         raise
        
        self.logger.info(f"Successfully initialized {len(self.writers)} writer(s)")
    
    def write_all(
        self,
        connection: duckdb.DuckDBPyConnection,
        tables: Dict[EntityType, str]
    ) -> Dict[str, List[Any]]:
        """Write all entities to all configured destinations.
        
        This method iterates through all initialized writers and
        writes data to each destination.
        
        Args:
            connection: DuckDB connection
            tables: Mapping of entity types to table names
            
        Returns:
            Dictionary of results by destination
        """
        results = {}
        
        # Process each configured writer
        for destination, writer in self.writers.items():
            self.logger.info(f"Writing to {destination.value}...")
            
            try:
                if destination == OutputDestination.PARQUET:
                    # Use specific Parquet logic
                    parquet_results = self._write_parquet(connection, tables)
                    results[destination.value] = parquet_results
                    
                elif destination == OutputDestination.ELASTICSEARCH:
                    # Use specific Elasticsearch logic
                    es_results = self._write_elasticsearch(connection, tables)
                    results[destination.value] = es_results
                    
                # ============================================================
                # ADD NEW DESTINATION WRITE LOGIC HERE
                # ============================================================
                # elif destination == OutputDestination.CSV:
                #     csv_results = self._write_csv(connection, tables)
                #     results[destination.value] = csv_results
                
                else:
                    self.logger.warning(f"No write implementation for {destination.value}")
                    
            except Exception as e:
                self.logger.error(f"Failed to write to {destination.value}: {e}")
                # Continue with other destinations even if one fails
                results[destination.value] = [{
                    'success': False,
                    'error': str(e)
                }]
        
        return results
    
    def _write_parquet(
        self,
        connection: duckdb.DuckDBPyConnection,
        tables: Dict[EntityType, str]
    ) -> List[Dict[str, Any]]:
        """Write entities to Parquet files.
        
        Args:
            connection: DuckDB connection
            tables: Mapping of entity types to table names
            
        Returns:
            List of write results
        """
        results = []
        writer = self.writers.get(OutputDestination.PARQUET)
        
        if not writer:
            return results
        
        # Set connection for ParquetWriter
        writer.set_connection(connection)
        
        # Write each entity type
        for entity_type, table_name in tables.items():
            if not table_name:
                continue
            
            try:
                # Generate output filename
                timestamp = int(time.time())
                output_filename = f"{entity_type.value}_{timestamp}.parquet"
                output_path = self.settings.data.output_path / output_filename
                
                # Write using legacy method for backward compatibility
                written_path = writer.write_with_schema(
                    table_name=table_name,
                    output_path=output_path
                )
                
                # Get record count
                safe_table = TableIdentifier(name=table_name)
                record_count = connection.execute(
                    f"SELECT COUNT(*) FROM {safe_table.qualified_name}"
                ).fetchone()[0]
                
                results.append({
                    'entity_type': entity_type.value,
                    'path': str(written_path),
                    'record_count': record_count,
                    'success': True
                })
                
                self.logger.success(f"Wrote {record_count} {entity_type.value} records to {written_path}")
                
            except Exception as e:
                self.logger.error(f"Failed to write {entity_type.value} to Parquet: {str(e)}")
                results.append({
                    'entity_type': entity_type.value,
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def _write_elasticsearch(
        self,
        connection: duckdb.DuckDBPyConnection,
        tables: Dict[EntityType, str]
    ) -> List[WriteResult]:
        """Extract data from DuckDB and write to Elasticsearch.
        
        Args:
            connection: DuckDB connection
            tables: Mapping of entity types to table names
            
        Returns:
            List of WriteResult objects
        """
        results = []
        writer = self.writers.get(OutputDestination.ELASTICSEARCH)
        
        if not writer:
            return results
        
        for entity_type, table_name in tables.items():
            if not table_name:
                continue
            
            try:
                self.logger.info(f"Extracting {entity_type.value} from {table_name}...")
                
                # Extract data from DuckDB as Pydantic models
                extraction_result = self.extractor.extract_records(connection, table_name, entity_type)
                
                # Convert Pydantic models to dicts for Elasticsearch
                data = [record.to_dict() for record in extraction_result.records]
                
                self.logger.info(f"Writing {extraction_result.total_count} {entity_type.value} records to Elasticsearch ({extraction_result.embeddings_count} with embeddings)...")
                
                # Write to Elasticsearch using legacy method
                result = writer.write_entity(entity_type, data)
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Failed to write {entity_type.value} to Elasticsearch: {str(e)}")
                results.append(WriteResult(
                    success=False,
                    entity_type=entity_type,
                    record_count=0,
                    failed_count=0,
                    index_name=entity_type.value,
                    error=str(e)
                ))
        
        return results
    
    def write_entity(
        self,
        entity_type: EntityType,
        table_name: str,
        connection: duckdb.DuckDBPyConnection
    ) -> WriteOperationResult:
        """Write a single entity to all configured destinations.
        
        This method provides a simpler interface for writing a single
        entity type to all destinations.
        
        Args:
            entity_type: Type of entity being written
            table_name: Name of the table containing the data
            connection: DuckDB connection
            
        Returns:
            WriteOperationResult with results from all destinations
        """
        result = WriteOperationResult()
        
        # Get record count once for all destinations
        try:
            record_count = self.extractor.extract_count(connection, table_name)
        except Exception as e:
            self.logger.error(f"Failed to get record count from {table_name}: {str(e)}")
            record_count = 0
        
        # Write to each configured destination
        for destination, writer in self.writers.items():
            self.logger.info(f"Writing {entity_type.value} to {destination.value}...")
            
            try:
                # Create a write request
                request = WriteRequest(
                    entity_type=entity_type,
                    table_name=table_name,
                    record_count=record_count
                )
                
                # Set connection for writers that need it
                writer.set_connection(connection)
                
                # Write using the standardized interface
                response = writer.write(request)
                
                # Convert response to WriteResult for backward compatibility
                write_result = WriteResult(
                    success=response.success,
                    entity_type=entity_type,
                    record_count=response.metrics.records_written,
                    failed_count=response.metrics.records_failed,
                    index_name=response.destination,
                    error=response.error
                )
                
                # Add to results
                result.add_destination_result(
                    destination,
                    WriteDestinationResults(
                        destination=destination,
                        results=[write_result]
                    )
                )
                
                # Update embedding count if available
                try:
                    if response.metrics.embeddings_count:
                        result.embeddings_count = max(result.embeddings_count, response.metrics.embeddings_count)
                except AttributeError:
                    pass  # Not all metrics have embeddings_count
                    
            except Exception as e:
                self.logger.error(f"Failed to write {entity_type.value} to {destination.value}: {str(e)}")
                
                # Add failure result
                write_result = WriteResult(
                    success=False,
                    entity_type=entity_type,
                    record_count=0,
                    failed_count=record_count,
                    index_name=table_name,
                    error=str(e)
                )
                
                result.add_destination_result(
                    destination,
                    WriteDestinationResults(
                        destination=destination,
                        results=[write_result]
                    )
                )
        
        return result
    
    def close(self):
        """Close all writer connections and clean up resources."""
        for destination, writer in self.writers.items():
            try:
                writer.cleanup()
                self.logger.debug(f"Cleaned up {destination.value} writer")
            except Exception as e:
                self.logger.warning(f"Error cleaning up {destination.value} writer: {e}")
        
        self.writers.clear()
        self.logger.info("All writers closed")