"""Batch processor for embedding generation with progress tracking."""

import time
from typing import List, Callable, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from llama_index.core.schema import TextNode
from llama_index.core.embeddings import BaseEmbedding
from tqdm import tqdm

from squack_pipeline.config.settings import ProcessingConfig
from squack_pipeline.utils.logging import PipelineLogger


class BatchProcessor:
    """Batch processor for embeddings following common_embeddings patterns."""
    
    def __init__(
        self, 
        config: ProcessingConfig,
        embedding_model: BaseEmbedding,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ):
        """Initialize batch processor.
        
        Args:
            config: Processing configuration
            embedding_model: LlamaIndex embedding model
            progress_callback: Optional callback for progress updates
        """
        self.config = config
        self.embedding_model = embedding_model
        self.progress_callback = progress_callback
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
    
    def process_nodes_to_embeddings(self, nodes: List[TextNode]) -> List[TextNode]:
        """Process text nodes to generate embeddings.
        
        Args:
            nodes: List of TextNode objects
            
        Returns:
            List of TextNode objects with embeddings
        """
        if not nodes:
            self.logger.warning("No nodes provided for embedding generation")
            return []
        
        self.logger.info(f"Processing {len(nodes)} nodes for embedding generation")
        self.logger.info(f"Batch size: {self.config.batch_size}, Max workers: {self.config.max_workers}")
        
        # Process in batches
        batches = self._create_batches(nodes)
        processed_nodes = []
        
        if self.config.show_progress:
            progress_bar = tqdm(
                total=len(nodes),
                desc="Generating embeddings",
                unit="nodes"
            )
        else:
            progress_bar = None
        
        try:
            if self.config.max_workers == 1:
                # Sequential processing
                for batch_idx, batch in enumerate(batches):
                    batch_nodes = self._process_batch_sequential(batch, batch_idx)
                    processed_nodes.extend(batch_nodes)
                    
                    if progress_bar:
                        progress_bar.update(len(batch))
                    
                    # Apply rate limiting
                    if self.config.rate_limit_delay > 0 and batch_idx < len(batches) - 1:
                        time.sleep(self.config.rate_limit_delay)
            else:
                # Parallel processing with thread pool
                processed_nodes = self._process_batches_parallel(batches, progress_bar)
            
            self.logger.info(f"Successfully generated embeddings for {len(processed_nodes)} nodes")
            return processed_nodes
            
        except Exception as e:
            self.logger.error(f"Error during batch processing: {e}")
            raise
        finally:
            if progress_bar:
                progress_bar.close()
    
    def _create_batches(self, nodes: List[TextNode]) -> List[List[TextNode]]:
        """Create batches from nodes."""
        batches = []
        for i in range(0, len(nodes), self.config.batch_size):
            batch = nodes[i:i + self.config.batch_size]
            batches.append(batch)
        
        self.logger.info(f"Created {len(batches)} batches from {len(nodes)} nodes")
        return batches
    
    def _process_batch_sequential(self, batch: List[TextNode], batch_idx: int) -> List[TextNode]:
        """Process a single batch sequentially."""
        self.logger.debug(f"Processing batch {batch_idx + 1} with {len(batch)} nodes")
        
        try:
            # Extract text from nodes
            texts = [node.text for node in batch]
            
            # Generate embeddings
            embeddings = self.embedding_model.get_text_embedding_batch(texts)
            
            # Assign embeddings to nodes
            for node, embedding in zip(batch, embeddings):
                node.embedding = embedding
                
                # Add embedding metadata
                node.metadata.update({
                    "embedding_dimension": len(embedding) if embedding else 0,
                    "embedding_model": getattr(self.embedding_model, 'model_name', 'unknown'),
                    "embedding_provider": self.config.__class__.__name__,
                    "batch_index": batch_idx,
                    "embedded_at": time.time()
                })
            
            return batch
            
        except Exception as e:
            self.logger.error(f"Error processing batch {batch_idx}: {e}")
            # Return nodes without embeddings rather than failing completely
            for node in batch:
                node.embedding = None
                node.metadata.update({
                    "embedding_error": str(e),
                    "batch_index": batch_idx
                })
            return batch
    
    def _process_batches_parallel(self, batches: List[List[TextNode]], progress_bar: Optional[tqdm]) -> List[TextNode]:
        """Process batches in parallel using thread pool."""
        processed_nodes = []
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(self._process_batch_sequential, batch, idx): (batch, idx)
                for idx, batch in enumerate(batches)
            }
            
            # Process completed batches
            for future in as_completed(future_to_batch):
                batch, batch_idx = future_to_batch[future]
                
                try:
                    batch_nodes = future.result()
                    processed_nodes.extend(batch_nodes)
                    
                    if progress_bar:
                        progress_bar.update(len(batch))
                    
                    if self.progress_callback:
                        self.progress_callback(len(processed_nodes), len(batches) * self.config.batch_size)
                
                except Exception as e:
                    self.logger.error(f"Batch {batch_idx} failed: {e}")
                    # Add batch nodes without embeddings
                    processed_nodes.extend(batch)
        
        return processed_nodes
    
    def validate_embeddings(self, nodes: List[TextNode]) -> Dict[str, Any]:
        """Validate generated embeddings and return metrics."""
        metrics = {
            "total_nodes": len(nodes),
            "nodes_with_embeddings": 0,
            "nodes_with_errors": 0,
            "embedding_dimensions": set(),
            "average_embedding_dimension": 0,
            "embedding_models": set()
        }
        
        valid_embeddings = []
        
        for node in nodes:
            if node.embedding is not None and len(node.embedding) > 0:
                metrics["nodes_with_embeddings"] += 1
                metrics["embedding_dimensions"].add(len(node.embedding))
                valid_embeddings.append(len(node.embedding))
                
                # Track embedding model
                if "embedding_model" in node.metadata:
                    metrics["embedding_models"].add(node.metadata["embedding_model"])
            
            if node.metadata.get("embedding_error"):
                metrics["nodes_with_errors"] += 1
        
        # Calculate average dimension
        if valid_embeddings:
            metrics["average_embedding_dimension"] = sum(valid_embeddings) / len(valid_embeddings)
        
        # Convert sets to lists for JSON serialization
        metrics["embedding_dimensions"] = list(metrics["embedding_dimensions"])
        metrics["embedding_models"] = list(metrics["embedding_models"])
        
        # Calculate success rate
        success_rate = metrics["nodes_with_embeddings"] / metrics["total_nodes"] if metrics["total_nodes"] > 0 else 0
        metrics["success_rate"] = success_rate
        
        # Log validation results
        self.logger.info(f"Embedding validation results:")
        self.logger.info(f"  Total nodes: {metrics['total_nodes']}")
        self.logger.info(f"  Nodes with embeddings: {metrics['nodes_with_embeddings']}")
        self.logger.info(f"  Nodes with errors: {metrics['nodes_with_errors']}")
        self.logger.info(f"  Success rate: {success_rate:.2%}")
        self.logger.info(f"  Average embedding dimension: {metrics['average_embedding_dimension']:.1f}")
        
        if success_rate < 0.8:
            self.logger.warning(f"Low embedding success rate: {success_rate:.2%}")
        
        return metrics