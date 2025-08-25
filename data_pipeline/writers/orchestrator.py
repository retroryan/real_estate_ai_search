"""
Type-safe entity-aware writer orchestrator.

This module provides a Pydantic-based orchestrator that manages multiple data writers
with full type safety and validation.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pyspark.sql import DataFrame

from data_pipeline.models.writer_models import (
    EntityType,
    EntityWriteRequests,
    WriteMetadata,
    WriteRequest,
    WriteResult,
    WriteSessionResult,
)
from data_pipeline.writers.base import EntityWriter

logger = logging.getLogger(__name__)


class WriterOrchestrator:
    """
    Type-safe entity-aware writer orchestrator.
    
    Manages multiple data writers with Pydantic models ensuring
    type safety and validation throughout the write process.
    """
    
    def __init__(self, writers: List[EntityWriter]):
        """
        Initialize the orchestrator with a list of writers.
        
        Args:
            writers: List of EntityWriter instances to manage
        """
        self.writers = writers
        self.logger = logging.getLogger(__name__)
    
    def validate_all_connections(self) -> None:
        """
        Validate connections for all enabled writers.
        
        Raises:
            RuntimeError: If any writer fails connection validation
        """
        self.logger.info("Validating connections for all writers...")
        
        for writer in self.writers:
            if not writer.is_enabled():
                self.logger.info(f"Skipping disabled writer: {writer.get_writer_name()}")
                continue
                
            writer_name = writer.get_writer_name()
            self.logger.info(f"Validating connection for {writer_name}...")
            
            if not writer.validate_connection():
                raise RuntimeError(f"Connection validation failed for {writer_name}")
            
            self.logger.info(f"Connection validated for {writer_name}")
        
        self.logger.info("All connections validated successfully")
    
    def write_entity(self, request: WriteRequest) -> List[WriteResult]:
        """
        Write a single entity DataFrame to all configured destinations using type-safe request.
        
        Args:
            request: Type-safe write request with entity type, DataFrame, and metadata
            
        Returns:
            List of WriteResult objects for each writer
            
        Raises:
            RuntimeError: If any write operation fails
        """
        if not self.writers:
            self.logger.warning("No writers configured")
            return []
        
        results = []
        entity_type = request.entity_type
        df = request.dataframe
        metadata = request.metadata
        
        # Ensure metadata has correct entity type
        metadata.entity_type = entity_type
        
        # Get record count if not provided
        if metadata.record_count == 0:
            metadata.record_count = df.count()
        
        self.logger.info(
            f"Writing {metadata.record_count} {entity_type} records to {len(self.writers)} writer(s)"
        )
        
        # Write to each enabled writer
        for writer in self.writers:
            if not writer.is_enabled():
                self.logger.debug(f"Skipping disabled writer: {writer.get_writer_name()}")
                continue
            
            writer_name = writer.get_writer_name()
            start_time = datetime.now()
            
            self.logger.info(f"Writing {entity_type} to {writer_name}...")
            
            try:
                # Call entity-specific write method
                if entity_type == EntityType.PROPERTY:
                    success = writer.write_properties(df)
                elif entity_type == EntityType.NEIGHBORHOOD:
                    success = writer.write_neighborhoods(df)
                elif entity_type == EntityType.WIKIPEDIA:
                    success = writer.write_wikipedia(df)
                else:
                    raise RuntimeError(f"Unknown entity type: {entity_type}")
                
                if not success:
                    raise RuntimeError(f"Write operation returned False")
                
                duration = (datetime.now() - start_time).total_seconds()
                
                output_path = getattr(writer, 'get_entity_path', lambda x: None)(entity_type)
                result = WriteResult(
                    entity_type=entity_type,
                    writer_name=writer_name,
                    success=True,
                    records_written=metadata.record_count,
                    duration_seconds=duration,
                    output_path=str(output_path) if output_path else None
                )
                results.append(result)
                
                self.logger.info(f"Successfully wrote {entity_type} to {writer_name}")
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                
                result = WriteResult(
                    entity_type=entity_type,
                    writer_name=writer_name,
                    success=False,
                    records_written=0,
                    duration_seconds=duration,
                    error_message=str(e)
                )
                results.append(result)
                
                self.logger.error(f"Failed to write {entity_type} to {writer_name}: {e}")
                raise RuntimeError(f"Failed to write {entity_type} to {writer_name}: {e}")
        
        self.logger.info(f"Successfully wrote {entity_type} to all destinations")
        return results
    
    def write_all_entities(self, requests: EntityWriteRequests) -> WriteSessionResult:
        """
        Write all entity DataFrames to configured destinations using type-safe requests.
        
        Args:
            requests: Container with write requests for each entity type
            
        Returns:
            WriteSessionResult with detailed results for all operations
            
        Raises:
            RuntimeError: If any write operation fails
        """
        session_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        session_result = WriteSessionResult(
            session_id=session_id,
            start_time=start_time,
            end_time=start_time,  # Will be updated
            total_duration_seconds=0
        )
        
        if not requests.has_data():
            self.logger.warning("No entity write requests provided")
            session_result.end_time = datetime.now()
            session_result.total_duration_seconds = (session_result.end_time - start_time).total_seconds()
            return session_result
        
        entity_requests = requests.get_requests()
        self.logger.info(f"Writing {len(entity_requests)} entity type(s) to destinations...")
        
        # Process each entity request
        for request in entity_requests:
            try:
                results = self.write_entity(request)
                for result in results:
                    session_result.add_result(result)
            except RuntimeError as e:
                # Already logged, just update session result
                session_result.end_time = datetime.now()
                session_result.total_duration_seconds = (session_result.end_time - start_time).total_seconds()
                raise
        
        session_result.end_time = datetime.now()
        session_result.total_duration_seconds = (session_result.end_time - start_time).total_seconds()
        
        self.logger.info(
            f"Write session {session_id} completed: "
            f"{session_result.successful_writes} successful, "
            f"{session_result.failed_writes} failed, "
            f"{session_result.total_records_written} total records"
        )
        
        return session_result
    
    def write_dataframes(self,
                        properties_df: Optional[DataFrame] = None,
                        neighborhoods_df: Optional[DataFrame] = None,
                        wikipedia_df: Optional[DataFrame] = None,
                        pipeline_name: str = "data_pipeline",
                        pipeline_version: str = "1.0.0",
                        environment: str = "development") -> WriteSessionResult:
        """
        Convenience method to write DataFrames with automatic request creation.
        
        Args:
            properties_df: Property DataFrame
            neighborhoods_df: Neighborhood DataFrame
            wikipedia_df: Wikipedia DataFrame
            pipeline_name: Name of the pipeline
            pipeline_version: Version of the pipeline
            environment: Environment name
            
        Returns:
            WriteSessionResult with all write operation results
        """
        requests = EntityWriteRequests()
        
        # Create request for properties if provided
        if properties_df is not None:
            metadata = WriteMetadata(
                pipeline_name=pipeline_name,
                pipeline_version=pipeline_version,
                entity_type=EntityType.PROPERTY,
                record_count=properties_df.count(),
                environment=environment
            )
            requests.property_request = WriteRequest(
                entity_type=EntityType.PROPERTY,
                dataframe=properties_df,
                metadata=metadata
            )
        
        # Create request for neighborhoods if provided
        if neighborhoods_df is not None:
            metadata = WriteMetadata(
                pipeline_name=pipeline_name,
                pipeline_version=pipeline_version,
                entity_type=EntityType.NEIGHBORHOOD,
                record_count=neighborhoods_df.count(),
                environment=environment
            )
            requests.neighborhood_request = WriteRequest(
                entity_type=EntityType.NEIGHBORHOOD,
                dataframe=neighborhoods_df,
                metadata=metadata
            )
        
        # Create request for wikipedia if provided
        if wikipedia_df is not None:
            metadata = WriteMetadata(
                pipeline_name=pipeline_name,
                pipeline_version=pipeline_version,
                entity_type=EntityType.WIKIPEDIA,
                record_count=wikipedia_df.count(),
                environment=environment
            )
            requests.wikipedia_request = WriteRequest(
                entity_type=EntityType.WIKIPEDIA,
                dataframe=wikipedia_df,
                metadata=metadata
            )
        
        return self.write_all_entities(requests)
    
    def write_all_relationships(self, relationships: Dict[str, DataFrame]) -> bool:
        """
        Write relationships to all writers that support them.
        
        Args:
            relationships: Dictionary of relationship name to DataFrame
            
        Returns:
            True if all relationship-supporting writers succeeded, False if any failed
        """
        if not relationships:
            self.logger.debug("No relationships to write")
            return True
        
        all_successful = True
        writers_that_support_relationships = [
            w for w in self.writers 
            if w.is_enabled() and w.supports_relationships()
        ]
        
        if not writers_that_support_relationships:
            self.logger.debug("No writers support relationships")
            return True
        
        self.logger.info(
            f"Writing relationships to {len(writers_that_support_relationships)} "
            f"relationship-supporting writer(s)"
        )
        
        for writer in writers_that_support_relationships:
            writer_name = writer.get_writer_name()
            self.logger.info(f"Writing relationships to {writer_name}...")
            
            try:
                if writer.write_relationships(relationships):
                    self.logger.info(f"Successfully wrote relationships to {writer_name}")
                else:
                    self.logger.error(f"Failed to write relationships to {writer_name}")
                    all_successful = False
            except Exception as e:
                self.logger.error(f"Exception writing relationships to {writer_name}: {e}")
                all_successful = False
        
        return all_successful
    
    def get_enabled_writers(self) -> List[str]:
        """
        Get list of enabled writer names.
        
        Returns:
            List of writer names that are enabled
        """
        return [w.get_writer_name() for w in self.writers if w.is_enabled()]
    
    def get_all_writers(self) -> List[str]:
        """
        Get list of all writer names.
        
        Returns:
            List of all writer names
        """
        return [w.get_writer_name() for w in self.writers]
    
    def clear_all_data(self) -> None:
        """
        Clear existing data in all writers that support clearing.
        
        This is useful for demo purposes to ensure clean state.
        """
        self.logger.info("Clearing existing data in all writers...")
        
        for writer in self.writers:
            if not writer.is_enabled():
                continue
            
            writer_name = writer.get_writer_name()
            
            # Check if writer has clear_data method
            if hasattr(writer, 'clear_data'):
                try:
                    writer.clear_data()
                    self.logger.info(f"Cleared data in {writer_name}")
                except Exception as e:
                    self.logger.warning(f"Failed to clear data in {writer_name}: {e}")
            
            # For ParquetWriter, clear entity-specific data
            if hasattr(writer, 'clear_entity_data'):
                for entity_type in ["property", "neighborhood", "wikipedia"]:
                    try:
                        writer.clear_entity_data(entity_type)
                        self.logger.info(f"Cleared {entity_type} data in {writer_name}")
                    except Exception as e:
                        self.logger.warning(f"Failed to clear {entity_type} data in {writer_name}: {e}")