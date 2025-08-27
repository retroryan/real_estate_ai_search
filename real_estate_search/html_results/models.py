"""
Pydantic models for HTML result generation.

Clean, well-structured models for representing search results
that will be rendered to HTML.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from pathlib import Path


class HTMLHighlight(BaseModel):
    """Represents a highlighted text fragment from search results."""
    
    text: str = Field(..., description="The highlighted text fragment")
    score: Optional[float] = Field(None, description="Relevance score for this fragment")
    field: str = Field(default="full_content", description="Field this highlight came from")
    
    model_config = ConfigDict(frozen=True)
    
    def to_html(self) -> str:
        """Convert highlight to HTML with proper formatting."""
        # Replace emphasis markers with HTML strong tags
        formatted = self.text.replace('**', '<strong>').replace('**', '</strong>')
        # Ensure proper closing of strong tags
        if formatted.count('<strong>') > formatted.count('</strong>'):
            formatted += '</strong>' * (formatted.count('<strong>') - formatted.count('</strong>'))
        return formatted


class HTMLDocument(BaseModel):
    """Represents a single document in search results."""
    
    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    score: float = Field(..., description="Search relevance score")
    categories: Optional[List[str]] = Field(default_factory=list, description="Document categories")
    location: Optional[str] = Field(None, description="Geographic location if available")
    content_length: Optional[int] = Field(None, description="Length of full content in characters")
    highlights: List[HTMLHighlight] = Field(default_factory=list, description="Highlighted text fragments")
    summary: Optional[str] = Field(None, description="Document summary")
    url: Optional[str] = Field(None, description="URL to the document if available")
    local_html_file: Optional[str] = Field(None, description="Path to locally saved HTML file")
    
    model_config = ConfigDict(frozen=True)
    
    @property
    def formatted_location(self) -> str:
        """Get formatted location string."""
        return self.location or "Unknown Location"
    
    @property
    def formatted_size(self) -> str:
        """Get formatted content size."""
        if not self.content_length:
            return "Unknown size"
        return f"{self.content_length:,} characters"
    
    @property
    def top_categories(self) -> List[str]:
        """Get top 3 categories for display."""
        return self.categories[:3] if self.categories else []


class HTMLQueryResult(BaseModel):
    """Represents results from a single query."""
    
    query_title: str = Field(..., description="Title/name of the query")
    query_description: str = Field(..., description="Description of what the query searches for")
    query_dsl: Optional[Dict[str, Any]] = Field(None, description="Elasticsearch query DSL")
    total_results: int = Field(..., description="Total number of matching documents")
    documents: List[HTMLDocument] = Field(default_factory=list, description="Top matching documents")
    execution_time_ms: Optional[int] = Field(None, description="Query execution time in milliseconds")
    
    model_config = ConfigDict(frozen=True)
    
    @property
    def has_results(self) -> bool:
        """Check if query returned results."""
        return self.total_results > 0
    
    @property
    def formatted_execution_time(self) -> str:
        """Get formatted execution time."""
        if not self.execution_time_ms:
            return "N/A"
        return f"{self.execution_time_ms}ms"


class HTMLSearchResult(BaseModel):
    """Represents the complete search results for HTML output."""
    
    title: str = Field(..., description="Title of the search/demo")
    description: str = Field(..., description="Description of the search demonstration")
    queries: List[HTMLQueryResult] = Field(default_factory=list, description="Individual query results")
    total_documents_found: int = Field(0, description="Total documents found across all queries")
    generated_at: datetime = Field(default_factory=datetime.now, description="When results were generated")
    output_path: Optional[Path] = Field(None, description="Path where HTML will be saved")
    
    model_config = ConfigDict(frozen=True)
    
    @property
    def total_queries(self) -> int:
        """Get total number of queries executed."""
        return len(self.queries)
    
    @property
    def successful_queries(self) -> int:
        """Get number of queries that returned results."""
        return sum(1 for q in self.queries if q.has_results)
    
    @property
    def average_results_per_query(self) -> float:
        """Calculate average results per query."""
        if not self.queries:
            return 0
        return self.total_documents_found / len(self.queries)
    
    @property
    def formatted_timestamp(self) -> str:
        """Get formatted generation timestamp."""
        return self.generated_at.strftime("%Y-%m-%d %H:%M:%S")
    
    def get_top_documents(self, limit: int = 5) -> List[HTMLDocument]:
        """Get top scoring documents across all queries."""
        all_docs = []
        for query in self.queries:
            all_docs.extend(query.documents)
        
        # Sort by score and deduplicate by title
        seen_titles = set()
        unique_docs = []
        for doc in sorted(all_docs, key=lambda x: x.score, reverse=True):
            if doc.title not in seen_titles:
                seen_titles.add(doc.title)
                unique_docs.append(doc)
                if len(unique_docs) >= limit:
                    break
        
        return unique_docs