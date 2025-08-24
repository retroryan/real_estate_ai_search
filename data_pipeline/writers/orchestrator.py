"""
Writer orchestrator for coordinating multiple data writers.

This module provides a simple orchestrator that manages multiple data writers
and executes them sequentially with fail-fast error handling.
"""

import logging
from typing import Any, Dict, List

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