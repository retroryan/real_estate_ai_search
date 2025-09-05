"""Integration test for Wikipedia neighborhood enrichment in Silver layer."""

import pytest
from pathlib import Path
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.silver.wikipedia import WikipediaSilverTransformer
from squack_pipeline_v2.utils.neighborhood_enrichment import NeighborhoodWikipediaEnricher


class TestWikipediaNeighborhoodEnrichment:
    """Test Wikipedia articles are enriched with neighborhood data."""
    
    @pytest.fixture
    def connection_manager(self):
        """Create DuckDB connection manager."""
        settings = PipelineSettings()
        return DuckDBConnectionManager(settings.duckdb)
    
    @pytest.fixture
    def transformer(self, connection_manager):
        """Create Wikipedia Silver transformer with mock embedding provider."""
        settings = PipelineSettings()
        
        # Mock embedding provider to avoid API calls
        class MockEmbeddingProvider:
            def generate_embeddings(self, texts):
                class MockResponse:
                    def __init__(self):
                        self.embeddings = [[0.1] * 10 for _ in texts]
                return MockResponse()
        
        return WikipediaSilverTransformer(
            settings=settings,
            connection_manager=connection_manager,
            embedding_provider=MockEmbeddingProvider()
        )
    
    def test_neighborhood_mapping_extraction(self, connection_manager, transformer):
        """Test that neighborhood mappings are correctly extracted using utility."""
        conn = connection_manager.get_connection()
        
        # Create test silver_neighborhoods table with sample data
        conn.execute("""
            DROP TABLE IF EXISTS silver_neighborhoods;
            CREATE TABLE silver_neighborhoods AS
            SELECT * FROM (VALUES
                ('n1', 'Mission District', 'San Francisco', 'CA', 12345),
                ('n2', 'Castro', 'San Francisco', 'CA', 12345),
                ('n3', 'SOMA', 'San Francisco', 'CA', 67890),
                ('n4', 'Haight-Ashbury', 'San Francisco', 'CA', NULL)
            ) AS t(neighborhood_id, name, city, state, wikipedia_page_id)
        """)
        
        # Use enricher utility to verify mappings work
        enricher = NeighborhoodWikipediaEnricher(conn)
        assert enricher.check_neighborhoods_table_exists() is True
        
        # Create a CTE and verify it works
        mappings = conn.execute(f"""
            WITH {enricher.get_neighborhood_mappings_cte()}
            SELECT * FROM neighborhood_mappings ORDER BY page_id
        """).fetchall()
        
        assert len(mappings) == 2
        
        # Check first Wikipedia article (has 2 neighborhoods)
        page1 = mappings[0]
        assert page1[0] == 12345  # page_id
        assert set(page1[1]) == {'n1', 'n2'}  # neighborhood_ids
        assert set(page1[2]) == {'Mission District', 'Castro'}  # neighborhood_names
        assert page1[3] in ['Mission District', 'Castro']  # primary_neighborhood_name
        
        # Check second Wikipedia article (has 1 neighborhood)
        page2 = mappings[1]
        assert page2[0] == 67890  # page_id
        assert page2[1] == ['n3']  # neighborhood_ids
        assert page2[2] == ['SOMA']  # neighborhood_names
        assert page2[3] == 'SOMA'  # primary_neighborhood_name
    
    def test_wikipedia_enrichment_with_neighborhoods(self, connection_manager, transformer):
        """Test that Wikipedia articles are enriched with neighborhood data."""
        conn = connection_manager.get_connection()
        
        # Clean up any existing test tables
        conn.execute("DROP TABLE IF EXISTS silver_wikipedia_test")
        
        # Create test bronze_wikipedia table
        conn.execute("""
            DROP TABLE IF EXISTS bronze_wikipedia;
            CREATE TABLE bronze_wikipedia AS
            SELECT * FROM (VALUES
                ('w1', 12345, 'loc1', 'Golden Gate Park', 'http://wiki.org/1', 'Parks', 
                 37.7, -122.4, 'San Francisco', 'San Francisco County', 'California', 
                 0.9, 1, '2024-01-01', 'file1.html', 'hash1', 'img1.jpg', 10, 
                 '{}', 'Short summary 1', 'Long detailed summary about Golden Gate Park'),
                ('w2', 67890, 'loc2', 'Salesforce Tower', 'http://wiki.org/2', 'Buildings',
                 37.8, -122.3, 'San Francisco', 'San Francisco County', 'California',
                 0.8, 1, '2024-01-01', 'file2.html', 'hash2', 'img2.jpg', 15,
                 '{}', 'Short summary 2', 'Long detailed summary about Salesforce Tower'),
                ('w3', 11111, 'loc3', 'Random Article', 'http://wiki.org/3', 'Other',
                 NULL, NULL, NULL, NULL, NULL,
                 0.5, 1, '2024-01-01', 'file3.html', 'hash3', NULL, 5,
                 '{}', 'Short summary 3', 'Long detailed summary about something else')
            ) AS t(id, pageid, location_id, title, url, categories, latitude, longitude,
                  best_city, best_county, best_state, relevance_score, depth, crawled_at,
                  html_file, file_hash, image_url, links_count, infobox_data,
                  short_summary, long_summary)
        """)
        
        # Create test silver_neighborhoods table
        conn.execute("""
            DROP TABLE IF EXISTS silver_neighborhoods;
            CREATE TABLE silver_neighborhoods AS
            SELECT * FROM (VALUES
                ('n1', 'Mission District', 'San Francisco', 'CA', 12345),
                ('n2', 'Castro', 'San Francisco', 'CA', 12345),
                ('n3', 'SOMA', 'San Francisco', 'CA', 67890)
            ) AS t(neighborhood_id, name, city, state, wikipedia_page_id)
        """)
        
        # Run the transformation (embedding provider is already mocked)
        transformer._apply_transformations('bronze_wikipedia', 'silver_wikipedia_test')
        
        # Verify enriched data
        results = conn.execute("""
            SELECT page_id, title, neighborhood_names, primary_neighborhood_name, neighborhood_ids
            FROM silver_wikipedia_test
            ORDER BY page_id
        """).fetchall()
        
        assert len(results) == 3
        
        # Check article with no neighborhoods
        article1 = results[0]
        assert article1[0] == 11111  # page_id
        assert article1[1] == 'Random Article'
        assert article1[2] is None or article1[2] == []  # neighborhood_names
        assert article1[3] is None  # primary_neighborhood_name
        assert article1[4] is None or article1[4] == []  # neighborhood_ids
        
        # Check article with multiple neighborhoods
        article2 = results[1]
        assert article2[0] == 12345  # page_id
        assert article2[1] == 'Golden Gate Park'
        assert set(article2[2]) == {'Mission District', 'Castro'}  # neighborhood_names
        assert article2[3] in ['Mission District', 'Castro']  # primary_neighborhood_name
        assert set(article2[4]) == {'n1', 'n2'}  # neighborhood_ids
        
        # Check article with single neighborhood
        article3 = results[2]
        assert article3[0] == 67890  # page_id
        assert article3[1] == 'Salesforce Tower'
        assert article3[2] == ['SOMA']  # neighborhood_names
        assert article3[3] == 'SOMA'  # primary_neighborhood_name
        assert article3[4] == ['n3']  # neighborhood_ids
    
    def test_handling_missing_neighborhoods_table(self, connection_manager, transformer):
        """Test graceful handling when silver_neighborhoods table doesn't exist."""
        conn = connection_manager.get_connection()
        
        # Clean up any existing test tables
        conn.execute("DROP TABLE IF EXISTS silver_wikipedia_test")
        conn.execute("DROP TABLE IF EXISTS silver_neighborhoods")
        
        # Create test bronze_wikipedia table
        conn.execute("""
            DROP TABLE IF EXISTS bronze_wikipedia;
            CREATE TABLE bronze_wikipedia AS
            SELECT * FROM (VALUES
                ('w1', 12345, 'loc1', 'Test Article', 'http://wiki.org/1', 'Test',
                 37.7, -122.4, 'San Francisco', 'San Francisco County', 'California',
                 0.9, 1, '2024-01-01', 'file1.html', 'hash1', 'img1.jpg', 10,
                 '{}', 'Short', 'Long summary')
            ) AS t(id, pageid, location_id, title, url, categories, latitude, longitude,
                  best_city, best_county, best_state, relevance_score, depth, crawled_at,
                  html_file, file_hash, image_url, links_count, infobox_data,
                  short_summary, long_summary)
        """)
        
        # Should not raise an error (embedding provider is already mocked)
        transformer._apply_transformations('bronze_wikipedia', 'silver_wikipedia_test')
        
        # Verify table was created with NULL neighborhood fields
        results = conn.execute("""
            SELECT page_id, title, neighborhood_names, primary_neighborhood_name, neighborhood_ids
            FROM silver_wikipedia_test
        """).fetchall()
        
        assert len(results) == 1
        assert results[0][0] == 12345  # page_id
        assert results[0][1] == 'Test Article'
        assert results[0][2] is None or results[0][2] == []  # neighborhood_names
        assert results[0][3] is None  # primary_neighborhood_name
        assert results[0][4] is None or results[0][4] == []  # neighborhood_ids