"""
Demo runner module for Wikipedia full-text search.

This module orchestrates the Wikipedia search demonstration by coordinating
all service modules to execute searches, display results, generate reports,
and export articles.
"""

from pathlib import Path
from typing import Optional
from elasticsearch import Elasticsearch
from rich.console import Console
from ..result_models import WikipediaSearchResult
from ...models import WikipediaArticle
from .models import (
    DemoConfiguration,
    SearchResult
)
from .query_builder import WikipediaQueryBuilder
from .search_executor import WikipediaSearchExecutor
from .display_service import WikipediaDisplayService
from .html_service import WikipediaHtmlService
from .article_exporter import WikipediaArticleExporter
from .statistics_service import WikipediaStatisticsService


class WikipediaDemoRunner:
    """Orchestrator for Wikipedia search demonstrations."""
    
    def __init__(
        self,
        es_client: Elasticsearch,
        config: Optional[DemoConfiguration] = None
    ):
        """Initialize the demo runner with all service modules.
        
        Args:
            es_client: Elasticsearch client instance
            config: Optional demo configuration
        """
        self.config = config or DemoConfiguration()
        
        # Initialize all service modules
        self.query_builder = WikipediaQueryBuilder()
        self.search_executor = WikipediaSearchExecutor(es_client)
        self.display_service = WikipediaDisplayService()
        self.html_service = WikipediaHtmlService(self.config.output_directory)
        self.article_exporter = WikipediaArticleExporter(
            es_client,
            self.config.output_directory
        )
        self.statistics_service = WikipediaStatisticsService()
    
    def run_demo(self) -> WikipediaSearchResult:
        """Run the complete Wikipedia full-text search demonstration.
        
        Returns:
            WikipediaSearchResult with query results and metrics
        """
        # Display header
        self.display_service.display_header()
        
        # Get demonstration queries
        queries = self.query_builder.get_demo_queries()
        
        # Execute searches with progress tracking
        search_results = self._execute_searches_with_progress(queries)
        
        # Calculate statistics
        statistics = self.statistics_service.calculate_statistics(search_results)
        
        # Display statistics
        self.display_service.display_statistics(statistics)
        self.display_service.display_top_documents(statistics)
        
        # Export top articles
        unique_page_ids = self.article_exporter.get_unique_page_ids_from_results(search_results)
        export_result = self.article_exporter.export_articles(
            page_ids=unique_page_ids,
            max_articles=self.config.max_export_articles
        )
        
        # Display export results
        self.display_service.display_export_results(export_result)
        
        # Generate HTML report
        exported_articles_map = self.article_exporter.create_export_mapping(export_result)
        html_path = self.html_service.generate_report(
            search_results=search_results,
            statistics=statistics,
            exported_articles=exported_articles_map
        )
        
        # Open HTML report in browser if configured
        if html_path and self.config.open_html_report:
            self.html_service.open_in_browser(html_path)
        
        # Display completion message
        self.display_service.display_completion_message()
        
        # Create return result
        return self._create_demo_result(
            search_results=search_results,
            statistics=statistics,
            html_path=html_path,
            exported_count=len(export_result.exported_articles)
        )
    
    def _execute_searches_with_progress(self, queries):
        """Execute searches with progress tracking.
        
        Args:
            queries: List of SearchQuery objects
            
        Returns:
            List of SearchResult objects
        """
        search_results = []
        total_queries = len(queries)
        
        if self.config.show_progress:
            with self.display_service.create_progress_context(
                total_queries,
                "Executing search queries..."
            ) as progress:
                task = progress.add_task(
                    "[cyan]Executing search queries...",
                    total=total_queries
                )
                
                for idx, query in enumerate(queries, 1):
                    # Display query info
                    self.display_service.display_query_info(
                        idx, total_queries,
                        query.title, query.description
                    )
                    
                    # Execute search
                    result = self.search_executor.execute_query(query)
                    search_results.append(result)
                    
                    # Display results
                    self.display_service.display_search_results(result)
                    
                    # Update progress
                    progress.update(task, advance=1)
        else:
            # Execute without progress tracking
            for idx, query in enumerate(queries, 1):
                self.display_service.display_query_info(
                    idx, total_queries,
                    query.title, query.description
                )
                result = self.search_executor.execute_query(query)
                search_results.append(result)
                self.display_service.display_search_results(result)
        
        return search_results
    
    def _create_demo_result(
        self,
        search_results,
        statistics,
        html_path,
        exported_count
    ) -> WikipediaSearchResult:
        """Create the final demo result object.
        
        Args:
            search_results: List of SearchResult objects
            statistics: SearchStatistics object
            html_path: Path to HTML report
            exported_count: Number of exported articles
            
        Returns:
            WikipediaSearchResult for the demo
        """
        # Convert top results to WikipediaArticle objects
        wikipedia_articles = []
        for result in search_results[:15]:
            if result.success:
                for hit in result.hits[:1]:
                    doc = hit.document
                    wikipedia_articles.append(WikipediaArticle(
                        page_id=str(doc.page_id) if doc.page_id else '',
                        title=doc.title,
                        summary=doc.content or doc.short_summary or '',
                        city=doc.city,
                        state=doc.state,
                        url=doc.url,
                        score=hit.score
                    ))
        
        # Create sample query DSL for documentation
        sample_query = {}
        if search_results:
            first_result = search_results[0]
            sample_query = self.query_builder.build_complete_search_request(
                first_result.query
            )
        
        return WikipediaSearchResult(
            query_name="Demo 9: Wikipedia Full-Text Search",
            query_description=(
                "Demonstrates enterprise-scale full-text search across 450+ Wikipedia "
                "articles (100MB+ text), showcasing complex query patterns and "
                "sub-100ms performance"
            ),
            execution_time_ms=0,
            total_hits=statistics.total_documents_found,
            returned_hits=len(wikipedia_articles),
            query_dsl=sample_query,
            results=wikipedia_articles,
            es_features=[
                "Full-Text Search - Searching across 100MB+ of text content",
                "Match Queries - Basic full-text search with OR operator",
                "Phrase Queries - Exact phrase matching for precision",
                "Boolean Queries - Complex AND/OR/NOT logic combinations",
                "Multi-Match Queries - Searching across multiple fields with boosting",
                "Highlighting - Extracting relevant content snippets",
                "Field Boosting - Prioritizing title matches over content (title^2)",
                "Large Document Handling - Efficient indexing of 222KB average documents",
                "Sub-100ms Performance - Fast search across massive text corpus"
            ],
            indexes_used=[
                "wikipedia index - 450+ enriched Wikipedia articles",
                "Average document size: 222KB of HTML content",
                "Total corpus size: 100MB+ of searchable text",
                "Demonstrates enterprise content management scale"
            ]
        )


