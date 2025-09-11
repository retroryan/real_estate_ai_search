"""
Wikipedia search module for demonstrating Elasticsearch full-text capabilities.

This module provides a clean, modular architecture for searching Wikipedia articles
with Elasticsearch, generating reports, and exporting documents.
"""

from ...models.search.wikipedia import (
    WikipediaSearchQuery as SearchQuery,
    WikipediaSearchResult as SearchResult,
    WikipediaSearchHit as SearchHit,
    ArticleExport,
    ArticleExportResult,
    SearchStatistics,
    HtmlReportData,
    DemoConfiguration,
    TopDocument,
    HighlightConfig
)
from ...models.wikipedia import WikipediaArticle
from .demo_runner import WikipediaDemoRunner
from .query_builder import WikipediaQueryBuilder
from .search_executor import WikipediaSearchExecutor
from .display_service import WikipediaDisplayService
from .html_service import WikipediaHtmlService
from .article_exporter import WikipediaArticleExporter
from .statistics_service import WikipediaStatisticsService

__all__ = [
    # Models
    'WikipediaArticle',
    'SearchQuery',
    'SearchResult',
    'SearchHit',
    'ArticleExport',
    'ArticleExportResult',
    'SearchStatistics',
    'HtmlReportData',
    'DemoConfiguration',
    'TopDocument',
    'HighlightConfig',
    # Main demo class
    # Service classes
    'WikipediaDemoRunner',
    'WikipediaQueryBuilder',
    'WikipediaSearchExecutor',
    'WikipediaDisplayService',
    'WikipediaHtmlService',
    'WikipediaArticleExporter',
    'WikipediaStatisticsService'
]