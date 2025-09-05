"""Integration test for Gold layer neighborhood enrichment."""

import pytest
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.gold.wikipedia import WikipediaGoldEnricher
from squack_pipeline_v2.utils.gold_enrichment import (
    GoldNeighborhoodEnricher,
    NeighborhoodSearchFacets,
    NeighborhoodQualityBoost
)


class TestGoldNeighborhoodEnrichment:
    """Test Gold layer neighborhood enrichments."""
    
    @pytest.fixture
    def connection_manager(self):
        """Create DuckDB connection manager."""
        settings = PipelineSettings()
        return DuckDBConnectionManager(settings.duckdb)
    
    @pytest.fixture
    def gold_enricher(self, connection_manager):
        """Create Gold layer Wikipedia enricher."""
        settings = PipelineSettings()
        return WikipediaGoldEnricher(settings, connection_manager)
    
    def test_neighborhood_search_facets(self, connection_manager):
        """Test neighborhood-based search facets generation."""
        conn = connection_manager.get_connection()
        
        # Create test Silver Wikipedia table with neighborhood data
        conn.execute("""
            DROP TABLE IF EXISTS silver_wikipedia_test;
            CREATE TABLE silver_wikipedia_test AS
            SELECT * FROM (VALUES
                ('id1', 12345, 'loc1', 'Golden Gate Park', 'http://wiki.org/1',
                 'Parks', 37.7, -122.4, 'San Francisco', 'SF County', 'CA',
                 0.8, 1, '2024-01-01', 'file1.html', 'hash1', 'img1.jpg', 15,
                 '{}', 'Park article', 'Long summary about park',
                 'embedding_text', NULL, NULL,
                 CAST(['n1', 'n2'] AS VARCHAR[]), 
                 CAST(['Mission District', 'Castro'] AS VARCHAR[]),
                 'Mission District'),
                ('id2', 67890, 'loc2', 'Bay Bridge', 'http://wiki.org/2',
                 'Infrastructure', NULL, NULL, 'San Francisco', 'SF County', 'CA',
                 0.6, 1, '2024-01-01', 'file2.html', 'hash2', 'img2.jpg', 5,
                 '{}', 'Bridge article', 'Long summary about bridge',
                 'embedding_text', NULL, NULL,
                 CAST(NULL AS VARCHAR[]), CAST(NULL AS VARCHAR[]), NULL),
                ('id3', 11111, 'loc3', 'Salesforce Tower', 'http://wiki.org/3',
                 'Buildings', 37.8, -122.3, 'San Francisco', 'SF County', 'CA',
                 0.7, 1, '2024-01-01', 'file3.html', 'hash3', 'img3.jpg', 10,
                 '{}', 'Tower article', 'Long summary about tower',
                 'embedding_text', NULL, NULL,
                 CAST(['n3'] AS VARCHAR[]), 
                 CAST(['SOMA'] AS VARCHAR[]),
                 'SOMA')
            ) AS t(id, page_id, location_id, title, url, categories,
                  latitude, longitude, city, county, state, relevance_score,
                  depth, crawled_at, html_file, file_hash, image_url, links_count,
                  infobox_data, short_summary, long_summary, embedding_text,
                  embedding_vector, embedding_generated_at, neighborhood_ids,
                  neighborhood_names, primary_neighborhood_name)
        """)
        
        # Create Gold view
        enricher = WikipediaGoldEnricher(PipelineSettings(), connection_manager)
        enricher._create_enriched_view('silver_wikipedia_test', 'gold_wikipedia_test')
        
        # Verify search facets include neighborhood filters
        results = conn.execute("""
            SELECT page_id, title, search_facets, neighborhood_count
            FROM gold_wikipedia_test
            ORDER BY page_id
        """).fetchall()
        
        assert len(results) == 3
        
        # Check article with multiple neighborhoods
        article1 = results[1]  # Golden Gate Park
        assert 'multi_neighborhood' in article1[2]
        assert article1[3] == 2  # neighborhood_count
        
        # Check article with no neighborhoods
        article2 = results[2]  # Bay Bridge
        assert 'no_neighborhood' in article2[2]
        assert article2[3] == 0
        
        # Check article with single neighborhood
        article3 = results[0]  # Salesforce Tower
        assert 'has_neighborhood' in article3[2]
        assert article3[3] == 1
    
    def test_quality_score_with_neighborhood_boost(self, connection_manager):
        """Test that quality scores are boosted for articles with neighborhoods."""
        conn = connection_manager.get_connection()
        
        # Create test data with two similar articles, one with neighborhood
        conn.execute("""
            DROP TABLE IF EXISTS silver_wikipedia_quality_test;
            CREATE TABLE silver_wikipedia_quality_test AS
            SELECT * FROM (VALUES
                ('id1', 1, 'loc1', 'Article With Neighborhood', 'http://wiki.org/1',
                 'Test', NULL, NULL, 'SF', 'SF County', 'CA', 0.5, 1, '2024-01-01',
                 'f1.html', 'hash1', 'img1.jpg', 10, '{}', 'content',
                 'A' || REPEAT(' test', 100),  -- 500+ chars for quality score
                 'text', NULL, NULL,
                 CAST(['n1'] AS VARCHAR[]), 
                 CAST(['Test Neighborhood'] AS VARCHAR[]),
                 'Test Neighborhood'),
                ('id2', 2, 'loc2', 'Article Without Neighborhood', 'http://wiki.org/2',
                 'Test', NULL, NULL, 'SF', 'SF County', 'CA', 0.5, 1, '2024-01-01',
                 'f2.html', 'hash2', 'img2.jpg', 10, '{}', 'content',
                 'A' || REPEAT(' test', 100),  -- Same content length
                 'text', NULL, NULL,
                 CAST(NULL AS VARCHAR[]), CAST(NULL AS VARCHAR[]), NULL)
            ) AS t(id, page_id, location_id, title, url, categories,
                  latitude, longitude, city, county, state, relevance_score,
                  depth, crawled_at, html_file, file_hash, image_url, links_count,
                  infobox_data, short_summary, long_summary, embedding_text,
                  embedding_vector, embedding_generated_at, neighborhood_ids,
                  neighborhood_names, primary_neighborhood_name)
        """)
        
        # Create Gold view
        enricher = WikipediaGoldEnricher(PipelineSettings(), connection_manager)
        enricher._create_enriched_view('silver_wikipedia_quality_test', 'gold_quality_test')
        
        # Get quality scores
        results = conn.execute("""
            SELECT page_id, title, article_quality_score, has_neighborhood_association
            FROM gold_quality_test
            ORDER BY page_id
        """).fetchall()
        
        article_with_neighborhood = results[0]
        article_without_neighborhood = results[1]
        
        # Article with neighborhood should have higher quality score
        assert article_with_neighborhood[3] is True  # has_neighborhood_association
        assert article_without_neighborhood[3] is False
        
        # Quality score should be boosted by 0.1 for having a neighborhood
        score_diff = article_with_neighborhood[2] - article_without_neighborhood[2]
        assert abs(score_diff - 0.1) < 0.001  # Account for float precision
    
    def test_search_ranking_with_neighborhood(self, connection_manager):
        """Test that search ranking includes neighborhood component."""
        conn = connection_manager.get_connection()
        
        # Create test data
        conn.execute("""
            DROP TABLE IF EXISTS silver_wikipedia_ranking_test;
            CREATE TABLE silver_wikipedia_ranking_test AS
            SELECT * FROM (VALUES
                ('id1', 1, 'loc1', 'High Quality With Neighborhood', 'http://wiki.org/1',
                 'Test', 37.7, -122.4, 'SF', 'SF County', 'CA', 0.9, 1, '2024-01-01',
                 'f1.html', 'hash1', 'img1.jpg', 20, '{}', 'content',
                 REPEAT('test ', 300),  -- 1500 chars
                 'text', NULL, NULL,
                 CAST(['n1', 'n2'] AS VARCHAR[]), 
                 CAST(['Neighborhood1', 'Neighborhood2'] AS VARCHAR[]),
                 'Neighborhood1'),
                ('id2', 2, 'loc2', 'High Quality No Neighborhood', 'http://wiki.org/2',
                 'Test', 37.7, -122.4, 'SF', 'SF County', 'CA', 0.9, 1, '2024-01-01',
                 'f2.html', 'hash2', 'img2.jpg', 20, '{}', 'content',
                 REPEAT('test ', 300),  -- Same content
                 'text', NULL, NULL,
                 CAST(NULL AS VARCHAR[]), CAST(NULL AS VARCHAR[]), NULL)
            ) AS t(id, page_id, location_id, title, url, categories,
                  latitude, longitude, city, county, state, relevance_score,
                  depth, crawled_at, html_file, file_hash, image_url, links_count,
                  infobox_data, short_summary, long_summary, embedding_text,
                  embedding_vector, embedding_generated_at, neighborhood_ids,
                  neighborhood_names, primary_neighborhood_name)
        """)
        
        # Create Gold view
        enricher = WikipediaGoldEnricher(PipelineSettings(), connection_manager)
        enricher._create_enriched_view('silver_wikipedia_ranking_test', 'gold_ranking_test')
        
        # Get ranking scores
        results = conn.execute("""
            SELECT page_id, title, search_ranking_score, neighborhood_names
            FROM gold_ranking_test
            ORDER BY search_ranking_score DESC
        """).fetchall()
        
        # Article with neighborhoods should rank higher
        assert results[0][0] == 1  # Article with neighborhoods should be first
        assert results[0][3] is not None  # Has neighborhoods
        assert results[1][3] is None  # No neighborhoods
        
        # Ranking difference should reflect neighborhood component
        ranking_diff = results[0][2] - results[1][2]
        assert ranking_diff > 0  # Article with neighborhoods ranks higher
    
    def test_gold_enrichment_utilities(self):
        """Test the Gold layer enrichment utility classes."""
        # Test default configuration
        enricher = GoldNeighborhoodEnricher()
        
        # Test facet SQL generation
        facet_sql = enricher.get_neighborhood_facet_sql()
        assert 'multi_neighborhood' in facet_sql
        assert 'has_neighborhood' in facet_sql
        assert 'no_neighborhood' in facet_sql
        
        # Test quality boost SQL
        boost_sql = enricher.get_neighborhood_quality_boost_sql()
        assert '0.15' in boost_sql  # Multi-neighborhood boost
        assert '0.1' in boost_sql   # Single neighborhood boost
        
        # Test custom configuration
        custom_facets = NeighborhoodSearchFacets(
            has_neighborhood="with_hood",
            no_neighborhood="without_hood",
            multi_neighborhood="many_hoods"
        )
        custom_quality = NeighborhoodQualityBoost(
            has_neighborhood_boost=0.2,
            multi_neighborhood_boost=0.1,
            weight_in_ranking=0.25
        )
        
        custom_enricher = GoldNeighborhoodEnricher(
            facets_config=custom_facets,
            quality_config=custom_quality
        )
        
        # Verify custom configuration
        facet_sql = custom_enricher.get_neighborhood_facet_sql()
        assert 'many_hoods' in facet_sql
        assert 'with_hood' in facet_sql
        
        boost_sql = custom_enricher.get_neighborhood_quality_boost_sql()
        assert '0.3' in boost_sql  # 0.2 + 0.1
        assert '0.2' in boost_sql  # Base boost