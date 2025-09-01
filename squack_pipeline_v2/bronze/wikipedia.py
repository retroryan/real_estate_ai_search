"""Wikipedia Bronze layer ingestion from SQLite database - raw data only."""

from pathlib import Path
from typing import Optional
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import log_stage, PipelineLogger
from squack_pipeline_v2.bronze.metadata import BronzeMetadata


class WikipediaBronzeIngester:
    """Ingester for raw Wikipedia data from SQLite database into Bronze layer.
    
    Bronze layer principle: Load data AS-IS from source with NO transformations.
    Uses DuckDB's SQLite extension to directly query the Wikipedia database.
    """
    
    def __init__(self, settings: PipelineSettings, connection_manager: DuckDBConnectionManager):
        """Initialize Wikipedia ingester.
        
        Args:
            settings: Pipeline settings
            connection_manager: DuckDB connection manager
        """
        self.settings = settings
        self.connection_manager = connection_manager
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        self.records_ingested = 0
    
    @log_stage("Bronze: Wikipedia Raw Ingestion from SQLite")
    def ingest(
        self,
        table_name: str,
        db_path: Optional[Path] = None,
        sample_size: Optional[int] = None
    ) -> BronzeMetadata:
        """Ingest raw Wikipedia data from SQLite database.
        
        Bronze principle: NO transformations, just raw load from SQLite.
        
        Args:
            table_name: Target table name in DuckDB
            db_path: Path to SQLite database (uses settings if not provided)
            sample_size: Optional number of records to load for testing
        """
        # Use provided path or get from settings
        if db_path is None:
            db_path = Path(self.settings.data_sources.wikipedia_db_path)
        
        # Validate SQLite database exists
        if not db_path.exists():
            raise FileNotFoundError(f"Wikipedia SQLite database not found: {db_path}")
        
        self.logger.info(f"Loading raw Wikipedia articles from SQLite: {db_path}")
        
        try:
            # Install and load SQLite extension
            self.connection_manager.execute("INSTALL sqlite")
            self.connection_manager.execute("LOAD sqlite")
            
            # Attach the SQLite database
            attach_query = f"ATTACH '{db_path.absolute()}' AS wiki_db (TYPE sqlite)"
            self.connection_manager.execute(attach_query)
            
            # Drop existing Bronze table if it exists
            self.connection_manager.drop_table(table_name)
            
            # Create Bronze table with raw data from SQLite articles table
            # Bronze principle: RAW DATA ONLY - no joins, no transformations
            if sample_size:
                create_query = f"""
                CREATE TABLE {table_name} AS
                SELECT * FROM wiki_db.articles
                LIMIT {sample_size}
                """
            else:
                create_query = f"""
                CREATE TABLE {table_name} AS
                SELECT * FROM wiki_db.articles
                """
            
            self.connection_manager.execute(create_query)
            
            # Get record count for metrics
            count_result = self.connection_manager.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()
            self.records_ingested = count_result[0] if count_result else 0
            
            self.logger.info(f"Loaded {self.records_ingested} raw Wikipedia articles into {table_name}")
            
            return BronzeMetadata(
                table_name=table_name,
                source_path=str(db_path.absolute()),
                records_loaded=self.records_ingested,
                sample_size=sample_size if sample_size else 0
            )
            
        finally:
            # Always detach the SQLite database to release locks
            try:
                self.connection_manager.execute("DETACH wiki_db")
            except Exception as e:
                self.logger.warning(f"Could not detach wiki_db: {e}")
        
        # Return metadata even if error occurred during detach
        return BronzeMetadata(
            table_name=table_name,
            source_path=str(db_path.absolute()),
            records_loaded=self.records_ingested,
            sample_size=sample_size if sample_size else 0
        )