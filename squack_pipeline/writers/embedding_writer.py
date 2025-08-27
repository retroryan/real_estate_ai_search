"""Embedding writer for storing embedded nodes to Parquet."""

from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import numpy as np
from llama_index.core.schema import TextNode

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.writers.parquet_writer import ParquetWriter
from squack_pipeline.models import EmbeddingBatch, EmbeddingMetadata
from squack_pipeline.models.duckdb_models import TableIdentifier
from squack_pipeline.utils.logging import PipelineLogger, log_execution_time


class EmbeddingWriter(ParquetWriter):
    """Writer for embedded nodes with vector storage support."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize embedding writer."""
        super().__init__(settings)
        self.embedding_dimension: Optional[int] = None
        
    @log_execution_time
    def write_embedded_nodes(
        self, 
        nodes: List[TextNode], 
        output_path: Path,
        include_embeddings: bool = True
    ) -> Path:
        """Write embedded nodes to Parquet format.
        
        Args:
            nodes: List of TextNodes with embeddings
            output_path: Path where the Parquet file should be written
            include_embeddings: Whether to include embedding vectors
            
        Returns:
            Path to the written Parquet file
        """
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        if not nodes:
            self.logger.warning("No nodes to write")
            return output_path
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create temporary table for nodes with safe identifier
        temp_table_name = f"temp_embeddings_{int(np.random.rand() * 1e9)}"
        temp_table = TableIdentifier(name=temp_table_name)
        
        try:
            # Prepare node data for insertion
            node_records = self._prepare_node_records(nodes, include_embeddings)
            
            # Create table schema based on first node
            schema = self._create_embedding_schema(nodes[0], include_embeddings)
            
            # Create temporary table
            create_query = f"""
            CREATE TABLE {temp_table.qualified_name} (
                {', '.join([f'{col} {dtype}' for col, dtype in schema.items()])}
            )
            """
            self.connection.execute(create_query)
            
            # Insert node data
            if include_embeddings:
                # For embeddings, we'll store as array or JSON
                insert_query = f"""
                INSERT INTO {temp_table.qualified_name} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
            else:
                insert_query = f"""
                INSERT INTO {temp_table.qualified_name} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
            
            self.connection.executemany(insert_query, node_records)
            
            # Write to Parquet
            parquet_path = self.write(temp_table.name, output_path)
            
            # Log statistics
            node_count = len(nodes)
            embedded_count = sum(1 for n in nodes if n.embedding is not None)
            self.logger.success(
                f"Wrote {node_count} nodes ({embedded_count} with embeddings) to {output_path}"
            )
            
            # Clean up temporary table
            self.connection.execute(f"DROP TABLE IF EXISTS {temp_table.qualified_name}")
            
            return parquet_path
            
        except Exception as e:
            # Clean up on error
            self.connection.execute(f"DROP TABLE IF EXISTS {temp_table.qualified_name}")
            self.logger.error(f"Failed to write embedded nodes: {e}")
            raise
    
    def _prepare_node_records(
        self, 
        nodes: List[TextNode],
        include_embeddings: bool
    ) -> List[tuple]:
        """Convert TextNodes to records for database insertion.
        
        Args:
            nodes: List of TextNodes
            include_embeddings: Whether to include embeddings
            
        Returns:
            List of tuples ready for insertion
        """
        records = []
        
        for idx, node in enumerate(nodes):
            # Extract metadata
            metadata = node.metadata or {}
            property_id = metadata.get("property_id", "")
            listing_id = metadata.get("listing_id", "")
            chunk_index = metadata.get("chunk_index", idx)
            city = metadata.get("city", "")
            property_type = metadata.get("property_type", "")
            
            # Get text content
            text_content = node.text[:5000] if node.text else ""  # Truncate if too long
            text_length = len(node.text) if node.text else 0
            
            # Get embedding info
            has_embedding = node.embedding is not None
            embedding_dim = len(node.embedding) if has_embedding else 0
            
            if include_embeddings and has_embedding:
                # Convert embedding to JSON string for storage
                embedding_json = json.dumps(node.embedding)
                record = (
                    node.id_,
                    property_id,
                    listing_id,
                    chunk_index,
                    text_content,
                    text_length,
                    city,
                    property_type,
                    embedding_dim,
                    embedding_json
                )
            else:
                record = (
                    node.id_,
                    property_id,
                    listing_id,
                    chunk_index,
                    text_content,
                    text_length,
                    city,
                    property_type,
                    embedding_dim
                )
            
            records.append(record)
            
            # Track embedding dimension
            if has_embedding and self.embedding_dimension is None:
                self.embedding_dimension = embedding_dim
        
        return records
    
    def _create_embedding_schema(
        self, 
        sample_node: TextNode,
        include_embeddings: bool
    ) -> Dict[str, str]:
        """Create schema for embedding table based on sample node.
        
        Args:
            sample_node: Sample TextNode to infer schema
            include_embeddings: Whether to include embedding column
            
        Returns:
            Dictionary mapping column names to DuckDB types
        """
        schema = {
            "node_id": "VARCHAR",
            "property_id": "VARCHAR",
            "listing_id": "VARCHAR", 
            "chunk_index": "INTEGER",
            "text_content": "VARCHAR",
            "text_length": "INTEGER",
            "city": "VARCHAR",
            "property_type": "VARCHAR",
            "embedding_dimension": "INTEGER"
        }
        
        if include_embeddings:
            # Store embeddings as JSON for now (could use array type)
            schema["embedding_vector"] = "JSON"
        
        return schema
    
    def write_embedding_metadata(
        self,
        nodes: List[TextNode],
        metadata_path: Path
    ) -> Path:
        """Write embedding metadata file.
        
        Args:
            nodes: List of embedded nodes
            metadata_path: Path for metadata JSON file
            
        Returns:
            Path to metadata file
        """
        # Calculate statistics
        total_nodes = len(nodes)
        embedded_nodes = sum(1 for n in nodes if n.embedding is not None)
        
        # Get unique properties
        property_ids = set()
        for node in nodes:
            if node.metadata and "property_id" in node.metadata:
                property_ids.add(node.metadata["property_id"])
        
        # Get embedding dimensions
        dimensions = []
        for node in nodes:
            if node.embedding is not None:
                dimensions.append(len(node.embedding))
        
        avg_dimension = np.mean(dimensions) if dimensions else 0
        
        metadata = {
            "total_nodes": total_nodes,
            "embedded_nodes": embedded_nodes,
            "embedding_rate": embedded_nodes / total_nodes if total_nodes > 0 else 0,
            "unique_properties": len(property_ids),
            "average_dimension": avg_dimension,
            "embedding_provider": self.settings.embedding.provider.value,
            "chunk_method": self.settings.processing.chunk_method.value,
            "chunk_size": self.settings.processing.chunk_size,
            "metadata_version": self.settings.metadata_version
        }
        
        # Write metadata
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self.logger.info(f"Wrote embedding metadata to {metadata_path}")
        
        return metadata_path
    
    def get_output_schema(self) -> Dict[str, str]:
        """Get the expected output schema for embeddings.
        
        Returns:
            Dictionary mapping column names to types
        """
        return {
            "node_id": "VARCHAR",
            "property_id": "VARCHAR",
            "listing_id": "VARCHAR",
            "chunk_index": "INTEGER",
            "text_content": "VARCHAR",
            "text_length": "INTEGER",
            "city": "VARCHAR",
            "property_type": "VARCHAR",
            "embedding_dimension": "INTEGER",
            "embedding_vector": "JSON"  # Or FLOAT[] if using array type
        }
    
    def get_partition_columns(self) -> List[str]:
        """Get columns to use for partitioning embeddings.
        
        Returns:
            List of column names for partitioning
        """
        # Partition embeddings by city for locality
        return ["city"]
    
    @log_execution_time
    def write_embedding_batch(
        self,
        nodes: List[TextNode],
        output_path: Path,
        provider: str,
        model: str,
        processing_time: float,
        chunk_method: Optional[str] = None,
        chunk_size: Optional[int] = None,
        batch_size: int = 50
    ) -> Path:
        """Write embedded nodes using Pydantic models for validation.
        
        Args:
            nodes: List of TextNodes with embeddings
            output_path: Path where the Parquet file should be written  
            provider: Embedding provider name
            model: Model name used
            processing_time: Processing time in seconds
            chunk_method: Text chunking method used
            chunk_size: Chunk size if chunking was used
            batch_size: Batch size used for processing
            
        Returns:
            Path to the written Parquet file
        """
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
            
        if not nodes:
            self.logger.warning("No nodes to write")
            return output_path
        
        # Create Pydantic embedding batch
        embedding_batch = EmbeddingBatch.from_text_nodes(
            nodes=nodes,
            provider=provider,
            model=model,
            processing_time=processing_time,
            chunk_method=chunk_method,
            chunk_size=chunk_size,
            batch_size=batch_size
        )
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to Parquet-ready data
        parquet_data = embedding_batch.to_parquet_data()
        
        # Create temporary table with safe identifier
        temp_table_name = f"temp_embeddings_{int(np.random.rand() * 1e9)}"
        temp_table = TableIdentifier(name=temp_table_name)
        
        try:
            # Create table with proper schema
            create_sql = f"""
            CREATE TABLE {temp_table.qualified_name} (
                node_id VARCHAR,
                text VARCHAR,
                embedding JSON,
                source_id VARCHAR,
                source_type VARCHAR,
                chunk_index INTEGER,
                created_at VARCHAR,
                metadata VARCHAR
            )
            """
            self.connection.execute(create_sql)
            
            # Insert data
            for i in range(len(parquet_data['node_id'])):
                insert_sql = f"""
                INSERT INTO {temp_table.qualified_name} VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?
                )
                """
                self.connection.execute(insert_sql, [
                    parquet_data['node_id'][i],
                    parquet_data['text'][i],
                    json.dumps(parquet_data['embedding'][i]) if parquet_data['embedding'][i] else None,
                    parquet_data['source_id'][i],
                    parquet_data['source_type'][i],
                    parquet_data['chunk_index'][i],
                    parquet_data['created_at'][i],
                    parquet_data['metadata'][i]
                ])
            
            # Write to Parquet
            compression = str(self.settings.parquet.compression)
            copy_sql = f"""
            COPY (SELECT * FROM {temp_table.qualified_name})
            TO '{output_path}' 
            (FORMAT PARQUET, COMPRESSION '{compression}')
            """
            self.connection.execute(copy_sql)
            
            # Update metadata with file info
            file_size = output_path.stat().st_size if output_path.exists() else 0
            embedding_batch.metadata.output_file_path = str(output_path)
            embedding_batch.metadata.file_size_bytes = file_size
            
            # Write metadata file
            metadata_path = output_path.with_suffix('.metadata.json')
            embedding_batch.save_metadata(metadata_path)
            
            self.logger.success(f"Wrote {len(nodes)} embedded nodes to {output_path}")
            self.logger.info(f"File size: {file_size / (1024*1024):.2f} MB")
            self.logger.info(f"Embedding dimensions: {embedding_batch.metadata.dimension}")
            self.logger.info(f"Success rate: {embedding_batch.metadata.success_rate:.2%}")
            
            return output_path
            
        finally:
            # Clean up temporary table
            try:
                self.connection.execute(f"DROP TABLE IF EXISTS {temp_table.qualified_name}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup temporary table: {e}")