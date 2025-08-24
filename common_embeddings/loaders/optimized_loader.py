"""
Optimized document loader following LlamaIndex best practices.

Implements efficient document loading patterns with proper ID management,
metadata preservation, and selective data loading strategies.
"""

from typing import List, Dict, Any, Optional, Iterator
from pathlib import Path
import json

from llama_index.core import Document

from ..models import EntityType, SourceType
from ..utils.logging import get_logger
from ..utils.hashing import hash_text

logger = get_logger(__name__)


class OptimizedDocumentLoader:
    """
    Document loader optimized for LlamaIndex best practices.
    
    Implements:
    - Proper document ID management
    - Lazy loading for memory efficiency
    - Selective data retrieval patterns
    - Consistent metadata structure
    """
    
    def __init__(self, base_path: Path, entity_type: EntityType, source_type: SourceType):
        """
        Initialize optimized loader.
        
        Args:
            base_path: Base directory for data files
            entity_type: Type of entity being loaded
            source_type: Source data type
        """
        self.base_path = Path(base_path)
        self.entity_type = entity_type
        self.source_type = source_type
    
    def load_documents_lazy(
        self,
        file_patterns: List[str],
        max_documents: Optional[int] = None,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> Iterator[Document]:
        """
        Lazy load documents following LlamaIndex best practices.
        
        Implements selective data retrieval as recommended:
        "RAG indexes your data and selectively sends only the relevant parts"
        
        Args:
            file_patterns: Glob patterns to match files
            max_documents: Maximum number of documents to load
            metadata_filter: Optional filter criteria
            
        Yields:
            Document objects with optimized metadata
        """
        loaded_count = 0
        
        for pattern in file_patterns:
            files = list(self.base_path.glob(pattern))
            logger.info(f"Found {len(files)} files matching pattern: {pattern}")
            
            for file_path in files:
                if max_documents and loaded_count >= max_documents:
                    logger.info(f"Reached maximum document limit: {max_documents}")
                    return
                
                try:
                    document = self._load_single_document(file_path)
                    if document and self._passes_filter(document, metadata_filter):
                        yield document
                        loaded_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to load {file_path}: {e}")
                    continue
        
        logger.info(f"Loaded {loaded_count} documents using lazy loading")
    
    def load_documents_batch(
        self,
        file_patterns: List[str],
        batch_size: int = 100,
        max_documents: Optional[int] = None
    ) -> Iterator[List[Document]]:
        """
        Load documents in batches for efficient processing.
        
        Follows LlamaIndex performance optimization recommendations.
        
        Args:
            file_patterns: File patterns to match
            batch_size: Number of documents per batch
            max_documents: Maximum total documents
            
        Yields:
            Batches of Document objects
        """
        batch = []
        
        for document in self.load_documents_lazy(file_patterns, max_documents):
            batch.append(document)
            
            if len(batch) >= batch_size:
                yield batch
                batch = []
        
        # Yield remaining documents
        if batch:
            yield batch
    
    def _load_single_document(self, file_path: Path) -> Optional[Document]:
        """
        Load a single document with optimized metadata.
        
        Following LlamaIndex best practice: Proper document structure
        
        Args:
            file_path: Path to document file
            
        Returns:
            Document with enhanced metadata or None
        """
        if file_path.suffix.lower() == '.json':
            return self._load_json_document(file_path)
        elif file_path.suffix.lower() == '.html':
            return self._load_html_document(file_path)
        else:
            return self._load_text_document(file_path)
    
    def _load_json_document(self, file_path: Path) -> Optional[Document]:
        """Load JSON document with structured metadata."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different JSON structures
            if isinstance(data, list):
                # Multiple items in file
                combined_text = []
                combined_metadata = []
                
                for item in data:
                    if isinstance(item, dict):
                        text = self._extract_text_from_dict(item)
                        if text:
                            combined_text.append(text)
                            combined_metadata.append(item)
                
                if not combined_text:
                    return None
                
                full_text = '\n\n'.join(combined_text)
                metadata = {
                    'source_file': str(file_path),
                    'entity_type': self.entity_type.value,
                    'source_type': self.source_type.value,
                    'item_count': len(combined_text),
                    'items': combined_metadata
                }
                
            else:
                # Single item
                full_text = self._extract_text_from_dict(data)
                if not full_text:
                    return None
                
                metadata = {
                    'source_file': str(file_path),
                    'entity_type': self.entity_type.value,
                    'source_type': self.source_type.value,
                    **data  # Include all original fields
                }
            
            # Generate consistent document ID
            doc_id = self._generate_document_id(file_path, full_text)
            
            return Document(
                text=full_text,
                metadata=metadata,
                doc_id=doc_id
            )
            
        except Exception as e:
            logger.error(f"Failed to load JSON document {file_path}: {e}")
            return None
    
    def _load_html_document(self, file_path: Path) -> Optional[Document]:
        """Load HTML document with cleaned text extraction."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Basic HTML cleaning (in production, use BeautifulSoup)
            text = self._clean_html_basic(html_content)
            
            if not text.strip():
                return None
            
            # Extract page ID from filename if applicable
            page_id = file_path.stem.split('_')[0] if '_' in file_path.stem else file_path.stem
            
            metadata = {
                'source_file': str(file_path),
                'entity_type': self.entity_type.value,
                'source_type': self.source_type.value,
                'page_id': page_id,
                'title': file_path.stem,
                'file_size': len(html_content)
            }
            
            doc_id = self._generate_document_id(file_path, text)
            
            return Document(
                text=text,
                metadata=metadata,
                doc_id=doc_id
            )
            
        except Exception as e:
            logger.error(f"Failed to load HTML document {file_path}: {e}")
            return None
    
    def _load_text_document(self, file_path: Path) -> Optional[Document]:
        """Load plain text document."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            if not text.strip():
                return None
            
            metadata = {
                'source_file': str(file_path),
                'entity_type': self.entity_type.value,
                'source_type': self.source_type.value,
                'file_size': len(text)
            }
            
            doc_id = self._generate_document_id(file_path, text)
            
            return Document(
                text=text,
                metadata=metadata,
                doc_id=doc_id
            )
            
        except Exception as e:
            logger.error(f"Failed to load text document {file_path}: {e}")
            return None
    
    def _extract_text_from_dict(self, data: Dict[str, Any]) -> str:
        """Extract text content from dictionary data."""
        text_fields = [
            'text', 'content', 'description', 'summary', 
            'title', 'name', 'details', 'body'
        ]
        
        texts = []
        for field in text_fields:
            if field in data and isinstance(data[field], str):
                texts.append(data[field])
        
        return '\n\n'.join(texts) if texts else ''
    
    def _clean_html_basic(self, html_content: str) -> str:
        """Basic HTML cleaning without external dependencies."""
        # Remove HTML tags (basic regex approach)
        import re
        
        # Remove script and style elements
        html_content = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML tags
        html_content = re.sub(r'<[^>]+>', '', html_content)
        
        # Clean up whitespace
        html_content = re.sub(r'\s+', ' ', html_content)
        html_content = re.sub(r'\n\s*\n', '\n\n', html_content)
        
        return html_content.strip()
    
    def _generate_document_id(self, file_path: Path, text: str) -> str:
        """
        Generate consistent document ID.
        
        Following LlamaIndex best practice: Proper document ID management
        
        Args:
            file_path: Source file path
            text: Document text content
            
        Returns:
            Unique, deterministic document ID
        """
        # Use file path and content hash for consistency
        path_hash = hash_text(str(file_path))[:8]
        content_hash = hash_text(text)[:8]
        return f"{self.entity_type.value}_{path_hash}_{content_hash}"
    
    def _passes_filter(self, document: Document, metadata_filter: Optional[Dict[str, Any]]) -> bool:
        """
        Check if document passes metadata filter.
        
        Implements selective data retrieval pattern.
        
        Args:
            document: Document to check
            metadata_filter: Filter criteria
            
        Returns:
            True if document passes filter
        """
        if not metadata_filter:
            return True
        
        for key, expected_value in metadata_filter.items():
            if key not in document.metadata:
                return False
            
            actual_value = document.metadata[key]
            if isinstance(expected_value, list):
                if actual_value not in expected_value:
                    return False
            elif actual_value != expected_value:
                return False
        
        return True