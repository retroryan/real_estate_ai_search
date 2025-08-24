"""
Text chunking strategies using LlamaIndex.

Adapted from real_estate_embed and wiki_embed chunking implementations,
following LlamaIndex best practices for node parsing.
"""

from typing import List, Tuple, Dict, Any, Optional
from llama_index.core import Document
from llama_index.core.node_parser import (
    SimpleNodeParser,
    SemanticSplitterNodeParser,
    SentenceSplitter,
)
from llama_index.core.schema import TextNode

from ..models import ChunkingConfig, ChunkingMethod, ChunkingError
from ..utils.logging import get_logger
from ..utils.hashing import hash_text


logger = get_logger(__name__)


class TextChunker:
    """
    Text chunking with multiple strategies.
    
    Uses LlamaIndex node parsers for consistent chunking.
    """
    
    def __init__(self, config: ChunkingConfig, embed_model: Any = None):
        """
        Initialize text chunker.
        
        Args:
            config: Chunking configuration
            embed_model: Embedding model (required for semantic chunking)
        """
        self.config = config
        self.embed_model = embed_model
        self.parser = self._create_parser()
    
    def _create_parser(self):
        """
        Create the appropriate parser based on configuration.
        
        Returns:
            LlamaIndex node parser instance
            
        Raises:
            ChunkingError: If parser creation fails
        """
        method = self.config.method
        
        try:
            if method == ChunkingMethod.SIMPLE:
                logger.debug(f"Creating simple parser (size={self.config.chunk_size}, overlap={self.config.chunk_overlap})")
                return SimpleNodeParser.from_defaults(
                    chunk_size=self.config.chunk_size,
                    chunk_overlap=self.config.chunk_overlap
                )
            
            elif method == ChunkingMethod.SEMANTIC:
                if not self.embed_model:
                    raise ChunkingError("Semantic chunking requires an embedding model")
                
                logger.debug(f"Creating semantic parser (breakpoint={self.config.breakpoint_percentile}%, buffer={self.config.buffer_size})")
                return SemanticSplitterNodeParser(
                    embed_model=self.embed_model,
                    breakpoint_percentile_threshold=self.config.breakpoint_percentile,
                    buffer_size=self.config.buffer_size
                )
            
            elif method == ChunkingMethod.SENTENCE:
                logger.debug("Creating sentence splitter")
                return SentenceSplitter(
                    chunk_size=self.config.chunk_size,
                    chunk_overlap=self.config.chunk_overlap
                )
            
            elif method == ChunkingMethod.NONE:
                logger.debug("No chunking - documents will be processed as-is")
                return None
            
            else:
                raise ChunkingError(f"Unknown chunking method: {method}")
                
        except Exception as e:
            logger.error(f"Failed to create parser: {e}")
            raise ChunkingError(f"Parser creation failed: {e}")
    
    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Chunk text into smaller pieces with metadata.
        
        Args:
            text: Text to chunk
            metadata: Base metadata to attach to chunks
            
        Returns:
            List of (chunk_text, chunk_metadata) tuples
        """
        if self.config.method == ChunkingMethod.NONE:
            # No chunking - return as single chunk
            chunk_metadata = (metadata or {}).copy()
            chunk_metadata.update({
                'chunk_index': 0,
                'chunk_total': 1,
                'text_hash': hash_text(text)
            })
            return [(text, chunk_metadata)]
        
        # Create document with metadata
        doc = Document(
            text=text,
            metadata=metadata or {}
        )
        
        # Parse into nodes
        try:
            nodes = self.parser.get_nodes_from_documents([doc])
        except Exception as e:
            logger.error(f"Chunking failed: {e}")
            raise ChunkingError(f"Failed to chunk text: {e}")
        
        # Handle oversized chunks if configured
        if self.config.split_oversized_chunks:
            nodes = self._split_oversized_chunks(nodes)
        
        # Convert nodes to tuples with enhanced metadata
        chunks = []
        total_chunks = len(nodes)
        
        for i, node in enumerate(nodes):
            chunk_text = node.text
            chunk_metadata = node.metadata.copy()
            
            # Add chunking metadata
            chunk_metadata.update({
                'chunk_index': i,
                'chunk_total': total_chunks,
                'text_hash': hash_text(chunk_text),
                'chunk_method': self.config.method.value
            })
            
            # Add parent document hash if multiple chunks
            if total_chunks > 1:
                chunk_metadata['parent_hash'] = hash_text(text)
            
            chunks.append((chunk_text, chunk_metadata))
        
        logger.debug(f"Created {len(chunks)} chunks from {len(text)} characters")
        return chunks
    
    def chunk_documents(
        self,
        documents: List[Document]
    ) -> List[TextNode]:
        """
        Chunk multiple documents into nodes.
        
        Args:
            documents: List of LlamaIndex Document objects
            
        Returns:
            List of TextNode objects with metadata
        """
        if self.config.method == ChunkingMethod.NONE:
            # Convert documents to nodes without chunking
            nodes = []
            for doc in documents:
                node = TextNode(
                    text=doc.text,
                    metadata=doc.metadata.copy()
                )
                node.metadata['chunk_index'] = 0
                node.metadata['chunk_total'] = 1
                nodes.append(node)
            return nodes
        
        # Parse all documents
        try:
            nodes = self.parser.get_nodes_from_documents(documents)
        except Exception as e:
            logger.error(f"Document chunking failed: {e}")
            raise ChunkingError(f"Failed to chunk documents: {e}")
        
        # Handle oversized chunks if configured
        if self.config.split_oversized_chunks:
            nodes = self._split_oversized_chunks(nodes)
        
        # Group nodes by source document and add chunk indices
        doc_nodes = {}
        for node in nodes:
            # Get source document identifier
            source_id = node.metadata.get('source_id', 'unknown')
            if source_id not in doc_nodes:
                doc_nodes[source_id] = []
            doc_nodes[source_id].append(node)
        
        # Add chunk indices per document
        final_nodes = []
        for source_id, source_nodes in doc_nodes.items():
            total = len(source_nodes)
            for i, node in enumerate(source_nodes):
                node.metadata['chunk_index'] = i
                node.metadata['chunk_total'] = total
                node.metadata['text_hash'] = hash_text(node.text)
                final_nodes.append(node)
        
        logger.info(f"Chunked {len(documents)} documents into {len(final_nodes)} nodes")
        return final_nodes
    
    def _split_oversized_chunks(self, nodes: List) -> List:
        """
        Split chunks that exceed maximum size.
        
        Args:
            nodes: List of nodes to check
            
        Returns:
            List of nodes with oversized ones split
        """
        max_size = self.config.max_chunk_size
        new_nodes = []
        split_count = 0
        
        for node in nodes:
            words = node.text.split()
            word_count = len(words)
            
            if word_count <= max_size:
                new_nodes.append(node)
            else:
                # Split oversized chunk
                split_count += 1
                num_splits = (word_count + max_size - 1) // max_size
                
                for i in range(num_splits):
                    start_idx = i * max_size
                    end_idx = min((i + 1) * max_size, word_count)
                    chunk_text = ' '.join(words[start_idx:end_idx])
                    
                    # Create new node with split metadata
                    new_node = TextNode(
                        text=chunk_text,
                        metadata={**node.metadata, 'split_index': i},
                        id_=f"{node.node_id}_split_{i}"
                    )
                    new_nodes.append(new_node)
        
        if split_count > 0:
            logger.info(f"Split {split_count} oversized chunks into {len(new_nodes) - len(nodes) + split_count} smaller chunks")
        
        return new_nodes