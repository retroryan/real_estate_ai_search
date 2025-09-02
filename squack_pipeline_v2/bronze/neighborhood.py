"""Neighborhood Bronze layer ingestion - raw data only."""

from pathlib import Path
from typing import Optional
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import log_stage, PipelineLogger
from squack_pipeline_v2.bronze.base import BronzeIngester, BronzeMetadata


class NeighborhoodBronzeIngester(BronzeIngester):
    """Ingester for raw neighborhood data into Bronze layer.
    
    Bronze layer principle: Load data AS-IS from source with NO transformations.
    DuckDB's read_json_auto handles all the nested structure preservation.
    """
    
    def __init__(self, settings: PipelineSettings, connection_manager: DuckDBConnectionManager):
        """Initialize neighborhood ingester.
        
        Args:
            settings: Pipeline settings
            connection_manager: DuckDB connection manager
        """
        self.settings = settings
        self.connection_manager = connection_manager
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        self.records_ingested = 0
    
    @log_stage("Bronze: Neighborhood Raw Ingestion")
    def ingest(
        self,
        table_name: str,
        file_path: Optional[Path] = None,
        sample_size: Optional[int] = None
    ) -> BronzeMetadata:
        """Ingest raw neighborhood data from JSON file(s).
        
        Bronze principle: NO transformations, just raw load.
        Now supports loading multiple neighborhood files.
        
        Args:
            table_name: Target table name in DuckDB
            file_path: Path to JSON file (if None, loads ALL files from settings)
            sample_size: Optional number of records to load for testing
        """
        conn = self.connection_manager.get_connection()
        
        # Determine which files to load
        if file_path is not None:
            # Single file mode (for backward compatibility)
            files_to_load = [file_path]
        else:
            # Load ALL files from settings
            files_to_load = [Path(f) for f in self.settings.data_sources.neighborhoods_files]
            self.logger.info(f"Loading {len(files_to_load)} neighborhood files from settings")
        
        # Validate all files exist
        for file in files_to_load:
            if not file.exists():
                raise FileNotFoundError(f"Neighborhoods JSON file not found: {file}")
        
        # Drop existing table if it exists
        self.connection_manager.drop_table(table_name)
        
        # Track total records loaded
        total_records = 0
        first_file = True
        
        # Load each file
        for file in files_to_load:
            self.logger.info(f"Loading raw neighborhoods from: {file}")
            
            # Use Relation API to safely load JSON
            relation = conn.read_json(
                str(file.absolute()),
                maximum_object_size=20000000,
                format='auto'
            )
            
            # Apply sample limit if needed (only on first file for simplicity)
            if sample_size and first_file:
                relation = relation.limit(sample_size)
            
            if first_file:
                # Create table from first file
                relation.create(table_name)
                first_file = False
            else:
                # Append to existing table
                conn.execute(f"INSERT INTO {table_name} SELECT * FROM relation")
            
            # Count records from this file
            file_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0] - total_records
            total_records += file_count
            self.logger.info(f"  Loaded {file_count} records from {file.name}")
        
        # Get final record count for metrics
        self.records_ingested = self.connection_manager.count_records(table_name)
        
        self.logger.info(f"Total: Loaded {self.records_ingested} raw neighborhood records into {table_name}")
        
        # Return metadata (using first file path for backward compatibility)
        return BronzeMetadata(
            table_name=table_name,
            source_path=files_to_load[0].absolute(),
            record_count=self.records_ingested,
            entity_type=self._get_entity_type()
        )
    
    def _get_entity_type(self) -> str:
        """Get the entity type for this ingester.
        
        Returns:
            Entity type string
        """
        return "neighborhood"