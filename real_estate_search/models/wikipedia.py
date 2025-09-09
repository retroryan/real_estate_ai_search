"""
Wikipedia article model.

This is the single, authoritative WikipediaArticle model that serves as the 
sole source of truth for Wikipedia article data throughout the application.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, computed_field


class WikipediaArticle(BaseModel):
    """Wikipedia article model."""
    page_id: str = Field(..., description="Wikipedia page ID")
    title: str = Field(..., description="Article title")
    url: Optional[str] = Field(None, description="Article URL")
    
    # Content
    summary: Optional[str] = Field(None, description="Article summary")
    content: Optional[str] = Field(None, description="Article content")
    full_content: Optional[str] = Field(None, description="Full HTML content")
    content_length: Optional[int] = Field(None, ge=0, description="Content length")
    
    # Location relevance
    city: Optional[str] = Field(None, description="Associated city")
    state: Optional[str] = Field(None, description="Associated state")
    # TODO: Fix relevance_score to ensure values are properly normalized to 0-100 range
    # Currently getting values > 100 from the pipeline which causes validation errors
    relevance_score: Optional[float] = Field(None, description="Location relevance")
    
    # Classification
    categories: List[str] = Field(default_factory=list, description="Wikipedia categories")
    topics: List[str] = Field(default_factory=list, description="Article topics")
    content_category: Optional[str] = Field(None, description="Content category")
    
    # Metadata
    score: Optional[float] = Field(None, alias="_score", description="Search relevance score")
    relationship: Optional[str] = Field(None, alias="_relationship", description="Relationship to parent entity")
    confidence: Optional[float] = Field(None, alias="_confidence", ge=0, le=1, description="Relationship confidence")
    
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    
    @computed_field  # type: ignore
    @property
    def location_string(self) -> str:
        """Get location as string."""
        if self.city and self.state:
            return f"{self.city}, {self.state}"
        return self.city or self.state or "Location unknown"