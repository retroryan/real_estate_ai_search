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

from .models.config import Config
from .models.metadata import (
    BaseMetadata,
    PropertyMetadata,
    NeighborhoodMetadata,
    WikipediaMetadata,
    ProcessingMetadata,
)
from .models.enums import EntityType, SourceType
from .models.processing import (
    ChunkMetadata as ProcessingChunkMetadata,  # Rename to avoid conflict
    ProcessingResult,
    DocumentBatch
)
from .models.statistics import PipelineStatistics
from .embedding.factory import EmbeddingFactory
from .processing.chunking import TextChunker
from .processing.batch_processor import BatchProcessor
from .models.exceptions import EmbeddingGenerationError
from .utils.logging import get_logger, PerformanceLogger
from .utils.hashing import hash_text


logger = get_logger(__name__)


class EmbeddingPipeline:
    """
    Main pipeline for generating embeddings with correlation metadata.
    
    Orchestrates the entire embedding generation process from documents
    to stored embeddings with comprehensive metadata.
    """
    
    def __init__(self, config: Config):
        """
        Initialize embedding pipeline.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config
        self.embed_model = None
        self.model_identifier = None
        self.chunker = None
        self.processor = None
        
        # Statistics
        self.stats = {
            "documents_processed": 0,
            "chunks_created": 0,
            "embeddings_generated": 0,
            "errors": 0
        }
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize pipeline components."""
        logger.info("Initializing embedding pipeline components")
        
        # Create embedding model
        try:
            self.embed_model, self.model_identifier = EmbeddingFactory.create_provider(self.config)
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
        source_file: str
    ) -> Generator[ProcessingResult, None, None]:
        """
        Process documents to generate embeddings with structured metadata.
        
        Args:
            documents: List of LlamaIndex Document objects
            entity_type: Type of entity being processed
            source_type: Type of data source
            source_file: Path to source file
            
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
                    for chunk_text, chunk_metadata in chunks:
                        # Create structured metadata using ProcessingChunkMetadata
                        combined_metadata = ProcessingChunkMetadata.from_combined_dict(
                            document_metadata=doc.metadata,
                            chunk_metadata=chunk_metadata,
                            source_doc_id=doc.metadata.get('id', hash_text(doc.text)[:8])
                        )
                        all_chunks.append((chunk_text, combined_metadata))
                    
                    self.stats["documents_processed"] += 1
                    
                    # Update progress for each document
                    chunking_progress.update(global_doc_idx + 1)
                
                # Log batch completion
                logger.info(f"Completed batch {current_batch_num}/{total_batches} - Total chunks so far: {len(all_chunks)}")
            
            chunking_progress.complete()
            self.stats["chunks_created"] = len(all_chunks)
            logger.info(f"Created {len(all_chunks)} chunks from {len(documents)} documents")
            
            # Process chunks in batches
            logger.info("Generating embeddings...")
            embedding_count = 0
            
            for embedding, chunk_metadata in self.processor.process_in_batches(all_chunks):
                if embedding is None:
                    self.stats["errors"] += 1
                    continue
                
                # chunk_metadata is now a ProcessingChunkMetadata object
                # Create appropriate BaseMetadata object for storage
                storage_metadata = self._create_metadata(
                    chunk_metadata.to_dict(),  # Convert to dict for compatibility
                    entity_type,
                    source_type,
                    source_file,
                    embedding
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
            
            perf.add_metric("chunks_created", self.stats["chunks_created"])
            perf.add_metric("embeddings_generated", embedding_count)
            perf.add_metric("errors", self.stats["errors"])
    
    def _create_metadata(
        self,
        chunk_metadata: Dict[str, Any],
        entity_type: EntityType,
        source_type: SourceType,
        source_file: str,
        embedding: List[float]
    ) -> BaseMetadata:
        """
        Create appropriate metadata object for the entity type.
        
        Args:
            chunk_metadata: Chunk-level metadata
            entity_type: Type of entity
            source_type: Source data type
            source_file: Path to source file
            embedding: Generated embedding vector
            
        Returns:
            Appropriate metadata object
        """
        # Common metadata fields
        base_fields = {
            "source_type": source_type,
            "source_file": source_file,
            "source_collection": f"{entity_type.value}_{self.model_identifier}_v{self.config.metadata_version.replace('.', '')}",
            "source_timestamp": datetime.utcnow(),
            "embedding_model": self.model_identifier,
            "embedding_provider": self.config.embedding.provider,
            "embedding_dimension": len(embedding),
            "embedding_version": self.config.metadata_version,
            "text_hash": chunk_metadata.get('text_hash', ''),
        }
        
        # Create entity-specific metadata
        if entity_type == EntityType.PROPERTY:
            metadata = PropertyMetadata(
                listing_id=chunk_metadata.get('listing_id', ''),
                source_file_index=chunk_metadata.get('source_file_index'),
                **base_fields
            )
        
        elif entity_type == EntityType.NEIGHBORHOOD:
            metadata = NeighborhoodMetadata(
                neighborhood_id=chunk_metadata.get('neighborhood_id', ''),
                neighborhood_name=chunk_metadata.get('neighborhood_name', ''),
                source_file_index=chunk_metadata.get('source_file_index'),
                **base_fields
            )
        
        elif entity_type in [EntityType.WIKIPEDIA_ARTICLE, EntityType.WIKIPEDIA_SUMMARY]:
            # Handle chunking metadata if present
            chunk_meta = None
            if chunk_metadata.get('chunk_total', 1) > 1:
                from .models.metadata import ChunkMetadata
                chunk_meta = ChunkMetadata(
                    chunk_index=chunk_metadata.get('chunk_index', 0),
                    chunk_total=chunk_metadata.get('chunk_total', 1),
                    parent_id=str(chunk_metadata.get('page_id', '')),
                )
            
            metadata = WikipediaMetadata(
                page_id=chunk_metadata.get('page_id', 0),
                article_id=chunk_metadata.get('article_id'),
                has_summary=chunk_metadata.get('has_summary', False),
                chunk_metadata=chunk_meta,
                **base_fields
            )
        
        else:
            # Fallback to base metadata
            metadata = BaseMetadata(
                entity_type=entity_type,
                **base_fields
            )
        
        return metadata
    
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