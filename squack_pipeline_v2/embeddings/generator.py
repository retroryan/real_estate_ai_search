"""Embedding generator that reads from Gold tables and stores embeddings in DuckDB.

Following DuckDB best practices:
- Reads embedding_text via SQL
- Batch processes embeddings
- Stores results back in DuckDB
- No row-by-row processing
"""

from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime
from squack_pipeline_v2.core.connection import DuckDBConnectionManager as ConnectionManager
from squack_pipeline_v2.embeddings.providers import create_provider, EmbeddingProvider
from squack_pipeline_v2.core.logging import log_stage

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for Gold layer data.
    
    Reads embedding_text from Gold tables, generates embeddings,
    and stores them back in DuckDB for further processing.
    """
    
    def __init__(
        self,
        connection_manager: ConnectionManager,
        provider: EmbeddingProvider
    ):
        """Initialize generator.
        
        Args:
            connection_manager: DuckDB connection manager
            provider: Embedding provider instance
        """
        self.connection_manager = connection_manager
        self.provider = provider
        self.embeddings_generated = 0
    
    @log_stage("Embeddings: Generate for entity")
    def generate_for_entity(
        self,
        entity_type: str,
        input_table: str,
        output_table: str,
        id_column: str,
        text_column: str = "embedding_text",
        batch_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate embeddings for an entity type.
        
        Args:
            entity_type: Type of entity (property, neighborhood, wikipedia)
            input_table: Gold table with embedding_text
            output_table: Table to store embeddings
            id_column: Primary key column name
            text_column: Column containing text to embed
            batch_size: Override provider batch size
            
        Returns:
            Generation statistics
        """
        if not batch_size:
            batch_size = self.provider.get_batch_size()
        
        # Create embeddings table
        self._create_embeddings_table(output_table, id_column)
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM {input_table}"
        total_records = self.connection_manager.execute(count_query).fetchone()[0]
        
        logger.info(f"Generating embeddings for {total_records} {entity_type} records")
        
        # Process in batches
        processed = 0
        errors = 0
        
        offset = 0
        while offset < total_records:
            # Fetch batch via SQL
            batch_query = f"""
            SELECT {id_column}, {text_column}
            FROM {input_table}
            ORDER BY {id_column}
            LIMIT {batch_size}
            OFFSET {offset}
            """
            
            batch_results = self.connection_manager.execute(batch_query).fetchall()
            
            if not batch_results:
                break
            
            # Extract IDs and texts, keeping them paired
            id_text_pairs = [(row[0], row[1]) for row in batch_results if row[1]]  # Skip nulls
            
            if not id_text_pairs:
                offset += batch_size
                continue
            
            # Separate after filtering
            ids = [pair[0] for pair in id_text_pairs]
            texts = [pair[1] for pair in id_text_pairs]
            
            try:
                # Generate embeddings
                response = self.provider.generate_embeddings(texts)
                
                # Insert embeddings into DuckDB
                self._store_embeddings(
                    output_table,
                    id_column,
                    ids,
                    response.embeddings
                )
                
                processed += len(id_text_pairs)
                self.embeddings_generated += len(id_text_pairs)
                
                if processed % 100 == 0:
                    logger.info(f"Processed {processed}/{total_records} embeddings")
                    
            except Exception as e:
                logger.error(f"Error generating embeddings for batch: {e}")
                errors += len(id_text_pairs)
            
            offset += batch_size
        
        # Create indexes for similarity search
        self._create_embedding_index(output_table)
        
        stats = {
            "entity_type": entity_type,
            "total_records": total_records,
            "embeddings_generated": processed,
            "errors": errors,
            "dimension": self.provider.dimension,
            "model": self.provider.model_name
        }
        
        logger.info(f"Completed embeddings for {entity_type}: {processed}/{total_records}")
        
        return stats
    
    def _create_embeddings_table(self, table_name: str, id_column: str) -> None:
        """Create table to store embeddings.
        
        Args:
            table_name: Name of embeddings table
            id_column: Primary key column name
        """
        # Drop if exists
        drop_query = f"DROP TABLE IF EXISTS {table_name}"
        self.connection_manager.execute(drop_query)
        
        # Create new table
        create_query = f"""
        CREATE TABLE {table_name} (
            {id_column} VARCHAR PRIMARY KEY,
            embedding DOUBLE[{self.provider.dimension}],
            model_name VARCHAR,
            dimension INTEGER,
            generated_at TIMESTAMP
        )
        """
        self.connection_manager.execute(create_query)
    
    def _store_embeddings(
        self,
        table_name: str,
        id_column: str,
        ids: List[str],
        embeddings: List[List[float]]
    ) -> None:
        """Store embeddings in DuckDB.
        
        Args:
            table_name: Embeddings table
            id_column: ID column name  
            ids: List of record IDs
            embeddings: List of embedding vectors
        """
        # Prepare batch insert
        current_time = datetime.now()
        
        for id_val, embedding in zip(ids, embeddings):
            # Convert embedding to array literal
            embedding_str = f"[{','.join(map(str, embedding))}]"
            
            insert_query = f"""
            INSERT OR REPLACE INTO {table_name} (
                {id_column},
                embedding,
                model_name,
                dimension,
                generated_at
            ) VALUES (
                $1,
                $2::DOUBLE[{self.provider.dimension}],
                $3,
                $4,
                $5
            )
            """
            
            self.connection_manager.execute(
                insert_query,
                [
                    id_val,
                    embedding_str,
                    self.provider.model_name,
                    self.provider.dimension,
                    current_time
                ]
            )
    
    def _create_embedding_index(self, table_name: str) -> None:
        """Create index for similarity search (placeholder for future).
        
        Args:
            table_name: Table with embeddings
        """
        # DuckDB doesn't have native vector indexes yet
        # This is a placeholder for when it's added
        logger.debug(f"Vector indexes not yet supported in DuckDB for {table_name}")
    
    @log_stage("Embeddings: Generate all")
    def generate_all_embeddings(self) -> Dict[str, Any]:
        """Generate embeddings for all entity types.
        
        Returns:
            Combined statistics
        """
        stats = {}
        
        # Define entity configurations
        entities = [
            {
                "entity_type": "property",
                "input_table": "gold_properties",
                "output_table": "embeddings_properties",
                "id_column": "listing_id"
            },
            {
                "entity_type": "neighborhood",
                "input_table": "gold_neighborhoods",
                "output_table": "embeddings_neighborhoods",
                "id_column": "neighborhood_id"
            },
            {
                "entity_type": "wikipedia",
                "input_table": "gold_wikipedia",
                "output_table": "embeddings_wikipedia",
                "id_column": "page_id"
            }
        ]
        
        for entity_config in entities:
            # Check if input table exists
            from squack_pipeline_v2.core.table_identifier import TableIdentifier
            input_table_id = TableIdentifier(name=entity_config["input_table"])
            if self.connection_manager.table_exists(input_table_id):
                entity_stats = self.generate_for_entity(**entity_config)
                stats[entity_config["entity_type"]] = entity_stats
            else:
                logger.warning(f"Skipping {entity_config['entity_type']}: table {entity_config['input_table']} not found")
        
        return {
            "total_embeddings": self.embeddings_generated,
            "entities": stats,
            "model": self.provider.model_name,
            "dimension": self.provider.dimension
        }
    
    def verify_embeddings(self, table_name: str) -> Dict[str, Any]:
        """Verify embeddings were generated correctly.
        
        Args:
            table_name: Embeddings table to verify
            
        Returns:
            Verification statistics
        """
        # Check count
        count_query = f"SELECT COUNT(*) FROM {table_name}"
        count = self.connection_manager.execute(count_query).fetchone()[0]
        
        # Check dimensions
        dim_query = f"""
        SELECT 
            MIN(dimension) as min_dim,
            MAX(dimension) as max_dim,
            AVG(dimension) as avg_dim
        FROM {table_name}
        """
        dim_result = self.connection_manager.execute(dim_query).fetchone()
        
        # Sample an embedding to check structure
        sample_query = f"""
        SELECT embedding
        FROM {table_name}
        LIMIT 1
        """
        sample = self.connection_manager.execute(sample_query).fetchone()
        
        return {
            "table": table_name,
            "count": count,
            "dimension": {
                "min": dim_result[0] if dim_result else None,
                "max": dim_result[1] if dim_result else None,
                "avg": dim_result[2] if dim_result else None
            },
            "sample_length": len(sample[0]) if sample else 0
        }