"""
Batch processing for efficient embedding generation.

Adapted from wiki_embed and real_estate_embed batch processing patterns.
"""

import time
from typing import List, Tuple, Dict, Any, Generator, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from ..models.config import ChunkingConfig as ProcessingConfig
from ..models.exceptions import EmbeddingGenerationError
from ..models.statistics import BatchProcessorStatistics
from ..utils.logging import get_logger, PerformanceLogger


logger = get_logger(__name__)


class BatchProcessor:
    """
    Handles batch processing of embeddings with progress tracking.
    
    Follows patterns from existing modules with enhanced error handling.
    """
    
    def __init__(
        self,
        config: ProcessingConfig,
        embed_model: Any,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ):
        """
        Initialize batch processor.
        
        Args:
            config: Processing configuration
            embed_model: Embedding model to use
            progress_callback: Optional callback for progress updates
        """
        self.config = config
        self.embed_model = embed_model
        self.progress_callback = progress_callback
        self.total_processed = 0
        self.total_failed = 0
    
    def process_batch(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        Process a batch of texts to generate embeddings.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            EmbeddingGenerationError: If batch processing fails
        """
        try:
            # Apply rate limiting if configured
            if self.config.rate_limit_delay > 0:
                time.sleep(self.config.rate_limit_delay)
            
            # Generate embeddings
            embeddings = []
            for text in texts:
                embedding = self.embed_model.get_text_embedding(text)
                embeddings.append(embedding)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            raise EmbeddingGenerationError(f"Failed to process batch: {e}")
    
    def process_in_batches(
        self,
        items: List[Tuple[str, Dict[str, Any]]]
    ) -> Generator[Tuple[List[float], Dict[str, Any]], None, None]:
        """
        Process items in batches with metadata preservation.
        
        Args:
            items: List of (text, metadata) tuples
            
        Yields:
            Tuples of (embedding, metadata)
        """
        total_items = len(items)
        batch_size = self.config.batch_size
        
        logger.info(f"Processing {total_items} items in batches of {batch_size}")
        
        with PerformanceLogger(f"Batch processing {total_items} items") as perf:
            for i in range(0, total_items, batch_size):
                batch_items = items[i:i + batch_size]
                batch_texts = [text for text, _ in batch_items]
                
                # Show progress
                current_batch = i // batch_size + 1
                total_batches = (total_items + batch_size - 1) // batch_size
                
                if self.config.show_progress:
                    logger.info(f"Processing batch {current_batch}/{total_batches}")
                
                if self.progress_callback:
                    self.progress_callback(i, total_items)
                
                try:
                    # Process batch
                    embeddings = self.process_batch(batch_texts)
                    
                    # Yield results with metadata
                    for j, embedding in enumerate(embeddings):
                        metadata = batch_items[j][1]
                        yield embedding, metadata
                    
                    self.total_processed += len(batch_items)
                    
                except Exception as e:
                    logger.error(f"Batch {current_batch} failed: {e}")
                    self.total_failed += len(batch_items)
                    
                    # Yield None for failed items
                    for _, metadata in batch_items:
                        yield None, metadata
            
            # Log final metrics
            perf.add_metric("total_processed", self.total_processed)
            perf.add_metric("total_failed", self.total_failed)
    
    def process_parallel(
        self,
        items: List[Tuple[str, Dict[str, Any]]]
    ) -> List[Tuple[Optional[List[float]], Dict[str, Any]]]:
        """
        Process items in parallel using thread pool.
        
        Args:
            items: List of (text, metadata) tuples
            
        Returns:
            List of (embedding, metadata) tuples
        """
        results = []
        total_items = len(items)
        
        logger.info(f"Processing {total_items} items in parallel with {self.config.max_workers} workers")
        
        def process_item(item: Tuple[str, Dict[str, Any]]) -> Tuple[Optional[List[float]], Dict[str, Any]]:
            """Process a single item."""
            text, metadata = item
            try:
                if self.config.rate_limit_delay > 0:
                    time.sleep(self.config.rate_limit_delay)
                
                embedding = self.embed_model.get_text_embedding(text)
                return embedding, metadata
            except Exception as e:
                logger.error(f"Failed to process item: {e}")
                return None, metadata
        
        with PerformanceLogger(f"Parallel processing {total_items} items") as perf:
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                # Submit all tasks
                futures = {
                    executor.submit(process_item, item): i
                    for i, item in enumerate(items)
                }
                
                # Collect results as they complete
                completed = 0
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                        
                        if result[0] is not None:
                            self.total_processed += 1
                        else:
                            self.total_failed += 1
                        
                        completed += 1
                        
                        if self.config.show_progress and completed % 10 == 0:
                            logger.info(f"Completed {completed}/{total_items} items")
                        
                        if self.progress_callback:
                            self.progress_callback(completed, total_items)
                        
                    except Exception as e:
                        logger.error(f"Future failed: {e}")
                        self.total_failed += 1
                        results.append((None, {}))
            
            perf.add_metric("total_processed", self.total_processed)
            perf.add_metric("total_failed", self.total_failed)
        
        return results
    
    def get_statistics(self) -> BatchProcessorStatistics:
        """
        Get processing statistics as structured Pydantic model.
        
        Returns:
            BatchProcessorStatistics with type-safe processing metrics
        """
        success_rate = (
            self.total_processed / (self.total_processed + self.total_failed)
            if (self.total_processed + self.total_failed) > 0
            else 0.0
        )
        
        return BatchProcessorStatistics(
            total_processed=self.total_processed,
            total_failed=self.total_failed,
            success_rate=success_rate,
            timestamp=datetime.utcnow()
        )