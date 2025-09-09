"""
Pydantic models for Wikipedia search functionality.

This module defines all data models used throughout the Wikipedia search system,
ensuring strong typing and validation across module boundaries.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


class WikipediaDocument(BaseModel):
    """Model for Wikipedia document from Elasticsearch."""
    title: str = Field(..., description="Article title")
    city: Optional[str] = Field(None, description="City location")
    state: Optional[str] = Field(None, description="State location")
    categories: List[str] = Field(default_factory=list, description="Article categories")
    full_content: Optional[str] = Field(None, description="Full article content")
    content: Optional[str] = Field(None, description="Content summary")
    content_length: Optional[int] = Field(None, description="Content length")
    page_id: Optional[str] = Field(None, description="Wikipedia page ID")
    url: Optional[str] = Field(None, description="Wikipedia URL")
    short_summary: Optional[str] = Field(None, description="Short summary")
    long_summary: Optional[str] = Field(None, description="Long summary")
    
    @field_validator('categories', mode='before')
    @classmethod
    def ensure_categories_list(cls, v):
        """Ensure categories is always a list."""
        if v is None:
            return []
        try:
            return list(v)
        except (TypeError, ValueError):
            return [v] if v else []


class SearchQuery(BaseModel):
    """Model for search query configuration."""
    title: str = Field(..., description="Query title for display")
    description: str = Field(..., description="Query description")
    query: Dict[str, Any] = Field(..., description="Elasticsearch query DSL")
    size: int = Field(3, description="Number of results to return")
    index: str = Field("wikipedia", description="Elasticsearch index to search")
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        """Ensure query has valid structure."""
        if not v:
            raise ValueError("Query cannot be empty")
        return v


class HighlightConfig(BaseModel):
    """Configuration for search result highlighting."""
    fragment_size: int = Field(200, description="Size of highlighted snippets")
    number_of_fragments: int = Field(2, description="Number of snippets per result")
    pre_tags: List[str] = Field(default_factory=lambda: ["<em>"], description="Highlight start tags")
    post_tags: List[str] = Field(default_factory=lambda: ["</em>"], description="Highlight end tags")
    require_field_match: bool = Field(True, description="Only highlight matching fields")


class SearchHit(BaseModel):
    """Model for individual search result hit."""
    document: WikipediaDocument = Field(..., description="Document data")
    score: float = Field(..., description="Relevance score")
    highlights: Dict[str, List[str]] = Field(default_factory=dict, description="Highlighted fragments")
    

class SearchResult(BaseModel):
    """Model for complete search result."""
    query: SearchQuery = Field(..., description="Original query")
    total_hits: int = Field(0, description="Total matching documents")
    hits: List[SearchHit] = Field(default_factory=list, description="Search result hits")
    success: bool = Field(True, description="Whether query succeeded")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time_ms: Optional[int] = Field(None, description="Query execution time")


class ArticleExport(BaseModel):
    """Model for exported Wikipedia article."""
    page_id: str = Field(..., description="Wikipedia page ID")
    title: str = Field(..., description="Article title")
    filename: str = Field(..., description="Exported filename")
    filepath: str = Field(..., description="Full file path")
    file_size_kb: float = Field(..., description="File size in KB")
    content_length: int = Field(..., description="Character count")
    url: Optional[str] = Field(None, description="Wikipedia URL")
    

class ArticleExportResult(BaseModel):
    """Result of article export operation."""
    exported_articles: List[ArticleExport] = Field(default_factory=list, description="Successfully exported articles")
    failed_exports: List[str] = Field(default_factory=list, description="Page IDs that failed to export")
    output_directory: str = Field(..., description="Directory where articles were saved")
    total_size_kb: float = Field(0.0, description="Total size of exported files")


class TopDocument(BaseModel):
    """Model for top-scoring document in results."""
    title: str = Field(..., description="Document title")
    page_id: str = Field(..., description="Wikipedia page ID")
    score: float = Field(..., description="Relevance score")
    query_title: str = Field(..., description="Query that found this document")


class SearchStatistics(BaseModel):
    """Statistics for search results."""
    total_queries: int = Field(0, description="Number of queries executed")
    successful_queries: int = Field(0, description="Number of successful queries")
    total_documents_found: int = Field(0, description="Total documents across all queries")
    average_results_per_query: float = Field(0.0, description="Average results per query")
    top_documents: List[TopDocument] = Field(default_factory=list, description="Top scoring documents")


class HtmlReportData(BaseModel):
    """Data for HTML report generation."""
    title: str = Field(..., description="Report title")
    description: str = Field(..., description="Report description")
    search_results: List[SearchResult] = Field(default_factory=list, description="All search results")
    statistics: SearchStatistics = Field(..., description="Summary statistics")
    exported_articles: Dict[str, str] = Field(default_factory=dict, description="Mapping of page_id to filename")
    report_path: Optional[str] = Field(None, description="Path where report was saved")


class DemoConfiguration(BaseModel):
    """Configuration for Wikipedia search demo."""
    elasticsearch_host: str = Field("localhost", description="Elasticsearch host")
    elasticsearch_port: int = Field(9200, description="Elasticsearch port")
    output_directory: str = Field("real_estate_search/out_html", description="Output directory for reports")
    max_export_articles: int = Field(10, description="Maximum articles to export")
    show_progress: bool = Field(True, description="Show progress indicators")
    open_html_report: bool = Field(True, description="Open HTML report in browser")