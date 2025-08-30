"""Property Bronze layer ingestion - raw data only."""

from pathlib import Path
from typing import Optional
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import log_stage, PipelineLogger


class PropertyBronzeIngester:
    """Ingester for raw property data into Bronze layer.
    
    Bronze layer principle: Load data AS-IS from source with NO transformations.
    DuckDB's read_json_auto handles all the nested structure preservation.
    """
    
    def __init__(self, settings: PipelineSettings, connection_manager: DuckDBConnectionManager):
        """Initialize property ingester.
        
        Args:
            settings: Pipeline settings
            connection_manager: DuckDB connection manager
        """
        self.settings = settings
        self.connection_manager = connection_manager
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        self.records_ingested = 0
    
    @log_stage("Bronze: Property Raw Ingestion")
    def ingest(
        self,
        file_path: Optional[Path] = None,
        table_name: str = "bronze_properties",
        sample_size: Optional[int] = None
    ) -> None:
        """Ingest raw property data from JSON file.
        
        Bronze principle: NO transformations, just raw load.
        
        Args:
            file_path: Path to JSON file (uses settings if not provided)
            table_name: Target table name in DuckDB
            sample_size: Optional number of records to load for testing
        """
        # Use provided path or get from settings
        if file_path is None:
            file_path = Path(self.settings.data_sources.properties_files[0])
        
        # Validate file exists
        if not file_path.exists():
            raise FileNotFoundError(f"Properties JSON file not found: {file_path}")
        
        self.logger.info(f"Loading raw properties from: {file_path}")
        
        # Drop existing table if it exists
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Load JSON directly into DuckDB - let DuckDB handle all structure
        if sample_size:
            query = f"""
            CREATE TABLE {table_name} AS
            SELECT * FROM read_json_auto(
                '{file_path.absolute()}',
                maximum_object_size=20000000
            )
            LIMIT {sample_size}
            """
        else:
            query = f"""
            CREATE TABLE {table_name} AS
            SELECT * FROM read_json_auto(
                '{file_path.absolute()}',
                maximum_object_size=20000000
            )
            """
        
        self.connection_manager.execute(query)
        
        # Get record count for metrics
        count_result = self.connection_manager.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()
        self.records_ingested = count_result[0] if count_result else 0
        
        self.logger.info(f"Loaded {self.records_ingested} raw property records into {table_name}")