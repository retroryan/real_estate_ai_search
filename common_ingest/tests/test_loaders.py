"""
Test data loaders with enrichment functionality.
"""

import pytest
import tempfile
import json
import sqlite3
from pathlib import Path
from decimal import Decimal

from common_ingest.loaders.property_loader import PropertyLoader
from common_ingest.loaders.neighborhood_loader import NeighborhoodLoader
from common_ingest.loaders.wikipedia_loader import WikipediaLoader
from common_ingest.models.property import (
    EnrichedProperty,
    EnrichedNeighborhood,
    PropertyType,
    PropertyStatus
)
from common_ingest.models.wikipedia import (
    EnrichedWikipediaArticle,
    WikipediaSummary
)
from common_ingest.utils.logger import setup_logger

logger = setup_logger("test_loaders")


def test_property_loader():
    """Test PropertyLoader returns enriched Pydantic models."""
    logger.info("Testing PropertyLoader...")
    
    # Create test data
    test_data = {
        "properties_sf.json": [
            {
                "listing_id": "sf_001",
                "property_type": "single_family",
                "price": 1500000,
                "bedrooms": 4,
                "bathrooms": 3.5,
                "square_feet": 2500,
                "address": {
                    "street": "123 Market St",
                    "city": "SF",  # Should be expanded to San Francisco
                    "state": "CA",  # Should be expanded to California
                    "zip_code": "94102"
                },
                "features": ["pool", "Pool", "garage", "Garage"],  # Should be deduplicated
                "amenities": ["gym", "Gym", "spa"],  # Should be deduplicated
                "description": "Beautiful home in SF"
            }
        ]
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Write test data
        for filename, data in test_data.items():
            file_path = temp_path / filename
            with open(file_path, 'w') as f:
                json.dump(data, f)
        
        # Load properties
        loader = PropertyLoader(temp_path)
        properties = loader.load_all()
        
        # Validate results
        assert len(properties) == 1, f"Expected 1 property, got {len(properties)}"
        
        prop = properties[0]
        assert isinstance(prop, EnrichedProperty), f"Expected EnrichedProperty, got {type(prop)}"
        
        # Check enrichment was applied
        assert prop.address.city == "San Francisco", f"City not expanded: {prop.address.city}"
        assert prop.address.state == "California", f"State not expanded: {prop.address.state}"
        
        # Check features were normalized (lowercase, deduplicated, sorted)
        assert prop.features == ["garage", "pool"], f"Features not normalized: {prop.features}"
        assert prop.amenities == ["gym", "spa"], f"Amenities not normalized: {prop.amenities}"
        
        # Check other fields
        assert prop.listing_id == "sf_001"
        assert prop.property_type == PropertyType.HOUSE  # single_family mapped to house
        assert prop.price == Decimal("1500000")
        assert prop.bedrooms == 4
        assert prop.bathrooms == 3.5
        assert prop.square_feet == 2500
        
        logger.info("✅ PropertyLoader test passed")


def test_neighborhood_loader():
    """Test NeighborhoodLoader returns enriched Pydantic models."""
    logger.info("Testing NeighborhoodLoader...")
    
    # Create test data
    test_data = {
        "neighborhoods_sf.json": [
            {
                "name": "Mission District",
                "city": "SF",  # Should be expanded
                "state": "CA",  # Should be expanded
                "center_point": {
                    "lat": 37.7599,
                    "lon": -122.4148
                },
                "characteristics": ["vibrant", "Vibrant", "cultural", "Cultural"],  # Should be deduplicated
                "poi_count": 150,
                "description": "Historic neighborhood in San Francisco"
            }
        ]
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Write test data
        for filename, data in test_data.items():
            file_path = temp_path / filename
            with open(file_path, 'w') as f:
                json.dump(data, f)
        
        # Load neighborhoods
        loader = NeighborhoodLoader(temp_path)
        neighborhoods = loader.load_all()
        
        # Validate results
        assert len(neighborhoods) == 1, f"Expected 1 neighborhood, got {len(neighborhoods)}"
        
        neighborhood = neighborhoods[0]
        assert isinstance(neighborhood, EnrichedNeighborhood), f"Expected EnrichedNeighborhood, got {type(neighborhood)}"
        
        # Check enrichment was applied
        assert neighborhood.city == "San Francisco", f"City not expanded: {neighborhood.city}"
        assert neighborhood.state == "California", f"State not expanded: {neighborhood.state}"
        
        # Check characteristics were normalized
        assert neighborhood.characteristics == ["cultural", "vibrant"], f"Characteristics not normalized: {neighborhood.characteristics}"
        
        # Check other fields
        assert neighborhood.name == "Mission District"
        assert neighborhood.poi_count == 150
        assert neighborhood.center_point is not None
        assert neighborhood.center_point.lat == 37.7599
        assert neighborhood.center_point.lon == -122.4148
        
        logger.info("✅ NeighborhoodLoader test passed")


def test_wikipedia_loader():
    """Test WikipediaLoader returns enriched Wikipedia models."""
    logger.info("Testing WikipediaLoader...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        db_path = temp_path / "wikipedia.db"
        
        # Create test database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create articles table
        cursor.execute("""
            CREATE TABLE articles (
                id INTEGER PRIMARY KEY,
                page_id INTEGER UNIQUE,
                title TEXT NOT NULL,
                url TEXT,
                full_text TEXT,
                depth INTEGER,
                relevance_score REAL,
                latitude REAL,
                longitude REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create page_summaries table
        cursor.execute("""
            CREATE TABLE page_summaries (
                page_id INTEGER PRIMARY KEY,
                article_id INTEGER NOT NULL,
                summary TEXT NOT NULL,
                key_topics TEXT,
                best_city TEXT,
                best_county TEXT,
                best_state TEXT,
                overall_confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            )
        """)
        
        # Insert test article
        cursor.execute("""
            INSERT INTO articles (id, page_id, title, url, full_text, relevance_score, latitude, longitude)
            VALUES (1, 12345, 'Park City, Utah', '/wiki/Park_City,_Utah', 
                    'Park City is a city in Summit County, Utah...', 0.95, 40.6461, -111.4980)
        """)
        
        # Insert test summary
        cursor.execute("""
            INSERT INTO page_summaries (page_id, article_id, summary, key_topics, best_city, best_state, overall_confidence)
            VALUES (12345, 1, 'Park City is a mountain resort town...', 
                    '["skiing", "Skiing", "resort", "Resort", "olympics"]',
                    'Park City', 'UT', 0.92)
        """)
        
        conn.commit()
        conn.close()
        
        # Load Wikipedia data
        loader = WikipediaLoader(db_path)
        
        # Test loading articles
        articles = loader.load_all()
        assert len(articles) == 1, f"Expected 1 article, got {len(articles)}"
        
        article = articles[0]
        assert isinstance(article, EnrichedWikipediaArticle), f"Expected EnrichedWikipediaArticle, got {type(article)}"
        
        # Check article fields
        assert article.page_id == 12345
        assert article.article_id == 1
        assert article.title == "Park City, Utah"
        assert article.url == "https://en.wikipedia.org/wiki/Park_City,_Utah"
        assert article.relevance_score == 0.95
        assert article.location.latitude == 40.6461
        assert article.location.longitude == -111.4980
        
        # Check location parsing from title
        assert article.location.city == "Park City"
        assert article.location.state == "Utah"
        
        # Test loading summaries
        summaries = loader.load_summaries()
        assert len(summaries) == 1, f"Expected 1 summary, got {len(summaries)}"
        
        summary = summaries[0]
        assert isinstance(summary, WikipediaSummary), f"Expected WikipediaSummary, got {type(summary)}"
        
        # Check summary fields
        assert summary.page_id == 12345
        assert summary.best_city == "Park City"
        assert summary.best_state == "Utah"  # Should be expanded from UT
        assert summary.overall_confidence == 0.92
        
        # Check key topics were normalized (lowercase, deduplicated, sorted)
        assert summary.key_topics == ["olympics", "resort", "skiing"], f"Key topics not normalized: {summary.key_topics}"
        
        logger.info("✅ WikipediaLoader test passed")


def test_city_filtering():
    """Test that city filtering works correctly."""
    logger.info("Testing city filtering...")
    
    # Create test data with mixed cities
    test_data = {
        "properties_sf.json": [
            {
                "listing_id": "sf_001",
                "property_type": "condo",
                "price": 800000,
                "bedrooms": 2,
                "bathrooms": 2,
                "address": {
                    "street": "456 Mission St",
                    "city": "SF",
                    "state": "CA",
                    "zip_code": "94103"
                }
            }
        ],
        "properties_pc.json": [
            {
                "listing_id": "pc_001",
                "property_type": "single_family",
                "price": 2500000,
                "bedrooms": 5,
                "bathrooms": 4,
                "address": {
                    "street": "789 Main St",
                    "city": "Park City",
                    "state": "UT",
                    "zip_code": "84060"
                }
            }
        ]
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Write test data
        for filename, data in test_data.items():
            file_path = temp_path / filename
            with open(file_path, 'w') as f:
                json.dump(data, f)
        
        # Load properties with filtering
        loader = PropertyLoader(temp_path)
        
        # Test filtering for SF
        sf_properties = loader.load_by_filter(city="SF")
        assert len(sf_properties) == 1, f"Expected 1 SF property, got {len(sf_properties)}"
        assert sf_properties[0].address.city == "San Francisco"
        assert sf_properties[0].address.state == "California"
        
        # Test filtering for Park City
        pc_properties = loader.load_by_filter(city="Park City")
        assert len(pc_properties) == 1, f"Expected 1 PC property, got {len(pc_properties)}"
        assert pc_properties[0].address.city == "Park City"
        assert pc_properties[0].address.state == "Utah"
        
        # Test loading all
        all_properties = loader.load_all()
        assert len(all_properties) == 2, f"Expected 2 properties total, got {len(all_properties)}"
        
        logger.info("✅ City filtering test passed")


def test_location_filtering_wikipedia():
    """Test location-based filtering for Wikipedia data."""
    logger.info("Testing Wikipedia location filtering...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        db_path = temp_path / "wikipedia.db"
        
        # Create test database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE articles (
                id INTEGER PRIMARY KEY,
                page_id INTEGER UNIQUE,
                title TEXT NOT NULL,
                url TEXT,
                full_text TEXT,
                depth INTEGER,
                relevance_score REAL,
                latitude REAL,
                longitude REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE page_summaries (
                page_id INTEGER PRIMARY KEY,
                article_id INTEGER NOT NULL,
                summary TEXT NOT NULL,
                key_topics TEXT,
                best_city TEXT,
                best_county TEXT,
                best_state TEXT,
                overall_confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            )
        """)
        
        # Insert multiple articles
        cursor.execute("""
            INSERT INTO articles (id, page_id, title, url, full_text, relevance_score)
            VALUES (1, 11111, 'San Francisco', '/wiki/San_Francisco', 'SF article', 0.9)
        """)
        
        cursor.execute("""
            INSERT INTO articles (id, page_id, title, url, full_text, relevance_score)
            VALUES (2, 22222, 'Park City, Utah', '/wiki/Park_City,_Utah', 'PC article', 0.95)
        """)
        
        # Insert summaries
        cursor.execute("""
            INSERT INTO page_summaries (page_id, article_id, summary, best_city, best_state, overall_confidence)
            VALUES (11111, 1, 'SF summary', 'San Francisco', 'CA', 0.9)
        """)
        
        cursor.execute("""
            INSERT INTO page_summaries (page_id, article_id, summary, best_city, best_state, overall_confidence)
            VALUES (22222, 2, 'PC summary', 'Park City', 'UT', 0.92)
        """)
        
        conn.commit()
        conn.close()
        
        # Test filtering
        loader = WikipediaLoader(db_path)
        
        # Filter by city
        sf_summaries = loader.load_summaries_by_location(city="San Francisco")
        assert len(sf_summaries) == 1, f"Expected 1 SF summary, got {len(sf_summaries)}"
        assert sf_summaries[0].best_city == "San Francisco"
        
        pc_summaries = loader.load_summaries_by_location(city="Park City")
        assert len(pc_summaries) == 1, f"Expected 1 PC summary, got {len(pc_summaries)}"
        assert pc_summaries[0].best_city == "Park City"
        
        # Filter by state
        ca_summaries = loader.load_summaries_by_location(state="CA")
        assert len(ca_summaries) == 1, f"Expected 1 CA summary, got {len(ca_summaries)}"
        assert ca_summaries[0].best_state == "California"  # Should be expanded
        
        ut_summaries = loader.load_summaries_by_location(state="UT")
        assert len(ut_summaries) == 1, f"Expected 1 UT summary, got {len(ut_summaries)}"
        assert ut_summaries[0].best_state == "Utah"  # Should be expanded
        
        logger.info("✅ Wikipedia location filtering test passed")