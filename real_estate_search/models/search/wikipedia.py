"""
Wikipedia-specific search models.

Models for Wikipedia search queries, results, and related operations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from .base import SearchRequest


class WikipediaSearchQuery(SearchRequest):
    """Wikipedia-specific search query configuration."""
    title: str = Field(..., description="Query title for display")
    description: str = Field(..., description="Query description")
    # Inherits query, index, size, sort, aggs, highlight from SearchRequest
    
    def __init__(self, **data):
        """Initialize with wikipedia defaults."""
        if 'index' not in data:
            data['index'] = ['wikipedia']
        super().__init__(**data)


class WikipediaSearchHit(BaseModel):
    """Wikipedia search result hit."""
    document: "WikipediaArticle" = Field(..., description="Wikipedia article document")
    score: float = Field(..., description="Relevance score")
    highlights: dict[str, List[str]] = Field(default_factory=dict, description="Highlighted text fragments")


class WikipediaSearchResult(BaseModel):
    """Wikipedia search result container."""
    query: WikipediaSearchQuery = Field(..., description="Original query")
    total_hits: int = Field(default=0, description="Total number of hits")
    hits: List[WikipediaSearchHit] = Field(default_factory=list, description="Search hits")
    success: bool = Field(..., description="Whether search was successful")
    execution_time_ms: int = Field(default=0, description="Execution time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if search failed")


class HighlightConfig(BaseModel):
    """Elasticsearch highlight configuration."""
    fragment_size: int = Field(default=150, description="Size of highlighted fragments")
    number_of_fragments: int = Field(default=3, description="Number of fragments to return")
    pre_tags: List[str] = Field(default=["<em>"], description="Pre-highlight tags")
    post_tags: List[str] = Field(default=["</em>"], description="Post-highlight tags")
    require_field_match: bool = Field(default=True, description="Only highlight fields that matched the query")


class TopDocument(BaseModel):
    """Top-scoring document from search results."""
    title: str = Field(..., description="Document title")
    page_id: str = Field(..., description="Wikipedia page ID")
    score: float = Field(..., description="Relevance score")
    query_title: str = Field(..., description="Query that found this document")


class ArticleExport(BaseModel):
    """Exported Wikipedia article."""
    page_id: str = Field(..., description="Wikipedia page ID")
    title: str = Field(..., description="Article title")
    filename: str = Field(..., description="Export filename")
    filepath: str = Field(..., description="Full path to exported file")
    file_size_kb: float = Field(..., description="File size in KB")
    content_length: int = Field(..., description="Content length in characters")
    url: str = Field(..., description="Wikipedia URL")


class ArticleExportResult(BaseModel):
    """Result of article export operation."""
    exported_articles: List[ArticleExport] = Field(default_factory=list, description="Successfully exported articles")
    failed_exports: List[str] = Field(default_factory=list, description="Failed article IDs")
    output_directory: str = Field(..., description="Export directory path")
    total_size_kb: float = Field(default=0.0, description="Total size of exported files")


class SearchStatistics(BaseModel):
    """Statistics from search operations."""
    total_queries: int = Field(..., description="Total number of queries executed")
    successful_queries: int = Field(..., description="Number of successful queries")
    total_documents_found: int = Field(..., description="Total documents across all queries")
    average_results_per_query: float = Field(..., description="Average results per query")
    top_documents: List[TopDocument] = Field(default_factory=list, description="Top-scoring documents")


class DemoConfiguration(BaseModel):
    """Configuration for Wikipedia demo."""
    elasticsearch_host: str = Field(default="localhost", description="Elasticsearch host")
    elasticsearch_port: int = Field(default=9200, description="Elasticsearch port")
    output_directory: str = Field(default="/tmp/wikipedia_export", description="Export directory")
    max_export_articles: int = Field(default=10, description="Maximum articles to export")
    show_progress: bool = Field(default=True, description="Show progress indicators")
    open_html_report: bool = Field(default=False, description="Open HTML report after generation")


class HtmlReportData(BaseModel):
    """Data for HTML report generation."""
    search_results: List[WikipediaSearchResult] = Field(..., description="All search results")
    statistics: SearchStatistics = Field(..., description="Search statistics")
    export_result: Optional[ArticleExportResult] = Field(None, description="Export results")
    timestamp: str = Field(..., description="Report generation timestamp")


# Import WikipediaArticle to avoid circular import
from ..wikipedia import WikipediaArticle
# Update forward reference
WikipediaSearchHit.model_rebuild()