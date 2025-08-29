"""Wikipedia-specific document converter."""

from typing import List, Dict, Any, Optional

from llama_index.core import Document
from squack_pipeline.embeddings.converters.base_converter import (
    BaseDocumentConverter, ConversionConfig
)
from squack_pipeline.models import EntityType


class WikipediaDocumentConverter(BaseDocumentConverter):
    """Convert Wikipedia data to LlamaIndex Documents.
    
    This converter handles the transformation of Gold tier Wikipedia data
    into Documents optimized for embedding generation, managing both
    full articles and chunks for efficient retrieval.
    """
    
    def __init__(self, config: Optional[ConversionConfig] = None):
        """Initialize Wikipedia document converter.
        
        Args:
            config: Optional conversion configuration
        """
        if config is None:
            config = ConversionConfig(
                entity_type=EntityType.WIKIPEDIA,
                embedding_fields=[
                    "title",
                    "summary",
                    "content",
                    "categories",
                    "sections",
                    "keywords"
                ]
            )
        super().__init__(config)
    
    def convert_to_documents(self, data: List[Dict[str, Any]]) -> List[Document]:
        """Convert Wikipedia data to LlamaIndex Documents.
        
        Args:
            data: List of Wikipedia records from Gold tier
            
        Returns:
            List of LlamaIndex Documents
        """
        documents = []
        
        for record in data:
            try:
                # Check if this is a chunk or full article
                is_chunk = record.get("chunk_index") is not None
                
                if is_chunk:
                    # Handle chunked article
                    documents.extend(self._convert_chunks(record))
                else:
                    # Handle full article
                    doc = self._convert_article(record)
                    if doc:
                        documents.append(doc)
                
            except Exception as e:
                self.logger.error(
                    f"Error converting Wikipedia {record.get('page_id', 'unknown')}: {e}"
                )
                continue
        
        self.logger.info(f"Converted {len(documents)} Wikipedia documents")
        return documents
    
    def _convert_article(self, record: Dict[str, Any]) -> Optional[Document]:
        """Convert a full Wikipedia article to a Document.
        
        Args:
            record: Wikipedia article record
            
        Returns:
            LlamaIndex Document or None if conversion fails
        """
        # Create text content
        text = self.create_text_content(record)
        
        # Create metadata
        metadata = self.create_metadata(record)
        
        # Create document with page ID as doc_id
        doc = self.create_document(
            text=text,
            metadata=metadata,
            doc_id=f"wiki_{record.get('page_id')}"
        )
        
        return doc
    
    def _convert_chunks(self, record: Dict[str, Any]) -> List[Document]:
        """Convert Wikipedia article chunks to Documents.
        
        Args:
            record: Wikipedia record with chunks
            
        Returns:
            List of LlamaIndex Documents for each chunk
        """
        documents = []
        chunks = record.get("chunks", [])
        
        for chunk in chunks:
            try:
                # Create chunk-specific text
                text = self._create_chunk_text(record, chunk)
                
                # Create chunk-specific metadata
                metadata = self._create_chunk_metadata(record, chunk)
                
                # Create document with unique chunk ID
                chunk_id = f"wiki_{record.get('page_id')}_chunk_{chunk.get('index', 0)}"
                doc = self.create_document(
                    text=text,
                    metadata=metadata,
                    doc_id=chunk_id
                )
                
                documents.append(doc)
                
            except Exception as e:
                self.logger.error(
                    f"Error converting chunk {chunk.get('index')} of {record.get('page_id')}: {e}"
                )
                continue
        
        return documents
    
    def create_text_content(self, record: Dict[str, Any]) -> str:
        """Create rich text content from Wikipedia data.
        
        Args:
            record: Wikipedia record from Gold tier
            
        Returns:
            Text content for embedding
        """
        text_parts = []
        
        # Article header
        title = record.get("title")
        if title:
            text_parts.append(f"Wikipedia Article: {title}")
        
        page_id = record.get("page_id")
        if page_id:
            text_parts.append(f"Page ID: {page_id}")
        
        # Categories (array field)
        categories = record.get("categories")
        if categories and isinstance(categories, list):
            text_parts.append(f"\nCategories: {', '.join(categories)}")
        
        # Keywords (array field)
        keywords = record.get("keywords")
        if keywords and isinstance(keywords, list):
            text_parts.append(f"Keywords: {', '.join(keywords)}")
        
        # Summary
        summary = record.get("summary")
        if summary:
            text_parts.append(f"\nSummary:\n{summary}")
        
        # Main content (may be truncated for full articles)
        content = record.get("content")
        if content:
            # For full articles, we might want to use a preview
            if len(content) > 2000:
                content_preview = content[:2000] + "..."
                text_parts.append(f"\nContent Preview:\n{content_preview}")
            else:
                text_parts.append(f"\nContent:\n{content}")
        
        # Sections (nested structure)
        sections = record.get("sections")
        if sections and isinstance(sections, list):
            section_titles = []
            for section in sections:
                title = section.get("title")
                if title:
                    section_titles.append(title)
            
            if section_titles:
                text_parts.append(f"\nSections:\n- " + "\n- ".join(section_titles))
        
        # References (array field)
        references = record.get("references")
        if references and isinstance(references, list) and len(references) > 0:
            # Show first few references
            ref_preview = references[:5]
            text_parts.append(f"\nReferences ({len(references)} total):\n- " + "\n- ".join(ref_preview))
        
        # Related articles (array field)
        related_articles = record.get("related_articles")
        if related_articles and isinstance(related_articles, list):
            text_parts.append(f"\nRelated Articles: {', '.join(related_articles)}")
        
        # Join all parts
        return "\n".join(text_parts)
    
    def _create_chunk_text(self, record: Dict[str, Any], chunk: Dict[str, Any]) -> str:
        """Create text content for a specific chunk.
        
        Args:
            record: Wikipedia record
            chunk: Chunk data
            
        Returns:
            Text content for the chunk
        """
        text_parts = []
        
        # Article context
        title = record.get("title")
        if title:
            text_parts.append(f"Wikipedia Article: {title}")
        
        # Chunk information
        chunk_index = chunk.get("index", 0)
        chunk_total = chunk.get("total", 1)
        text_parts.append(f"Chunk {chunk_index + 1} of {chunk_total}")
        
        # Section context if available
        section = chunk.get("section")
        if section:
            text_parts.append(f"Section: {section}")
        
        # Chunk content
        content = chunk.get("content", "")
        if content:
            text_parts.append(f"\nContent:\n{content}")
        
        return "\n".join(text_parts)
    
    def create_metadata(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata from Wikipedia record.
        
        Args:
            record: Wikipedia record from Gold tier
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            "entity_type": "wikipedia",
            "page_id": record.get("page_id"),
            "title": record.get("title"),
        }
        
        # Add URL if available
        metadata["url"] = record.get("url")
        
        # Add language
        metadata["language"] = record.get("language", "en")
        
        # Add categories as list
        categories = record.get("categories")
        if categories:
            metadata["categories"] = categories
        
        # Add keywords as list
        keywords = record.get("keywords")
        if keywords:
            metadata["keywords"] = keywords
        
        # Add relevance information
        metadata["relevance_score"] = record.get("relevance_score")
        metadata["page_rank"] = record.get("page_rank")
        
        # Add content metrics
        metadata["word_count"] = record.get("word_count")
        metadata["section_count"] = record.get("section_count")
        metadata["reference_count"] = record.get("reference_count")
        
        # Add dates
        metadata["last_modified"] = record.get("last_modified")
        metadata["retrieval_date"] = record.get("retrieval_date")
        
        # Add location context if available
        metadata["location_context"] = record.get("location_context")
        metadata["city_relevance"] = record.get("city_relevance")
        
        # Add chunk information if present
        if record.get("chunk_index") is not None:
            metadata["chunk_index"] = record.get("chunk_index")
            metadata["chunk_total"] = record.get("chunk_total")
        
        # Add processing metadata
        metadata["gold_processed_at"] = record.get("gold_processed_at")
        metadata["processing_version"] = record.get("processing_version")
        
        return metadata
    
    def _create_chunk_metadata(self, record: Dict[str, Any], chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata for a specific chunk.
        
        Args:
            record: Wikipedia record
            chunk: Chunk data
            
        Returns:
            Metadata dictionary for the chunk
        """
        # Start with base metadata
        metadata = self.create_metadata(record)
        
        # Override/add chunk-specific metadata
        metadata["chunk_index"] = chunk.get("index", 0)
        metadata["chunk_total"] = chunk.get("total", 1)
        metadata["chunk_section"] = chunk.get("section")
        metadata["chunk_start_char"] = chunk.get("start_char")
        metadata["chunk_end_char"] = chunk.get("end_char")
        metadata["chunk_word_count"] = chunk.get("word_count")
        
        # Add parent document reference
        metadata["parent_page_id"] = record.get("page_id")
        metadata["parent_title"] = record.get("title")
        
        return metadata