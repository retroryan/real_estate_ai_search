"""Base document converter for entity-specific document conversion."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set
from pydantic import BaseModel, Field

from llama_index.core import Document
from squack_pipeline.models import EntityType
from squack_pipeline.utils.logging import PipelineLogger


class ConversionConfig(BaseModel):
    """Configuration for document conversion."""
    
    entity_type: EntityType = Field(
        ..., 
        description="Type of entity being converted"
    )
    
    embedding_fields: List[str] = Field(
        default_factory=list,
        description="Fields to include in embeddings"
    )
    
    excluded_embed_metadata_keys: Set[str] = Field(
        default_factory=lambda: {
            "entity_id", "chunk_index", "chunk_total",
            "processing_version", "created_at", "updated_at"
        },
        description="Metadata keys to exclude from embeddings"
    )
    
    excluded_llm_metadata_keys: Set[str] = Field(
        default_factory=lambda: {
            "embedding_dimension", "text_hash", "vector_id"
        },
        description="Metadata keys to exclude from LLM context"
    )
    
    include_descriptions: bool = Field(
        default=True,
        description="Whether to include field descriptions in text"
    )
    
    max_text_length: int = Field(
        default=8000,
        ge=100,
        le=50000,
        description="Maximum length of document text"
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = False


class BaseDocumentConverter(ABC):
    """Abstract base class for entity-specific document converters."""
    
    def __init__(self, config: ConversionConfig):
        """Initialize the document converter.
        
        Args:
            config: Conversion configuration
        """
        self.config = config
        self.logger = PipelineLogger.get_logger(
            f"{self.__class__.__name__}({config.entity_type.value})"
        )
    
    @abstractmethod
    def convert_to_documents(self, data: List[Dict[str, Any]]) -> List[Document]:
        """Convert entity data to LlamaIndex Documents.
        
        Args:
            data: List of entity records from Gold tier
            
        Returns:
            List of LlamaIndex Documents ready for embedding
        """
        pass
    
    @abstractmethod
    def create_text_content(self, record: Dict[str, Any]) -> str:
        """Create text content from a single entity record.
        
        Args:
            record: Entity record from Gold tier
            
        Returns:
            Text content for the document
        """
        pass
    
    @abstractmethod
    def create_metadata(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata from a single entity record.
        
        Args:
            record: Entity record from Gold tier
            
        Returns:
            Metadata dictionary for the document
        """
        pass
    
    def get_embedding_fields(self) -> List[str]:
        """Return fields to include in embeddings.
        
        Returns:
            List of field names to include in embeddings
        """
        return self.config.embedding_fields
    
    def truncate_text(self, text: str) -> str:
        """Truncate text to maximum length if needed.
        
        Args:
            text: Text to potentially truncate
            
        Returns:
            Truncated text if it exceeds max length
        """
        if len(text) > self.config.max_text_length:
            # Truncate and add ellipsis
            truncated = text[:self.config.max_text_length - 3] + "..."
            self.logger.debug(
                f"Truncated text from {len(text)} to {self.config.max_text_length} characters"
            )
            return truncated
        return text
    
    def clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Clean metadata by removing None values and empty collections.
        
        Args:
            metadata: Raw metadata dictionary
            
        Returns:
            Cleaned metadata dictionary
        """
        cleaned = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (list, dict, set, tuple)) and not value:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            cleaned[key] = value
        return cleaned
    
    def create_document(
        self,
        text: str,
        metadata: Dict[str, Any],
        doc_id: Optional[str] = None
    ) -> Document:
        """Create a LlamaIndex Document.
        
        Args:
            text: Document text content
            metadata: Document metadata
            doc_id: Optional document ID
            
        Returns:
            LlamaIndex Document
        """
        # Truncate text if needed
        text = self.truncate_text(text)
        
        # Clean metadata
        metadata = self.clean_metadata(metadata)
        
        # Create document
        doc = Document(
            text=text,
            metadata=metadata,
            doc_id=doc_id,
            excluded_embed_metadata_keys=list(self.config.excluded_embed_metadata_keys),
            excluded_llm_metadata_keys=list(self.config.excluded_llm_metadata_keys)
        )
        
        return doc