"""Raw Wikipedia article model matching source data."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class RawWikipediaArticle(BaseModel):
    """Raw Wikipedia article data as it appears in source files."""
    
    model_config = ConfigDict(frozen=True)
    
    # Core identifiers
    page_id: str = Field(description="Wikipedia page ID")
    title: str = Field(description="Article title")
    
    # Content
    summary: str = Field(description="Article summary")
    content: str = Field(description="Full article content")
    
    # Metadata
    categories: list[str] = Field(default_factory=list, description="Article categories")
    url: str = Field(description="Wikipedia URL")
    
    # Related entities
    related_neighborhoods: list[str] = Field(default_factory=list, description="Related neighborhood IDs")
    coordinates: Optional[str] = Field(default=None, description="Geographic coordinates if applicable")
    
    # Statistics
    word_count: Optional[int] = Field(default=None, description="Word count of content")
    last_modified: Optional[str] = Field(default=None, description="Last modification date")
    
    # Links
    inbound_links: Optional[int] = Field(default=None, description="Number of inbound links")
    outbound_links: Optional[int] = Field(default=None, description="Number of outbound links")
    images: list[str] = Field(default_factory=list, description="Image URLs in article")