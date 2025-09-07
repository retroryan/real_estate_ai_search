"""Integration tests for the new modular Elasticsearch writer."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, date

from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.settings import PipelineSettings, DuckDBConfig
from squack_pipeline_v2.writers.elastic import ElasticsearchWriter
from squack_pipeline_v2.writers.elastic.property import PropertyDocument, transform_property
from squack_pipeline_v2.writers.elastic.neighborhood import NeighborhoodDocument, transform_neighborhood
from squack_pipeline_v2.writers.elastic.wikipedia import WikipediaDocument, transform_wikipedia


class TestElasticsearchWriter:
    """Test the new modular Elasticsearch writer implementation."""
    
    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return PipelineSettings()
    
    @pytest.fixture
    def connection_manager(self, settings):
        """Create a test connection manager with in-memory database."""
        return DuckDBConnectionManager(DuckDBConfig(database_file=":memory:"))
    
    @pytest.fixture
    def setup_test_data(self, connection_manager):
        """Set up test data in DuckDB."""
        conn = connection_manager.get_connection()
        
        # Drop tables/views if they exist
        conn.execute("DROP VIEW IF EXISTS gold_properties")
        conn.execute("DROP TABLE IF EXISTS gold_properties")
        conn.execute("DROP VIEW IF EXISTS gold_neighborhoods")
        conn.execute("DROP TABLE IF EXISTS gold_neighborhoods")
        conn.execute("DROP VIEW IF EXISTS gold_wikipedia")
        conn.execute("DROP TABLE IF EXISTS gold_wikipedia")
        
        # Create gold_properties table
        conn.execute("""
            CREATE TABLE gold_properties AS
            SELECT 
                'prop-1' as listing_id,
                'nbh-1' as neighborhood_id,
                500000.0 as price,
                3 as bedrooms,
                2.5 as bathrooms,
                2000 as square_feet,
                'single_family' as property_type,
                2020 as year_built,
                5000 as lot_size,
                {'street': '123 Main St', 'city': 'San Francisco', 'state': 'CA', 
                 'zip_code': '94105', 'location': [-122.4, 37.7]}::JSON as address,
                250.0 as price_per_sqft,
                {'spaces': 2, 'type': 'garage'}::JSON as parking,
                'Beautiful home' as description,
                ['hardwood floors', 'updated kitchen']::VARCHAR[] as features,
                ['pool', 'gym']::VARCHAR[] as amenities,
                'active' as status,
                ['luxury', 'downtown']::VARCHAR[] as search_tags,
                DATE '2024-01-01' as listing_date,
                30 as days_on_market,
                'https://example.com/tour' as virtual_tour_url,
                ['https://example.com/img1.jpg']::VARCHAR[] as images,
                ARRAY[0.1, 0.2, 0.3]::FLOAT[] as embedding_vector,
                NOW() as embedding_generated_at
        """)
        
        # Create gold_neighborhoods table
        conn.execute("""
            CREATE TABLE gold_neighborhoods AS
            SELECT
                'nbh-1' as neighborhood_id,
                'Downtown' as name,
                'San Francisco' as city,
                'CA' as state,
                50000 as population,
                95.0 as walkability_score,
                8.5 as school_rating,
                85.0 as overall_livability_score,
                37.7 as center_latitude,
                -122.4 as center_longitude,
                'Urban downtown area' as description,
                ['restaurants', 'shops']::VARCHAR[] as amenities,
                ['urban', 'walkable']::VARCHAR[] as lifestyle_tags,
                {'median_age': 35}::JSON as demographics,
                NULL as wikipedia_correlations,
                ARRAY[0.4, 0.5, 0.6]::FLOAT[] as embedding_vector,
                NOW() as embedding_generated_at
        """)
        
        # Create gold_wikipedia table
        conn.execute("""
            CREATE TABLE gold_wikipedia AS
            SELECT
                12345 as page_id,
                'San Francisco' as title,
                'https://en.wikipedia.org/wiki/San_Francisco' as url,
                'san_francisco.json' as article_filename,
                'San Francisco is a city...' as long_summary,
                'SF is a major city' as short_summary,
                10000 as content_length,
                true as content_loaded,
                NOW() as content_loaded_at,
                '["History", "Geography"]'::VARCHAR as categories,
                ['technology', 'tourism']::VARCHAR[] as key_topics,
                0.95 as relevance_score,
                0.9 as article_quality_score,
                'high' as article_quality,
                'San Francisco' as city,
                'CA' as state,
                NOW() as last_updated,
                ARRAY[0.7, 0.8, 0.9]::FLOAT[] as embedding_vector,
                NOW() as embedding_generated_at
        """)
        
        return connection_manager
    
    def test_property_transformation(self):
        """Test property document transformation."""
        record = {
            'listing_id': 'prop-1',
            'neighborhood_id': 'nbh-1',
            'price': 500000.0,
            'bedrooms': 3,
            'bathrooms': 2.5,
            'square_feet': 2000,
            'property_type': 'single_family',
            'year_built': 2020,
            'lot_size': 5000,
            'address': {
                'street': '123 Main St',
                'city': 'San Francisco',
                'state': 'CA',
                'zip_code': '94105',
                'location': [-122.4, 37.7]
            },
            'price_per_sqft': 250.0,
            'parking': {'spaces': 2, 'type': 'garage'},
            'description': 'Beautiful home',
            'features': ['hardwood floors', 'updated kitchen'],
            'amenities': ['pool', 'gym'],
            'status': 'active',
            'search_tags': ['luxury', 'downtown'],
            'listing_date': date(2024, 1, 1),
            'days_on_market': 30,
            'virtual_tour_url': 'https://example.com/tour',
            'images': ['https://example.com/img1.jpg'],
            'embedding_vector': (0.1, 0.2, 0.3),
            'embedding_generated_at': datetime.now()
        }
        
        # Transform to PropertyDocument
        doc = transform_property(record, 'test-model')
        
        # Verify transformation
        assert doc.listing_id == 'prop-1'
        assert doc.price == 500000.0
        assert doc.bedrooms == 3
        assert doc.address.street == '123 Main St'
        assert doc.address.location.lat == 37.7
        assert doc.address.location.lon == -122.4
        assert doc.parking.spaces == 2
        assert doc.parking.type == 'garage'
        assert doc.embedding == [0.1, 0.2, 0.3]  # Tuple converted to list
        assert doc.listing_date == '2024-01-01'  # Date converted to string
        assert doc.embedding_model == 'test-model'
        
    def test_neighborhood_transformation(self):
        """Test neighborhood document transformation."""
        record = {
            'neighborhood_id': 'nbh-1',
            'name': 'Downtown',
            'city': 'San Francisco',
            'state': 'CA',
            'population': 50000,
            'walkability_score': 95.0,
            'school_rating': 8.5,
            'overall_livability_score': 85.0,
            'center_latitude': 37.7,
            'center_longitude': -122.4,
            'description': 'Urban downtown area',
            'amenities': ['restaurants', 'shops'],
            'lifestyle_tags': ['urban', 'walkable'],
            'demographics': {'median_age': 35},
            'wikipedia_correlations': None,
            'embedding_vector': (0.4, 0.5, 0.6),
            'embedding_generated_at': datetime.now()
        }
        
        # Transform to NeighborhoodDocument
        doc = transform_neighborhood(record, 'test-model')
        
        # Verify transformation
        assert doc.neighborhood_id == 'nbh-1'
        assert doc.name == 'Downtown'
        assert doc.location.lat == 37.7
        assert doc.location.lon == -122.4
        assert doc.embedding == [0.4, 0.5, 0.6]  # Tuple converted to list
        assert doc.embedding_model == 'test-model'
        
    def test_wikipedia_transformation(self):
        """Test Wikipedia document transformation."""
        record = {
            'page_id': 12345,
            'title': 'San Francisco',
            'url': 'https://en.wikipedia.org/wiki/San_Francisco',
            'article_filename': 'san_francisco.json',
            'long_summary': 'San Francisco is a city...',
            'short_summary': 'SF is a major city',
            'content_length': 10000,
            'content_loaded': True,
            'content_loaded_at': datetime.now(),
            'categories': '["History", "Geography"]',
            'key_topics': ['technology', 'tourism'],
            'relevance_score': 0.95,
            'article_quality_score': 0.9,
            'article_quality': 'high',
            'city': 'San Francisco',
            'state': 'CA',
            'last_updated': datetime.now(),
            'embedding_vector': (0.7, 0.8, 0.9),
            'embedding_generated_at': datetime.now()
        }
        
        # Transform to WikipediaDocument
        doc = transform_wikipedia(record, 'test-model')
        
        # Verify transformation
        assert doc.page_id == '12345'  # Int converted to string
        assert doc.title == 'San Francisco'
        assert doc.categories == ['History', 'Geography']  # JSON parsed
        assert doc.embedding == [0.7, 0.8, 0.9]  # Tuple converted to list
        assert doc.embedding_model == 'test-model'
    
    @patch('squack_pipeline_v2.writers.elastic.base.Elasticsearch')
    def test_elasticsearch_writer_initialization(self, mock_es, settings, connection_manager):
        """Test ElasticsearchWriter initialization."""
        # Mock Elasticsearch client
        mock_es_instance = MagicMock()
        mock_es_instance.ping.return_value = True
        mock_es.return_value = mock_es_instance
        
        # Create writer
        writer = ElasticsearchWriter(connection_manager, settings)
        
        # Verify initialization
        assert writer.property_writer is not None
        assert writer.neighborhood_writer is not None
        assert writer.wikipedia_writer is not None
        assert writer.documents_indexed == 0
    
    @patch('squack_pipeline_v2.writers.elastic.base.bulk')
    @patch('squack_pipeline_v2.writers.elastic.base.Elasticsearch')
    def test_index_all(self, mock_es, mock_bulk, settings, setup_test_data):
        """Test indexing all entity types."""
        # Mock Elasticsearch client
        mock_es_instance = MagicMock()
        mock_es_instance.ping.return_value = True
        mock_es.return_value = mock_es_instance
        
        # Mock bulk indexing to return success
        mock_bulk.return_value = (1, [])  # 1 success, no failures
        
        # Create writer
        writer = ElasticsearchWriter(setup_test_data, settings)
        
        # Index all entities
        stats = writer.index_all()
        
        # Verify indexing was attempted for all entity types
        assert 'entities' in stats
        assert 'properties' in stats['entities']
        assert 'neighborhoods' in stats['entities']
        assert 'wikipedia' in stats['entities']
        
        # Verify bulk was called (3 times, once for each entity type)
        assert mock_bulk.call_count == 3
    
    def test_duckdb_streaming(self, setup_test_data):
        """Test that DuckDB streaming with fetchmany works correctly."""
        conn = setup_test_data.get_connection()
        
        # Execute query
        results = conn.execute("SELECT * FROM gold_properties")
        
        # Test fetchmany streaming
        batch = results.fetchmany(10)
        assert len(batch) == 1  # We only have 1 test record
        
        # Second fetchmany should return empty
        batch = results.fetchmany(10)
        assert len(batch) == 0
    
    def test_pydantic_models_validation(self):
        """Test Pydantic model validation."""
        from squack_pipeline_v2.writers.elastic.property import GeoPoint, AddressInfo, ParkingInfo
        
        # Test GeoPoint validation
        geo = GeoPoint(lat=37.7, lon=-122.4)
        assert geo.lat == 37.7
        assert geo.lon == -122.4
        
        # Test invalid latitude
        with pytest.raises(ValueError):
            GeoPoint(lat=91, lon=-122.4)  # lat > 90
        
        # Test AddressInfo
        addr = AddressInfo(
            street="123 Main St",
            city="SF",
            state="CA",
            zip_code="94105",
            location=geo
        )
        assert addr.city == "SF"
        
        # Test ParkingInfo
        parking = ParkingInfo(spaces=2, type="garage")
        assert parking.spaces == 2
        
    def test_modular_structure(self):
        """Test that the modular structure is correctly implemented."""
        # Import all modules to verify structure
        from squack_pipeline_v2.writers.elastic import ElasticsearchWriter
        from squack_pipeline_v2.writers.elastic.base import ElasticsearchWriterBase
        from squack_pipeline_v2.writers.elastic.property import PropertyWriter, PropertyDocument
        from squack_pipeline_v2.writers.elastic.neighborhood import NeighborhoodWriter, NeighborhoodDocument
        from squack_pipeline_v2.writers.elastic.wikipedia import WikipediaWriter, WikipediaDocument
        from squack_pipeline_v2.writers.elastic.writer import ElasticsearchWriter as UnifiedWriter
        
        # Verify all classes are importable
        assert ElasticsearchWriter is not None
        assert ElasticsearchWriterBase is not None
        assert PropertyWriter is not None
        assert NeighborhoodWriter is not None
        assert WikipediaWriter is not None
        assert UnifiedWriter is not None
        
        # Verify unified writer is the exported one
        assert ElasticsearchWriter == UnifiedWriter