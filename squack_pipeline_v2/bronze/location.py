"""Location Bronze layer ingestion - raw geographic hierarchy data."""

from pathlib import Path
from typing import Optional
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import log_stage, PipelineLogger
from squack_pipeline_v2.bronze.base import BronzeIngester, BronzeMetadata


class LocationBronzeIngester(BronzeIngester):
    """Ingester for raw location hierarchy data into Bronze layer.
    
    Bronze layer principle: Load data AS-IS from source with NO transformations.
    This provides the complete geographic hierarchy needed for relationships.
    """
    
    def __init__(self, settings: PipelineSettings, connection_manager: DuckDBConnectionManager):
        """Initialize location ingester.
        
        Args:
            settings: Pipeline settings
            connection_manager: DuckDB connection manager
        """
        self.settings = settings
        self.connection_manager = connection_manager
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        self.records_ingested = 0
    
    @log_stage("Bronze: Location Raw Ingestion")
    def ingest(
        self,
        table_name: str,
        file_path: Optional[Path] = None,
        sample_size: Optional[int] = None
    ) -> BronzeMetadata:
        """Ingest raw location hierarchy data from JSON file.
        
        Bronze principle: NO transformations, just raw load.
        
        Args:
            table_name: Target table name in DuckDB
            file_path: Path to JSON file (uses settings if not provided)
            sample_size: Optional number of records to load for testing
        """
        # Use provided path or get from settings
        if file_path is None:
            file_path = Path(self.settings.data_sources.locations_file)
        
        # Validate file exists
        if not file_path.exists():
            raise FileNotFoundError(f"Locations JSON file not found: {file_path}")
        
        self.logger.info(f"Loading raw locations from: {file_path}")
        
        # Drop existing table if it exists
        self.connection_manager.drop_table(table_name)
        
        # Use Relation API to safely load JSON
        conn = self.connection_manager.get_connection()
        relation = conn.read_json(
            str(file_path.absolute()),
            maximum_object_size=20000000,
            format='auto'
        )
        
        # Apply sample limit if needed
        if sample_size:
            relation = relation.limit(sample_size)
        
        # Create table from relation
        relation.create(table_name)
        
        # Get record count for metrics
        self.records_ingested = self.connection_manager.count_records(table_name)
        
        self.logger.info(f"Loaded {self.records_ingested} raw location records into {table_name}")
        
        return BronzeMetadata(
            table_name=table_name,
            source_path=file_path.absolute(),
            record_count=self.records_ingested,
            entity_type=self._get_entity_type()
        )
    
    def _get_entity_type(self) -> str:
        """Get the entity type for this ingester.
        
        Returns:
            Entity type string
        """
        return "location"