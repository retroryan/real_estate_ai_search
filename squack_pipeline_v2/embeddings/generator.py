"""Embedding generator using Gold layer extension and DuckDB Relation API.

Following medallion architecture:
- Gold tables contain ALL business-ready data including embeddings
- No separate embedding tables
- Uses DuckDB Relation API with lazy evaluation
- Fixed 1024 dimension with current LlamaIndex + Voyage integration
"""

from typing import List, Dict, Any
import logging
from datetime import datetime

from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.embeddings.providers import EmbeddingProvider
from squack_pipeline_v2.embeddings.metadata import EmbeddingMetadata
from squack_pipeline_v2.core.logging import log_stage

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for Gold layer data using DuckDB Relation API.
    
    Medallion architecture compliance:
    - Updates Gold tables directly with embedding vectors
    - No separate embedding tables (single source of truth)
    - Uses DuckDB Relation API for efficient batch processing
    """
    
    def __init__(
        self,
        connection_manager: DuckDBConnectionManager,
        provider: EmbeddingProvider
    ):
        """Initialize generator.
        
        Args:
            connection_manager: DuckDB connection manager
            provider: Embedding provider instance
        """
        self.connection_manager = connection_manager
        self.provider = provider
    
    @log_stage("Embeddings: Generate for Gold table")
    def generate_for_gold_table(
        self,
        entity_type: str,
        gold_table: str,
        id_column: str,
        text_column: str = "embedding_text"
    ) -> EmbeddingMetadata:
        """Generate embeddings for records in Gold table using Relation API.
        
        Args:
            entity_type: Type of entity (property, neighborhood, wikipedia)
            gold_table: Gold table name
            id_column: Primary key column name
            text_column: Column containing text to embed
            
        Returns:
            Embedding generation metadata
        """
        # Get connection for Relation API
        conn = self.connection_manager.get_connection()
        
        # Use lazy evaluation to select records needing embeddings
        records_needing_embeddings = conn.sql(f"""
            SELECT {id_column}, {text_column}
            FROM {gold_table}
            WHERE embedding_vector IS NULL
            AND {text_column} IS NOT NULL
            AND LENGTH(TRIM({text_column})) > 0
            ORDER BY {id_column}
        """)
        
        # Materialize the data for processing
        embedding_batch = records_needing_embeddings.fetchall()
        
        if not embedding_batch:
            logger.info(f"No records need embeddings in {gold_table}")
            
            # Get total record count for skipped calculation
            total_records = self.connection_manager.count_records(gold_table)
            
            return EmbeddingMetadata(
                entity_type=entity_type,
                gold_table=gold_table,
                records_processed=total_records,
                embeddings_generated=0,
                records_skipped=total_records
            )
        
        logger.info(f"Generating embeddings for {len(embedding_batch)} records in {gold_table}")
        
        # Extract IDs and texts for embedding generation
        ids = [row[0] for row in embedding_batch]
        texts = [row[1] for row in embedding_batch]
        
        # Generate embeddings using current LlamaIndex + Voyage integration
        response = self.provider.generate_embeddings(texts)
        
        # Update Gold table with embeddings using Relation API batch operation
        self._update_gold_table_with_embeddings(
            gold_table,
            id_column,
            ids,
            response.embeddings
        )
        
        # Get final counts
        total_records = self.connection_manager.count_records(gold_table)
        records_with_embeddings = conn.sql(f"""
            SELECT COUNT(*) 
            FROM {gold_table} 
            WHERE embedding_vector IS NOT NULL
        """).fetchone()[0]
        
        logger.info(f"Generated {len(response.embeddings)} embeddings for {entity_type}")
        
        return EmbeddingMetadata(
            entity_type=entity_type,
            gold_table=gold_table,
            records_processed=total_records,
            embeddings_generated=len(response.embeddings),
            records_skipped=total_records - len(response.embeddings),
            embedding_dimension=self.provider.dimension,
            embedding_model=self.provider.model_name
        )
    
    def _update_gold_table_with_embeddings(
        self,
        gold_table: str,
        id_column: str,
        ids: List[str],
        embeddings: List[List[float]]
    ) -> None:
        """Update Gold table with embeddings using DuckDB batch operations.
        
        Args:
            gold_table: Gold table name
            id_column: ID column name
            ids: List of record IDs
            embeddings: List of embedding vectors
        """
        conn = self.connection_manager.get_connection()
        current_time = datetime.now()
        
        # Use DuckDB's efficient batch update with parameterized queries
        for id_val, embedding in zip(ids, embeddings):
            # Convert embedding to DuckDB array format
            embedding_array = f"[{','.join(map(str, embedding))}]"
            
            # Use parameterized update query for safety
            update_query = f"""
            UPDATE {gold_table}
            SET 
                embedding_vector = $1::DOUBLE[1024],
                embedding_generated_at = $2
            WHERE {id_column} = $3
            """
            
            self.connection_manager.execute(
                update_query,
                [embedding_array, current_time, id_val]
            )
    
    @log_stage("Embeddings: Generate all Gold tables")
    def generate_all_embeddings(self) -> Dict[str, EmbeddingMetadata]:
        """Generate embeddings for all Gold tables.
        
        Returns:
            Dictionary of embedding metadata by entity type
        """
        results = {}
        
        # Define Gold table configurations (medallion architecture)
        gold_configs = [
            {
                "entity_type": "property",
                "gold_table": "gold_properties",
                "id_column": "listing_id"
            },
            {
                "entity_type": "neighborhood", 
                "gold_table": "gold_neighborhoods",
                "id_column": "neighborhood_id"
            },
            {
                "entity_type": "wikipedia",
                "gold_table": "gold_wikipedia",
                "id_column": "page_id"
            }
        ]
        
        for config in gold_configs:
            # Check if Gold table exists
            if self.connection_manager.table_exists(config["gold_table"]):
                metadata = self.generate_for_gold_table(**config)
                results[config["entity_type"]] = metadata
            else:
                logger.warning(f"Skipping {config['entity_type']}: Gold table {config['gold_table']} not found")
        
        return results
    
    def verify_embeddings(self, gold_table: str) -> Dict[str, Any]:
        """Verify embeddings in Gold table using Relation API.
        
        Args:
            gold_table: Gold table to verify
            
        Returns:
            Verification statistics
        """
        conn = self.connection_manager.get_connection()
        
        # Use Relation API for verification queries
        stats_relation = conn.sql(f"""
            SELECT 
                COUNT(*) as total_records,
                COUNT(embedding_vector) as records_with_embeddings,
                COUNT(*) - COUNT(embedding_vector) as records_without_embeddings
            FROM {gold_table}
        """)
        
        stats = stats_relation.fetchone()
        
        return {
            "gold_table": gold_table,
            "total_records": stats[0],
            "records_with_embeddings": stats[1], 
            "records_without_embeddings": stats[2],
            "embedding_coverage": stats[1] / stats[0] if stats[0] > 0 else 0.0
        }