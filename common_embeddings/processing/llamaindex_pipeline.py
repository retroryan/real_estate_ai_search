"""
LlamaIndex-optimized embedding pipeline.

Implements LlamaIndex best practices:
- Node-centric processing as atomic units
- Selective data retrieval patterns
- Efficient storage and indexing strategies
- Proper document/node relationship management
"""

from typing import List, Dict, Any, Optional, Generator, Iterator
from datetime import datetime
from pathlib import Path

from llama_index.core import Document
from llama_index.core.schema import TextNode
from llama_index.core.node_parser import NodeParser

from ..models import (
    Config, EntityType, SourceType, ProcessingResult, 
    PipelineStatistics, EmbeddingGenerationError
)
from ..models.processing import ProcessingChunkMetadata
from ..embedding.factory import EmbeddingFactory
from ..processing.chunking import TextChunker
from ..processing.node_processor import NodeProcessor
from ..processing.batch_processor import BatchProcessor
from ..storage.chromadb_store import ChromaDBStore
from ..services import MetadataFactory, BatchStorageManager
from ..utils.logging import get_logger, PerformanceLogger
from ..utils.hashing import hash_text

logger = get_logger(__name__)


class LlamaIndexOptimizedPipeline:
    """
    Embedding pipeline optimized for LlamaIndex best practices.
    
    Key optimizations:
    1. Node-centric processing (Nodes as atomic units)
    2. Lazy document loading for memory efficiency
    3. Selective processing based on metadata filters
    4. Proper node relationship management
    5. Optimized storage patterns
    """
    
    def __init__(self, config: Config, store_embeddings: bool = True):
        """
        Initialize optimized pipeline.
        
        Args:
            config: Pipeline configuration
            store_embeddings: Whether to store embeddings to ChromaDB
        """
        self.config = config
        self.store_embeddings = store_embeddings
        
        # Core components
        self.embed_model = None
        self.model_identifier = None
        self.node_processor = None
        self.batch_processor = None
        
        # Storage services
        self.store = None
        self.metadata_factory = None
        self.batch_storage = None
        
        # Performance tracking
        self.stats = {
            "documents_processed": 0,
            "nodes_created": 0,
            "embeddings_generated": 0,
            "embeddings_stored": 0,
            "errors": 0
        }
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize pipeline components following LlamaIndex patterns."""
        logger.info("Initializing LlamaIndex-optimized pipeline components")
        
        # Create embedding model
        try:
            self.embed_model, self.model_identifier = EmbeddingFactory.create_provider(self.config)
            logger.info(f"Initialized embedding model: {self.model_identifier}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise
        
        # Create text chunker (returns LlamaIndex NodeParser)
        chunker = TextChunker(
            self.config.chunking,
            self.embed_model if self.config.chunking.method.value == "semantic" else None
        )
        node_parser = chunker.parser
        
        # Create node processor for LlamaIndex best practices
        self.node_processor = NodeProcessor(node_parser)
        logger.info(f"Initialized node processor with method: {self.config.chunking.method}")
        
        # Create batch processor for embeddings
        self.batch_processor = BatchProcessor(
            self.config.processing,
            self.embed_model,
            progress_callback=self._progress_callback
        )
        logger.info("Initialized batch processor")
        
        # Initialize storage services if needed
        if self.store_embeddings:
            self._initialize_storage_services()
    
    def _initialize_storage_services(self):
        """Initialize storage-related services."""
        self.store = ChromaDBStore(self.config.chromadb)
        self.metadata_factory = MetadataFactory(self.config, self.model_identifier)
        self.batch_storage = BatchStorageManager(
            store=self.store,
            batch_size=self.config.processing.batch_size,
            auto_flush=True
        )
        logger.info("Initialized ChromaDB store and modular services for embedding storage")
    
    def _progress_callback(self, current: int, total: int):
        """Progress callback for batch processor."""
        if self.config.processing.show_progress:
            percentage = (current / total * 100) if total > 0 else 0
            logger.info(f"Progress: {current}/{total} ({percentage:.1f}%)")
    
    def process_documents_optimized(
        self,
        documents: List[Document],
        entity_type: EntityType,
        source_type: SourceType,
        source_file: str,
        collection_name: Optional[str] = None,
        force_recreate: bool = False,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> Generator[ProcessingResult, None, None]:
        """
        Process documents using LlamaIndex best practices.
        
        Implements:
        - Node-centric processing
        - Selective data retrieval
        - Efficient relationship management
        
        Args:
            documents: List of LlamaIndex Document objects
            entity_type: Type of entity being processed
            source_type: Type of data source
            source_file: Path to source file
            collection_name: Optional ChromaDB collection name
            force_recreate: Whether to recreate the collection
            metadata_filter: Optional filter for selective processing
            
        Yields:
            ProcessingResult objects with enhanced node information
        """
        logger.info(f"Processing {len(documents)} documents with LlamaIndex optimization")
        
        with PerformanceLogger(f"Processing {len(documents)} documents") as perf:
            # Apply selective data retrieval if filter provided
            if metadata_filter:
                documents = self._filter_documents(documents, metadata_filter)
                logger.info(f"After filtering: {len(documents)} documents remain")
            
            # Process documents to nodes (atomic units)
            logger.info("Converting documents to nodes...")
            nodes = self.node_processor.process_documents_to_nodes(
                documents, entity_type, source_type
            )
            
            if not nodes:
                logger.warning("No nodes created from documents")
                return
            
            self.stats["documents_processed"] = len(documents)
            self.stats["nodes_created"] = len(nodes)
            
            # Setup storage collection if needed
            if self.store_embeddings and collection_name and self.batch_storage:
                self.batch_storage.prepare_collection(
                    collection_name=collection_name,
                    entity_type=entity_type,
                    source_type=source_type,
                    model_identifier=self.model_identifier,
                    force_recreate=force_recreate
                )
                logger.info(f"Prepared collection: {collection_name}")
            
            # Process nodes in batches for embeddings
            logger.info("Generating embeddings from nodes...")
            processed_count = 0
            
            # Convert nodes to text chunks for batch processor
            node_texts = [(node.text, self._node_to_chunk_metadata(node)) for node in nodes]
            
            # Process through batch processor
            for embedding, chunk_metadata in self.batch_processor.process_in_batches(node_texts):
                if embedding is None:
                    self.stats["errors"] += 1
                    continue
                
                # Find corresponding node
                node = nodes[processed_count] if processed_count < len(nodes) else None
                if not node:
                    logger.error(f"Node mismatch at index {processed_count}")
                    self.stats["errors"] += 1
                    continue
                
                # Create metadata using metadata factory
                if self.metadata_factory:
                    storage_metadata = self.metadata_factory.create_metadata(
                        chunk_metadata.to_dict(),
                        entity_type,
                        source_type,
                        source_file,
                        embedding
                    )
                else:
                    # Fallback metadata
                    from ..models import BaseMetadata
                    storage_metadata = BaseMetadata(
                        entity_type=entity_type,
                        source_type=source_type,
                        source_file=source_file,
                        embedding_model=self.model_identifier,
                        embedding_provider=self.config.embedding.provider,
                        embedding_dimension=len(embedding),
                        text_hash=chunk_metadata.text_hash
                    )
                
                # Store using batch storage if enabled
                if self.store_embeddings and collection_name and self.batch_storage:
                    self.batch_storage.add_embedding(
                        embedding=embedding,
                        text=node.text,
                        metadata=storage_metadata,
                        text_hash=chunk_metadata.text_hash,
                        chunk_index=chunk_metadata.chunk_index
                    )
                
                # Create enhanced ProcessingResult with node information
                result = ProcessingResult(
                    embedding=embedding,
                    metadata=storage_metadata,
                    entity_type=entity_type,
                    source_type=source_type,
                    source_file=source_file,
                    # Enhanced with node information
                    node_id=node.node_id,
                    relationships=dict(node.relationships) if node.relationships else {},
                    text=node.text
                )
                
                yield result
                
                processed_count += 1
                self.stats["embeddings_generated"] = processed_count
            
            # Finalize storage
            if self.store_embeddings and collection_name and self.batch_storage:
                storage_stats = self.batch_storage.finalize()
                self.stats["embeddings_stored"] = storage_stats.embeddings_stored
                if storage_stats.errors > 0:
                    logger.warning(f"Storage completed with {storage_stats.errors} errors")
            
            perf.add_metric("nodes_created", self.stats["nodes_created"])
            perf.add_metric("embeddings_generated", processed_count)
            perf.add_metric("errors", self.stats["errors"])
    
    def process_documents_lazy(
        self,
        document_iterator: Iterator[Document],
        entity_type: EntityType,
        source_type: SourceType,
        source_file: str,
        collection_name: Optional[str] = None,
        batch_size: int = 50
    ) -> Generator[List[ProcessingResult], None, None]:
        """
        Process documents lazily for memory efficiency.
        
        Following LlamaIndex best practice: Efficient memory usage
        
        Args:
            document_iterator: Lazy iterator of documents
            entity_type: Entity type
            source_type: Source type
            source_file: Source file path
            collection_name: Collection name for storage
            batch_size: Documents per batch
            
        Yields:
            Batches of ProcessingResult objects
        """
        batch = []
        
        for document in document_iterator:
            batch.append(document)
            
            if len(batch) >= batch_size:
                # Process batch
                results = list(self.process_documents_optimized(
                    batch, entity_type, source_type, source_file, collection_name
                ))
                yield results
                batch = []
        
        # Process remaining documents
        if batch:
            results = list(self.process_documents_optimized(
                batch, entity_type, source_type, source_file, collection_name
            ))
            yield results
    
    def _filter_documents(
        self, 
        documents: List[Document], 
        metadata_filter: Dict[str, Any]
    ) -> List[Document]:
        """
        Apply selective data retrieval filter.
        
        Following LlamaIndex best practice: Selective data retrieval
        
        Args:
            documents: Documents to filter
            metadata_filter: Filter criteria
            
        Returns:
            Filtered documents
        """
        filtered = []
        
        for doc in documents:
            passes_filter = True
            
            for key, expected_value in metadata_filter.items():
                if key not in doc.metadata:
                    passes_filter = False
                    break
                
                actual_value = doc.metadata[key]
                if isinstance(expected_value, list):
                    if actual_value not in expected_value:
                        passes_filter = False
                        break
                elif actual_value != expected_value:
                    passes_filter = False
                    break
            
            if passes_filter:
                filtered.append(doc)
        
        return filtered
    
    def _node_to_chunk_metadata(self, node: TextNode) -> ProcessingChunkMetadata:
        """
        Convert TextNode to ProcessingChunkMetadata.
        
        Args:
            node: TextNode to convert
            
        Returns:
            ProcessingChunkMetadata object
        """
        return ProcessingChunkMetadata.from_combined_dict(
            document_metadata=node.metadata,
            chunk_metadata={
                'chunk_index': node.metadata.get('chunk_index', 0),
                'chunk_total': node.metadata.get('chunk_total', 1),
                'text_hash': hash_text(node.text),
                'node_id': node.node_id
            },
            source_doc_id=getattr(node, 'ref_doc_id', None)
        )
    
    def get_statistics(self) -> PipelineStatistics:
        """
        Get enhanced pipeline statistics.
        
        Returns:
            PipelineStatistics with node-level metrics
        """
        processor_stats = self.batch_processor.get_statistics() if self.batch_processor else None
        processor_stats_dict = processor_stats.model_dump() if processor_stats else {}
        
        return PipelineStatistics(
            documents_processed=self.stats.get("documents_processed", 0),
            chunks_created=self.stats.get("nodes_created", 0),  # Nodes are chunks in LlamaIndex
            embeddings_generated=self.stats.get("embeddings_generated", 0),
            errors=self.stats.get("errors", 0),
            model_identifier=self.model_identifier,
            chunking_method=self.config.chunking.method.value,
            batch_size=self.config.processing.batch_size,
            processor_stats=processor_stats_dict
        )