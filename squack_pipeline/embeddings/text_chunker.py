"""Text chunking using LlamaIndex node parsers."""

from typing import List, Optional

from llama_index.core import Document
from llama_index.core.schema import TextNode
from llama_index.core.node_parser import SimpleNodeParser, SentenceSplitter
from llama_index.core.embeddings import BaseEmbedding

from squack_pipeline.config.settings import ProcessingConfig, ChunkingMethod
from squack_pipeline.utils.logging import PipelineLogger


class TextChunker:
    """Text chunking using LlamaIndex following common_embeddings patterns."""
    
    def __init__(self, config: ProcessingConfig, embedding_model: Optional[BaseEmbedding] = None):
        """Initialize text chunker.
        
        Args:
            config: Processing configuration
            embedding_model: Optional embedding model for semantic chunking
        """
        self.config = config
        self.embedding_model = embedding_model
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        
        # Initialize node parser based on chunking method
        self.node_parser = self._create_node_parser()
    
    def _create_node_parser(self) -> SimpleNodeParser:
        """Create appropriate node parser based on configuration."""
        if self.config.chunk_method == ChunkingMethod.SIMPLE:
            return self._create_simple_parser()
        elif self.config.chunk_method == ChunkingMethod.SEMANTIC:
            return self._create_semantic_parser()
        elif self.config.chunk_method == ChunkingMethod.SENTENCE:
            return self._create_sentence_parser()
        elif self.config.chunk_method == ChunkingMethod.NONE:
            return self._create_no_chunking_parser()
        else:
            self.logger.warning(f"Unknown chunking method: {self.config.chunk_method}, using simple")
            return self._create_simple_parser()
    
    def _create_simple_parser(self) -> SimpleNodeParser:
        """Create simple node parser with token-based chunking."""
        self.logger.info(f"Creating simple node parser with chunk_size={self.config.chunk_size}")
        
        return SimpleNodeParser.from_defaults(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )
    
    def _create_semantic_parser(self) -> SimpleNodeParser:
        """Create semantic node parser if embedding model is available."""
        if not self.embedding_model:
            self.logger.warning("No embedding model provided for semantic chunking, falling back to simple")
            return self._create_simple_parser()
        
        try:
            from llama_index.core.node_parser import SemanticSplitterNodeParser
            
            self.logger.info(
                f"Creating semantic node parser with breakpoint_percentile={self.config.breakpoint_percentile}"
            )
            
            return SemanticSplitterNodeParser(
                buffer_size=self.config.buffer_size,
                breakpoint_percentile_threshold=self.config.breakpoint_percentile,
                embed_model=self.embedding_model
            )
        except ImportError:
            self.logger.warning("SemanticSplitterNodeParser not available, falling back to simple")
            return self._create_simple_parser()
    
    def _create_sentence_parser(self) -> SentenceSplitter:
        """Create sentence-based splitter."""
        self.logger.info(f"Creating sentence splitter with chunk_size={self.config.chunk_size}")
        
        return SentenceSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separator=" "
        )
    
    def _create_no_chunking_parser(self) -> SimpleNodeParser:
        """Create parser that doesn't chunk (one document = one node)."""
        self.logger.info("Creating no-chunking parser (one document per node)")
        
        return SimpleNodeParser.from_defaults(
            chunk_size=10000,  # Large chunk size to avoid splitting
            chunk_overlap=0
        )
    
    def chunk_documents(self, documents: List[Document]) -> List[TextNode]:
        """Chunk documents into text nodes.
        
        Args:
            documents: List of LlamaIndex Documents to chunk
            
        Returns:
            List of TextNode objects
        """
        if not self.config.enable_chunking:
            self.logger.info("Chunking disabled, converting documents to single nodes")
            return self._documents_to_single_nodes(documents)
        
        self.logger.info(f"Chunking {len(documents)} documents using {self.config.chunk_method.value} method")
        
        try:
            # Parse documents into nodes
            nodes = self.node_parser.get_nodes_from_documents(documents)
            
            # Enrich nodes with chunking metadata
            enriched_nodes = []
            for doc_idx, doc in enumerate(documents):
                doc_nodes = [n for n in nodes if n.ref_doc_id == doc.id_]
                
                for node_idx, node in enumerate(doc_nodes):
                    # Add chunking metadata
                    node.metadata.update({
                        "chunk_index": node_idx,
                        "chunk_total": len(doc_nodes),
                        "chunk_method": self.config.chunk_method.value,
                        "source_document_index": doc_idx
                    })
                    
                    # Preserve important metadata from document
                    if "property_id" in doc.metadata:
                        node.metadata["property_id"] = doc.metadata["property_id"]
                    if "entity_type" in doc.metadata:
                        node.metadata["entity_type"] = doc.metadata["entity_type"]
                    
                    enriched_nodes.append(node)
            
            self.logger.info(f"Created {len(enriched_nodes)} text nodes from {len(documents)} documents")
            return enriched_nodes
            
        except Exception as e:
            self.logger.error(f"Error during chunking: {e}")
            # Fallback to single nodes
            self.logger.warning("Falling back to single node per document")
            return self._documents_to_single_nodes(documents)
    
    def _documents_to_single_nodes(self, documents: List[Document]) -> List[TextNode]:
        """Convert documents directly to single text nodes without chunking."""
        nodes = []
        
        for doc_idx, doc in enumerate(documents):
            node = TextNode(
                text=doc.text,
                metadata={
                    **doc.metadata,
                    "chunk_index": 0,
                    "chunk_total": 1,
                    "chunk_method": "none",
                    "source_document_index": doc_idx
                }
            )
            nodes.append(node)
        
        return nodes
    
    def validate_nodes(self, nodes: List[TextNode]) -> bool:
        """Validate chunked nodes."""
        if not nodes:
            self.logger.error("No nodes to validate")
            return False
        
        for i, node in enumerate(nodes):
            if not node.text or len(node.text.strip()) == 0:
                self.logger.error(f"Node {i} has empty text content")
                return False
            
            # Check required metadata
            required_fields = ["chunk_index", "chunk_total", "chunk_method"]
            for field in required_fields:
                if field not in node.metadata:
                    self.logger.error(f"Node {i} missing required metadata field: {field}")
                    return False
        
        self.logger.info(f"Validated {len(nodes)} nodes successfully")
        return True