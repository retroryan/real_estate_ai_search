"""
Main embedding pipeline orchestrating the generation process.

Combines patterns from wiki_embed and real_estate_embed pipelines
with enhanced metadata tracking for correlation.
"""

from typing import List, Dict, Any, Optional, Generator, Tuple
from datetime import datetime
from pathlib import Path
import hashlib

from llama_index.core import Document

from .models import (
    Config,
    BaseMetadata,
    EntityType,
    SourceType,
    ProcessingResult,
    DocumentBatch,
    PipelineStatistics,
    EmbeddingGenerationError,
)
from .models.processing import ProcessingChunkMetadata  # Has from_combined_dict method
from .embedding.factory import EmbeddingFactory
from .processing.chunking import TextChunker
from .processing.batch_processor import BatchProcessor
from .storage.chromadb_store import ChromaDBStore
from .services import MetadataFactory, BatchStorageManager, BatchStorageStats
from .utils.logging import get_logger, PerformanceLogger
from .utils.hashing import hash_text


logger = get_logger(__name__)


class EmbeddingPipeline:
    """
    Main pipeline for generating embeddings with correlation metadata.
    
    Orchestrates the entire embedding generation process from documents
    to stored embeddings with comprehensive metadata.
    """
    
    def __init__(self, config: Config, store_embeddings: bool = True):
        """
        Initialize embedding pipeline.
        
        Args:
            config: Pipeline configuration
            store_embeddings: Whether to store embeddings to ChromaDB
        """
        self.config = config
        self.embed_model = None
        self.model_identifier = None
        self.chunker = None
        self.processor = None
        self.store_embeddings = store_embeddings
        self.store = None
        
        # Modular services
        self.metadata_factory = None
        self.batch_storage = None
        
        # Statistics
        self.stats = {
            "documents_processed": 0,
            "chunks_created": 0,
            "embeddings_generated": 0,
            "embeddings_stored": 0,
            "errors": 0
        }
        
        # Initialize components
        self._initialize_components()
        
        # Initialize storage services if storing embeddings
        if self.store_embeddings:
            self._initialize_storage_services()
    
    def _initialize_components(self):
        """Initialize pipeline components."""
        logger.info("Initializing embedding pipeline components")
        
        # Create embedding model
        try:
            self.embed_model, self.model_identifier = EmbeddingFactory.create_from_config(self.config)
            logger.info(f"Initialized embedding model: {self.model_identifier}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise
        
        # Create text chunker
        self.chunker = TextChunker(
            self.config.chunking,
            self.embed_model if self.config.chunking.method.value == "semantic" else None
        )
        logger.info(f"Initialized chunker with method: {self.config.chunking.method}")
        
        # Create batch processor
        self.processor = BatchProcessor(
            self.config.processing,
            self.embed_model,
            progress_callback=self._progress_callback
        )
        logger.info("Initialized batch processor")
    
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
    
    def process_documents(
        self,
        documents: List[Document],
        entity_type: EntityType,
        source_type: SourceType,
        source_file: str,
        collection_name: Optional[str] = None,
        force_recreate: bool = False
    ) -> Generator[ProcessingResult, None, None]:
        """
        Process documents to generate embeddings with structured metadata.
        
        Args:
            documents: List of LlamaIndex Document objects
            entity_type: Type of entity being processed
            source_type: Type of data source
            source_file: Path to source file
            collection_name: Optional ChromaDB collection name for storage
            force_recreate: Whether to recreate the collection
            
        Yields:
            ProcessingResult objects with embeddings and structured metadata
        """
        logger.info(f"Processing {len(documents)} documents of type {entity_type.value}")
        
        with PerformanceLogger(f"Processing {len(documents)} documents") as perf:
            # Process documents in batches for better progress visibility
            logger.info("Chunking documents...")
            all_chunks = []
            
            # Create progress indicator for chunking
            from .utils.progress import ProgressIndicator
            chunking_progress = ProgressIndicator(
                total=len(documents),
                operation="Chunking documents",
                show_console=True
            )
            
            # Process documents in batches for semantic chunking transparency
            batch_size = self.config.processing.document_batch_size
            total_batches = (len(documents) + batch_size - 1) // batch_size
            
            for batch_idx in range(0, len(documents), batch_size):
                batch_end = min(batch_idx + batch_size, len(documents))
                batch_docs = documents[batch_idx:batch_end]
                current_batch_num = (batch_idx // batch_size) + 1
                
                logger.info(f"Processing document batch {current_batch_num}/{total_batches} ({len(batch_docs)} documents)")
                
                # Process each document in the batch
                for i, doc in enumerate(batch_docs):
                    global_doc_idx = batch_idx + i
                    
                    # Semantic chunking can be slow, so show progress per document
                    logger.debug(f"Chunking document {global_doc_idx + 1}/{len(documents)}")
                    
                    chunks = self.chunker.chunk_text(
                        doc.text,
                        doc.metadata
                    )
                    
                    # Add document-level metadata to chunks using Pydantic model
                    for chunk_data in chunks:
                        # Create ProcessingChunkMetadata directly from ChunkData and document metadata
                        combined_metadata = ProcessingChunkMetadata(
                            source_doc_id=doc.metadata.get('id', hash_text(doc.text)[:8]),
                            chunk_index=chunk_data.chunk_index,
                            chunk_total=chunk_data.chunk_total,
                            text_hash=chunk_data.text_hash,
                            chunk_method=chunk_data.chunk_method,
                            parent_hash=chunk_data.parent_hash,
                            # Entity-specific fields from document metadata
                            listing_id=doc.metadata.get('listing_id'),
                            property_type=doc.metadata.get('property_type'),
                            source_file_index=doc.metadata.get('source_file_index'),
                            neighborhood_id=doc.metadata.get('neighborhood_id'),
                            neighborhood_name=doc.metadata.get('neighborhood_name'),
                            page_id=doc.metadata.get('page_id'),
                            article_id=doc.metadata.get('article_id'),
                            title=doc.metadata.get('title'),
                            start_position=chunk_data.start_position,
                            end_position=chunk_data.end_position,
                        )
                        all_chunks.append((chunk_data.text, combined_metadata))
                    
                    self.stats["documents_processed"] += 1
                    
                    # Update progress for each document
                    chunking_progress.update(global_doc_idx + 1)
                
                # Log batch completion
                logger.info(f"Completed batch {current_batch_num}/{total_batches} - Total chunks so far: {len(all_chunks)}")
            
            chunking_progress.complete()
            self.stats["chunks_created"] = len(all_chunks)
            logger.info(f"Created {len(all_chunks)} chunks from {len(documents)} documents")
            
            # Setup ChromaDB collection if storing
            if self.store_embeddings and collection_name and self.batch_storage:
                self.batch_storage.prepare_collection(
                    collection_name=collection_name,
                    entity_type=entity_type,
                    source_type=source_type,
                    model_identifier=self.model_identifier,
                    force_recreate=force_recreate
                )
                logger.info(f"Using collection: {collection_name}")
            
            # Process chunks in batches
            logger.info("Generating embeddings...")
            embedding_count = 0
            
            for embedding, chunk_metadata in self.processor.process_in_batches(all_chunks):
                if embedding is None:
                    self.stats["errors"] += 1
                    continue
                
                # chunk_metadata is now a ProcessingChunkMetadata object
                # Create appropriate BaseMetadata object using metadata factory
                if self.metadata_factory:
                    storage_metadata = self.metadata_factory.create_metadata(
                        chunk_metadata,  # Pass Pydantic model directly
                        entity_type,
                        source_type,
                        source_file,
                        embedding
                    )
                else:
                    # Fallback for when not storing embeddings
                    storage_metadata = BaseMetadata(
                        entity_type=entity_type,
                        source_type=source_type,
                        source_file=source_file,
                        embedding_model=self.model_identifier,
                        embedding_provider=self.config.embedding.provider,
                        embedding_dimension=len(embedding),
                        text_hash=chunk_metadata.text_hash
                    )
                
                # Store using batch storage manager if enabled
                if self.store_embeddings and collection_name and self.batch_storage:
                    # Get chunk text from the original chunks
                    chunk_text = next((text for text, meta in all_chunks 
                                     if meta.text_hash == chunk_metadata.text_hash), "")
                    
                    self.batch_storage.add_embedding(
                        embedding=embedding,
                        text=chunk_text,
                        metadata=storage_metadata,
                        text_hash=chunk_metadata.text_hash,
                        chunk_index=chunk_metadata.chunk_index
                    )
                
                # Create ProcessingResult with structured data
                result = ProcessingResult(
                    embedding=embedding,
                    metadata=storage_metadata,
                    entity_type=entity_type,
                    source_type=source_type,
                    source_file=source_file
                )
                
                yield result
                
                embedding_count += 1
                self.stats["embeddings_generated"] = embedding_count
            
            # Finalize batch storage
            if self.store_embeddings and collection_name and self.batch_storage:
                storage_stats = self.batch_storage.finalize()
                self.stats["embeddings_stored"] = storage_stats.embeddings_stored
                if storage_stats.errors > 0:
                    logger.warning(f"Storage completed with {storage_stats.errors} batch errors")
            
            perf.add_metric("chunks_created", self.stats["chunks_created"])
            perf.add_metric("embeddings_generated", embedding_count)
            perf.add_metric("errors", self.stats["errors"])
    
    
    def process_texts(
        self,
        texts: List[str],
        entity_type: EntityType,
        source_type: SourceType,
        source_file: str,
        metadata_list: Optional[List[Dict[str, Any]]] = None
    ) -> List[Tuple[List[float], BaseMetadata]]:
        """
        Process raw texts to generate embeddings.
        
        Args:
            texts: List of texts to process
            entity_type: Type of entity
            source_type: Source data type
            source_file: Path to source file
            metadata_list: Optional list of metadata for each text
            
        Returns:
            List of (embedding, metadata) tuples
        """
        # Convert texts to documents
        documents = []
        for i, text in enumerate(texts):
            metadata = metadata_list[i] if metadata_list and i < len(metadata_list) else {}
            doc = Document(text=text, metadata=metadata)
            documents.append(doc)
        
        # Process through main pipeline
        results = []
        for embedding, metadata in self.process_documents(
            documents, entity_type, source_type, source_file
        ):
            results.append((embedding, metadata))
        
        return results
    
    
    def get_statistics(self) -> PipelineStatistics:
        """
        Get pipeline statistics as structured Pydantic model.
        
        Returns:
            PipelineStatistics with type-safe processing metrics
        """
        processor_stats = self.processor.get_statistics() if self.processor else None
        processor_stats_dict = processor_stats.model_dump() if processor_stats else {}
        
        return PipelineStatistics(
            documents_processed=self.stats.get("documents_processed", 0),
            chunks_created=self.stats.get("chunks_created", 0),
            embeddings_generated=self.stats.get("embeddings_generated", 0),
            errors=self.stats.get("errors", 0),
            model_identifier=self.model_identifier,
            chunking_method=self.config.chunking.method.value,
            batch_size=self.config.processing.batch_size,
            processor_stats=processor_stats_dict
        )