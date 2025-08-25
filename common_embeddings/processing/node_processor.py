"""
Node-based processing following LlamaIndex best practices.

Implements Node-centric approach as recommended in LlamaIndex documentation
where Nodes are the atomic unit of data processing.
"""

from typing import List, Dict, Any, Optional, Generator
from uuid import uuid4

from llama_index.core import Document
from llama_index.core.schema import TextNode, NodeRelationship, RelatedNodeInfo
from llama_index.core.node_parser import NodeParser

from ..models import ProcessingResult, EntityType, SourceType
from ..utils.logging import get_logger
from ..utils.hashing import hash_text

logger = get_logger(__name__)


class NodeProcessor:
    """
    Process documents into nodes following LlamaIndex best practices.
    
    Implements the Node-centric approach where Nodes are atomic units
    that maintain relationships and enable efficient retrieval.
    """
    
    def __init__(self, node_parser: NodeParser):
        """
        Initialize node processor.
        
        Args:
            node_parser: LlamaIndex node parser instance
        """
        self.node_parser = node_parser
    
    def process_documents_to_nodes(
        self,
        documents: List[Document],
        entity_type: EntityType,
        source_type: SourceType
    ) -> List[TextNode]:
        """
        Process documents to nodes with proper relationships.
        
        Following LlamaIndex best practice: "Nodes as atomic unit of data"
        
        Args:
            documents: Source documents to process
            entity_type: Type of entity being processed
            source_type: Source data type
            
        Returns:
            List of TextNode objects with relationships and enhanced metadata
        """
        if not documents:
            return []
        
        # Ensure documents have proper IDs for relationship tracking
        documents = self._ensure_document_ids(documents)
        
        # Parse documents into nodes
        try:
            nodes = self.node_parser.get_nodes_from_documents(documents)
        except Exception as e:
            logger.error(f"Node parsing failed: {e}")
            return []
        
        # Enhance nodes with relationships and metadata
        enhanced_nodes = self._enhance_nodes_with_relationships(
            nodes, documents, entity_type, source_type
        )
        
        logger.info(f"Processed {len(documents)} documents into {len(enhanced_nodes)} nodes")
        return enhanced_nodes
    
    def _ensure_document_ids(self, documents: List[Document]) -> List[Document]:
        """
        Ensure all documents have proper IDs for relationship tracking.
        
        LlamaIndex best practice: Proper document ID management
        
        Args:
            documents: Documents to process
            
        Returns:
            Documents with guaranteed unique IDs
        """
        for doc in documents:
            if not hasattr(doc, 'doc_id') or not doc.doc_id:
                # Generate ID from content hash for consistency
                content_hash = hash_text(doc.text)
                doc.doc_id = f"{content_hash[:8]}-{str(uuid4())[:8]}"
        
        return documents
    
    def _enhance_nodes_with_relationships(
        self,
        nodes: List[TextNode],
        source_documents: List[Document],
        entity_type: EntityType,
        source_type: SourceType
    ) -> List[TextNode]:
        """
        Enhance nodes with parent/child relationships and metadata.
        
        Following LlamaIndex best practice: Node relationships for retrieval
        
        Args:
            nodes: Parsed nodes
            source_documents: Original documents
            entity_type: Entity type
            source_type: Source type
            
        Returns:
            Enhanced nodes with relationships
        """
        # Create document lookup for relationship mapping
        doc_lookup = {doc.doc_id: doc for doc in source_documents}
        
        # Group nodes by source document
        doc_nodes = {}
        for node in nodes:
            source_doc_id = getattr(node, 'ref_doc_id', None)
            if source_doc_id not in doc_nodes:
                doc_nodes[source_doc_id] = []
            doc_nodes[source_doc_id].append(node)
        
        enhanced_nodes = []
        for source_doc_id, node_group in doc_nodes.items():
            source_doc = doc_lookup.get(source_doc_id)
            if not source_doc:
                logger.warning(f"Source document not found for node group: {source_doc_id}")
                continue
            
            # Sort nodes by their order in the document
            node_group.sort(key=lambda n: getattr(n, 'start_char_idx', 0))
            
            # Enhance each node with relationships and metadata
            for i, node in enumerate(node_group):
                # Add entity and source metadata
                node.metadata.update({
                    'entity_type': entity_type.value,
                    'source_type': source_type.value,
                    'text_hash': hash_text(node.text),
                    'chunk_index': i,
                    'chunk_total': len(node_group),
                    'processing_timestamp': str(hash(frozenset(node.metadata.items())))  # Deterministic timestamp
                })
                
                # Set up node relationships following LlamaIndex patterns
                relationships = {}
                
                # Parent relationship to source document
                if source_doc_id:
                    relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(
                        node_id=source_doc_id,
                        metadata={'doc_type': 'source_document'}
                    )
                
                # Previous/Next relationships for sequential access
                if i > 0:
                    prev_node = node_group[i - 1]
                    relationships[NodeRelationship.PREVIOUS] = RelatedNodeInfo(
                        node_id=prev_node.node_id,
                        metadata={'chunk_index': i - 1}
                    )
                
                if i < len(node_group) - 1:
                    next_node = node_group[i + 1]
                    relationships[NodeRelationship.NEXT] = RelatedNodeInfo(
                        node_id=next_node.node_id,
                        metadata={'chunk_index': i + 1}
                    )
                
                # Apply relationships to node
                node.relationships.update(relationships)
                
                # Ensure node has a unique ID
                if not node.node_id:
                    node.node_id = f"{source_doc_id}_chunk_{i}"
                
                enhanced_nodes.append(node)
        
        logger.debug(f"Enhanced {len(enhanced_nodes)} nodes with relationships and metadata")
        return enhanced_nodes
    
    def nodes_to_processing_results(
        self,
        nodes: List[TextNode],
        embeddings: List[List[float]],
        entity_type: EntityType,
        source_type: SourceType,
        source_file: str
    ) -> Generator[ProcessingResult, None, None]:
        """
        Convert nodes with embeddings to ProcessingResult objects.
        
        Args:
            nodes: Enhanced TextNode objects
            embeddings: Corresponding embeddings
            entity_type: Entity type
            source_type: Source type  
            source_file: Source file path
            
        Yields:
            ProcessingResult objects with node-based metadata
        """
        if len(nodes) != len(embeddings):
            logger.error(f"Mismatch: {len(nodes)} nodes but {len(embeddings)} embeddings")
            return
        
        for node, embedding in zip(nodes, embeddings):
            # Create metadata from node attributes
            from ..services import MetadataFactory
            
            # Convert node metadata for metadata factory
            chunk_metadata = {
                'text_hash': node.metadata.get('text_hash'),
                'chunk_index': node.metadata.get('chunk_index', 0),
                'chunk_total': node.metadata.get('chunk_total', 1),
                **node.metadata  # Include all other metadata
            }
            
            # Note: This would need the metadata factory instance
            # In practice, this conversion should be handled by the pipeline
            
            yield ProcessingResult(
                embedding=embedding,
                text=node.text,
                metadata=chunk_metadata,  # Simplified for now
                entity_type=entity_type,
                source_type=source_type,
                source_file=source_file,
                node_id=node.node_id,
                relationships=dict(node.relationships) if node.relationships else {}
            )