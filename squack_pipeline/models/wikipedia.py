"""Wikipedia article data models using Pydantic V2."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WikipediaArticle(BaseModel):
    """Wikipedia article model."""
    
    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    page_id: int
    title: str
    content: str
    url: str
    summary: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    links: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)
    section_titles: List[str] = Field(default_factory=list)
    
    # Embedding field for vector storage
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    
    # Metadata fields
    last_updated: Optional[str] = None
    word_count: Optional[int] = Field(default=None, gt=0)
    language: str = Field(default="en")
    
    @field_validator('embedding')
    @classmethod
    def validate_embedding_dimension(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        """Validate embedding dimensions if present."""
        if v is not None and len(v) > 0:
            # Voyage embeddings are typically 1024 or 1536 dimensions
            if len(v) not in [1024, 1536]:
                raise ValueError(f"Invalid embedding dimension: {len(v)}")
        return v