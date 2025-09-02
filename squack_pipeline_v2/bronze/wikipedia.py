"""Wikipedia Bronze layer ingestion from SQLite database - raw data only."""

from pathlib import Path
from typing import Optional
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import log_stage, PipelineLogger
from squack_pipeline_v2.bronze.base import BronzeIngester, BronzeMetadata


class WikipediaBronzeIngester(BronzeIngester):
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
            
            # Attach the SQLite database - validate path first
            conn = self.connection_manager.get_connection()
            # Validate path to prevent injection
            db_path_str = str(db_path.absolute())
            if "'" in db_path_str or ";" in db_path_str:
                raise ValueError(f"Invalid characters in database path: {db_path_str}")
            
            conn.execute(f"ATTACH '{db_path_str}' AS wiki_db (TYPE sqlite)")
            
            # Drop existing Bronze table if it exists
            self.connection_manager.drop_table(table_name)
            
            # Use SQL to join articles with page_summaries for location data
            # Bronze layer principle: Load data AS-IS with NO transformations
            if sample_size:
                create_query = f"""
                CREATE TABLE {table_name} AS
                SELECT 
                    a.*,
                    ps.best_city,
                    ps.best_county,
                    ps.best_state
                FROM wiki_db.articles a
                LEFT JOIN wiki_db.page_summaries ps ON a.pageid = ps.page_id
                LIMIT {sample_size}
                """
            else:
                create_query = f"""
                CREATE TABLE {table_name} AS
                SELECT 
                    a.*,
                    ps.best_city,
                    ps.best_county,
                    ps.best_state
                FROM wiki_db.articles a
                LEFT JOIN wiki_db.page_summaries ps ON a.pageid = ps.page_id
                """
            
            conn.execute(create_query)
            
            # Get record count for metrics
            self.records_ingested = self.connection_manager.count_records(table_name)
            
            self.logger.info(f"Loaded {self.records_ingested} raw Wikipedia articles into {table_name}")
            
            return BronzeMetadata(
                table_name=table_name,
                source_path=db_path.absolute(),
                record_count=self.records_ingested,
                entity_type=self._get_entity_type()
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
            source_path=db_path.absolute(),
            record_count=self.records_ingested,
            entity_type=self._get_entity_type()
        )
    
    def _get_entity_type(self) -> str:
        """Get the entity type for this ingester.
        
        Returns:
            Entity type string
        """
        return "wikipedia"