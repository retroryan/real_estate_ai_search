"""
Writer orchestrator for coordinating multiple data writers.

This module provides a simple orchestrator that manages multiple data writers
and executes them sequentially with fail-fast error handling.
"""

import logging
from typing import Any, Dict, List, Optional

from pyspark.sql import DataFrame

from data_pipeline.writers.base import DataWriter

logger = logging.getLogger(__name__)


class WriterOrchestrator:
    """
    Simple sequential writer orchestrator.
    
    Manages multiple data writers and executes them in sequence.
    Fails immediately if any writer fails (fail-fast approach).
    """
    
    def __init__(self, writers: List[DataWriter]):
        """
        Initialize the orchestrator with a list of writers.
        
        Args:
            writers: List of DataWriter instances to manage
        """
        self.writers = writers
        self.logger = logging.getLogger(__name__)
    
    def validate_all_connections(self) -> None:
        """
        Validate connections for all writers.
        
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
    
    def write_to_all(self, df: DataFrame, metadata: Dict[str, Any]) -> None:
        """
        Write DataFrame to all configured destinations sequentially.
        
        Args:
            df: DataFrame to write
            metadata: Metadata about the data being written
            
        Raises:
            RuntimeError: If any write operation fails
        """
        if not self.writers:
            self.logger.warning("No writers configured")
            return
        
        total_writers = len([w for w in self.writers if w.is_enabled()])
        self.logger.info(f"Writing to {total_writers} destination(s)...")
        
        for writer in self.writers:
            if not writer.is_enabled():
                self.logger.info(f"Skipping disabled writer: {writer.get_writer_name()}")
                continue
                
            writer_name = writer.get_writer_name()
            self.logger.info(f"Writing to {writer_name}...")
            
            try:
                success = writer.write(df, metadata)
                if not success:
                    raise RuntimeError(f"Write operation returned False for {writer_name}")
                
                self.logger.info(f"Successfully wrote to {writer_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to write to {writer_name}: {e}")
                raise RuntimeError(f"Failed to write to {writer_name}: {e}")
        
        self.logger.info(f"Successfully wrote to all {total_writers} destination(s)")
    
    def write_entity_dataframes(self, entity_dataframes: Dict[str, DataFrame], metadata: Dict[str, Any]) -> None:
        """
        Write entity-specific DataFrames to configured destinations.
        
        Args:
            entity_dataframes: Dictionary of entity type to DataFrame
            metadata: Metadata about the data being written
            
        Raises:
            RuntimeError: If any write operation fails
        """
        if not self.writers:
            self.logger.warning("No writers configured")
            return
        
        if not entity_dataframes:
            self.logger.warning("No DataFrames to write")
            return
        
        # Count total operations
        total_operations = 0
        for entity_type, df in entity_dataframes.items():
            if df is not None:
                enabled_writers = [w for w in self.writers if w.is_enabled() and entity_type in w.get_writer_name()]
                total_operations += len(enabled_writers)
        
        self.logger.info(f"Writing {len(entity_dataframes)} entity types to destination(s)...")
        
        # Process each entity type
        for entity_type, df in entity_dataframes.items():
            if df is None:
                self.logger.debug(f"Skipping {entity_type} - no data")
                continue
            
            # Find writers for this entity type
            entity_writers = [w for w in self.writers if w.is_enabled() and entity_type in w.get_writer_name()]
            
            if not entity_writers:
                self.logger.debug(f"No writers found for entity type: {entity_type}")
                continue
            
            self.logger.info(f"Writing {entity_type} to {len(entity_writers)} destination(s)...")
            
            # Write to each destination for this entity
            for writer in entity_writers:
                writer_name = writer.get_writer_name()
                self.logger.info(f"Writing {entity_type} to {writer_name}...")
                
                try:
                    entity_metadata = metadata.copy()
                    entity_metadata["entity_type"] = entity_type
                    
                    success = writer.write(df, entity_metadata)
                    if not success:
                        raise RuntimeError(f"Write operation returned False for {writer_name}")
                    
                    self.logger.info(f"Successfully wrote {entity_type} to {writer_name}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to write {entity_type} to {writer_name}: {e}")
                    raise RuntimeError(f"Failed to write {entity_type} to {writer_name}: {e}")
        
        self.logger.info(f"Successfully completed all write operations")
    
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