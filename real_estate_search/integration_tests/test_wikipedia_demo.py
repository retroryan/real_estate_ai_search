"""
Integration tests for WikipediaDemoRunner.

Tests the complete Wikipedia search demo functionality including:
- Query building
- Search execution
- Result processing
- Statistics calculation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from elasticsearch import Elasticsearch
from real_estate_search.demo_queries.wikipedia import (
    WikipediaDemoRunner,
    WikipediaQueryBuilder,
    WikipediaSearchExecutor,
    WikipediaDisplayService,
    WikipediaStatisticsService,
    WikipediaHtmlService,
    WikipediaArticleExporter,
    DemoConfiguration,
    SearchQuery,
    SearchResult,
    SearchHit,
    WikipediaArticle,
    SearchStatistics,
    TopDocument,
    ArticleExportResult,
    ArticleExport
)
from real_estate_search.models.results import WikipediaSearchResult


class TestWikipediaDemoRunner:
    """Test suite for WikipediaDemoRunner."""
    
    @pytest.fixture
    def mock_es_client(self):
        """Create a mock Elasticsearch client."""
        mock = MagicMock(spec=Elasticsearch)
        mock.ping.return_value = True
        return mock
    
    @pytest.fixture
    def demo_config(self):
        """Create test demo configuration."""
        return DemoConfiguration(
            elasticsearch_host="localhost",
            elasticsearch_port=9200,
            output_directory="/tmp/test_output",
            max_export_articles=5,
            show_progress=False,
            open_html_report=False
        )
    
    @pytest.fixture
    def sample_wikipedia_document(self):
        """Create a sample Wikipedia document."""
        return WikipediaArticle(
            title="San Francisco",
            city="San Francisco",
            state="California",
            categories=["Cities in California", "San Francisco Bay Area"],
            full_content="San Francisco is a city in California.",
            content_length=40,
            page_id="wiki-sf-001",
            url="https://en.wikipedia.org/wiki/San_Francisco"
        )
    
    @pytest.fixture
    def mock_search_response(self, sample_wikipedia_document):
        """Create a mock Elasticsearch search response."""
        return {
            'hits': {
                'total': {'value': 2},
                'hits': [
                    {
                        '_score': 0.95,
                        '_source': sample_wikipedia_document.model_dump(),
                        'highlight': {
                            'full_content': [
                                'San Francisco is a <em>city</em> in California.'
                            ]
                        }
                    },
                    {
                        '_score': 0.85,
                        '_source': {
                            'title': 'Golden Gate Bridge',
                            'city': 'San Francisco',
                            'state': 'California',
                            'categories': ['Bridges', 'San Francisco landmarks'],
                            'content': 'The Golden Gate Bridge spans the Golden Gate strait.',
                            'content_length': 50,
                            'page_id': 'wiki-gg-002',
                            'url': 'https://en.wikipedia.org/wiki/Golden_Gate_Bridge'
                        }
                    }
                ]
            }
        }
    
    def test_demo_runner_initialization(self, mock_es_client, demo_config):
        """Test WikipediaDemoRunner initialization."""
        runner = WikipediaDemoRunner(mock_es_client, demo_config)
        
        assert runner.config == demo_config
        assert runner.query_builder is not None
        assert runner.search_executor is not None
        assert runner.display_service is not None
        assert runner.html_service is not None
        assert runner.article_exporter is not None
        assert runner.statistics_service is not None
    
    def test_query_builder_creates_valid_queries(self):
        """Test that query builder creates valid SearchQuery objects."""
        builder = WikipediaQueryBuilder()
        queries = builder.get_demo_queries()
        
        assert len(queries) == 5
        for query in queries:
            assert query.title
            assert query.description
            assert query.query
            assert query.index == "wikipedia"
            assert query.size == 3
    
    def test_search_executor_processes_response(self, mock_es_client, mock_search_response):
        """Test search executor processes Elasticsearch response correctly."""
        mock_es_client.search.return_value = mock_search_response
        
        executor = WikipediaSearchExecutor(mock_es_client)
        query = SearchQuery(
            title="Test Query",
            description="Test Description",
            query={"match": {"full_content": "San Francisco"}}
        )
        
        result = executor.execute_query(query)
        
        assert result.success is True
        assert result.total_hits == 2
        assert len(result.hits) == 2
        assert result.hits[0].score == 0.95
        assert result.hits[0].document.title == "San Francisco"
        assert 'full_content' in result.hits[0].highlights
    
    def test_statistics_service_calculates_metrics(self, sample_wikipedia_document):
        """Test statistics service calculates correct metrics."""
        service = WikipediaStatisticsService()
        
        # Create sample search results
        hit1 = SearchHit(
            document=sample_wikipedia_document,
            score=0.95,
            highlights={}
        )
        
        search_results = [
            SearchResult(
                query=SearchQuery(
                    title="Query 1",
                    description="Description 1",
                    query={"match": {"title": "test"}}
                ),
                total_hits=10,
                hits=[hit1],
                success=True,
                execution_time_ms=50
            ),
            SearchResult(
                query=SearchQuery(
                    title="Query 2",
                    description="Description 2",
                    query={"match": {"title": "test2"}}
                ),
                total_hits=5,
                hits=[],
                success=True,
                execution_time_ms=30
            )
        ]
        
        stats = service.calculate_statistics(search_results)
        
        assert stats.total_queries == 2
        assert stats.successful_queries == 2
        assert stats.total_documents_found == 15
        assert stats.average_results_per_query == 7.5
    
    def test_article_exporter_exports_articles(self, mock_es_client, sample_wikipedia_document):
        """Test article exporter functionality."""
        mock_es_client.get.return_value = {
            '_source': {
                **sample_wikipedia_document.model_dump(),
                'full_content': '<html>Full article content</html>'
            }
        }
        
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            with patch('pathlib.Path.write_text') as mock_write:
                with patch('pathlib.Path.stat') as mock_stat:
                    mock_stat.return_value = MagicMock(st_size=5000)
                    
                    exporter = WikipediaArticleExporter(mock_es_client, "/tmp/test_wiki_export")
                    result = exporter.export_articles(["wiki-sf-001"], max_articles=1)
                    
                    assert len(result.exported_articles) == 1
                    assert result.exported_articles[0].page_id == "wiki-sf-001"
                    assert result.exported_articles[0].title == "San Francisco"
                    mock_mkdir.assert_called_once()
                    mock_write.assert_called_once()
    
    @patch('real_estate_search.demo_queries.wikipedia.display_service.Console')
    def test_display_service_formats_output(self, mock_console, sample_wikipedia_document):
        """Test display service formatting."""
        service = WikipediaDisplayService()
        
        # Test header display
        service.display_header()
        mock_console.return_value.print.assert_called()
        
        # Test search results display
        hit = SearchHit(
            document=sample_wikipedia_document,
            score=0.95,
            highlights={'full_content': ['Test <em>highlight</em>']}
        )
        
        result = SearchResult(
            query=SearchQuery(
                title="Test",
                description="Test",
                query={"match": {"title": "test"}}
            ),
            total_hits=1,
            hits=[hit],
            success=True
        )
        
        service.display_search_results(result)
        
        # Test statistics display
        stats = SearchStatistics(
            total_queries=5,
            successful_queries=5,
            total_documents_found=25,
            average_results_per_query=5.0,
            top_documents=[
                TopDocument(
                    title="Top Doc",
                    page_id="top-1",
                    score=0.99,
                    query_title="Query 1"
                )
            ]
        )
        
        service.display_statistics(stats)
        service.display_top_documents(stats)
    
    def test_run_demo_integration(self, mock_es_client, mock_search_response, demo_config):
        """Test complete demo run integration."""
        mock_es_client.search.return_value = mock_search_response
        mock_es_client.get.return_value = {
            '_source': {
                'title': 'Test Article',
                'full_content': 'Full content here',
                'url': 'http://test.com',
                'content_length': 100,
                'page_id': 'test-001'
            }
        }
        
        with patch('pathlib.Path.mkdir'):
            with patch('pathlib.Path.write_text'):
                with patch('pathlib.Path.stat') as mock_stat:
                    mock_stat.return_value = MagicMock(st_size=1000)
                    
                    with patch.object(WikipediaHtmlService, 'generate_report', return_value="/tmp/report.html"):
                        with patch.object(WikipediaDisplayService, 'display_header'):
                            with patch.object(WikipediaDisplayService, 'display_query_info'):
                                with patch.object(WikipediaDisplayService, 'display_search_results'):
                                    with patch.object(WikipediaDisplayService, 'display_statistics'):
                                        with patch.object(WikipediaDisplayService, 'display_completion_message'):
                                            runner = WikipediaDemoRunner(mock_es_client, demo_config)
                                            result = runner.run_demo()
                                            
                                            assert result.query_name == "Demo 9: Wikipedia Full-Text Search"
                                            assert result.total_hits > 0
                                            assert len(result.es_features) > 0
                                            assert len(result.indexes_used) > 0
    
    def test_demo_runner_error_handling(self, mock_es_client, demo_config):
        """Test demo runner handles errors gracefully."""
        mock_es_client.search.side_effect = Exception("Elasticsearch error")
        
        with patch.object(WikipediaDisplayService, 'display_header'):
            with patch.object(WikipediaDisplayService, 'display_query_info'):
                with patch.object(WikipediaDisplayService, 'display_search_results'):
                    with patch.object(WikipediaDisplayService, 'display_statistics'):
                        with patch.object(WikipediaDisplayService, 'display_completion_message'):
                            runner = WikipediaDemoRunner(mock_es_client, demo_config)
                            result = runner.run_demo()
                            
                            # Should still return a result even with errors
                            assert result.query_name == "Demo 9: Wikipedia Full-Text Search"
    
    def test_no_backward_compatibility_function(self):
        """Verify no backward compatibility function exists."""
        from real_estate_search.demo_queries import wikipedia
        
        # Verify WikipediaDemoRunner exists
        assert hasattr(wikipedia, 'WikipediaDemoRunner')
        
        # Verify demo_wikipedia_fulltext does NOT exist
        assert not hasattr(wikipedia, 'demo_wikipedia_fulltext')
        
        # Verify all service modules exist
        assert hasattr(wikipedia, 'WikipediaQueryBuilder')
        assert hasattr(wikipedia, 'WikipediaSearchExecutor')
        assert hasattr(wikipedia, 'WikipediaDisplayService')
        assert hasattr(wikipedia, 'WikipediaHtmlService')
        assert hasattr(wikipedia, 'WikipediaArticleExporter')
        assert hasattr(wikipedia, 'WikipediaStatisticsService')