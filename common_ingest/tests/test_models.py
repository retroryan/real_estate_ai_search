"""
Test Pydantic models and data validation.
"""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common_ingest.models.base import BaseEnrichedModel, generate_uuid
from common_ingest.models.property import (
    EnrichedProperty,
    EnrichedAddress,
    EnrichedNeighborhood,
    PropertyType,
    PropertyStatus,
    GeoLocation,
    GeoPolygon
)
from common_ingest.models.wikipedia import (
    EnrichedWikipediaArticle,
    WikipediaSummary,
    LocationInfo
)
from common_ingest.models.embedding import (
    EmbeddingData,
    PropertyEmbedding,
    WikipediaEmbedding,
    NeighborhoodEmbedding
)
from common_ingest.utils.logger import setup_logger

logger = setup_logger("test_models")


def test_geo_location_model():
    """Test GeoLocation model validation."""
    logger.info("Testing GeoLocation model...")
    
    # Valid coordinates
    loc = GeoLocation(lat=37.7749, lon=-122.4194)
    assert loc.lat == 37.7749
    assert loc.lon == -122.4194
    
    # Test latitude bounds
    try:
        GeoLocation(lat=91, lon=0)
        assert False, "Should have raised validation error for lat > 90"
    except ValueError:
        pass
    
    try:
        GeoLocation(lat=-91, lon=0)
        assert False, "Should have raised validation error for lat < -90"
    except ValueError:
        pass
    
    # Test longitude bounds
    try:
        GeoLocation(lat=0, lon=181)
        assert False, "Should have raised validation error for lon > 180"
    except ValueError:
        pass
    
    try:
        GeoLocation(lat=0, lon=-181)
        assert False, "Should have raised validation error for lon < -180"
    except ValueError:
        pass
    
    logger.info("✅ GeoLocation model test passed")
    return True


def test_enriched_address_model():
    """Test EnrichedAddress model."""
    logger.info("Testing EnrichedAddress model...")
    
    address = EnrichedAddress(
        street="123 Main St",
        city="San Francisco",
        state="California",
        zip_code="94102",
        coordinates=GeoLocation(lat=37.7749, lon=-122.4194)
    )
    
    assert address.street == "123 Main St"
    assert address.city == "San Francisco"
    assert address.state == "California"
    assert address.zip_code == "94102"
    assert address.coordinates.lat == 37.7749
    
    # Test without coordinates
    address2 = EnrichedAddress(
        street="456 Oak Ave",
        city="Park City",
        state="Utah",
        zip_code="84060"
    )
    assert address2.coordinates is None
    
    logger.info("✅ EnrichedAddress model test passed")
    return True


def test_enriched_property_model():
    """Test EnrichedProperty model with all fields."""
    logger.info("Testing EnrichedProperty model...")
    
    prop = EnrichedProperty(
        listing_id="test_001",
        property_type=PropertyType.HOUSE,
        price=Decimal("1500000"),
        bedrooms=4,
        bathrooms=3.5,
        square_feet=2500,
        year_built=2010,
        lot_size=5000,
        address=EnrichedAddress(
            street="789 Pine St",
            city="San Francisco",
            state="California",
            zip_code="94103"
        ),
        features=["pool", "garage", "garden"],
        amenities=["gym", "spa"],
        description="Beautiful home in the heart of SF",
        status=PropertyStatus.ACTIVE,
        images=["image1.jpg", "image2.jpg"],
        virtual_tour_url="https://example.com/tour",
        mls_number="MLS123456",
        hoa_fee=Decimal("500")
    )
    
    assert prop.listing_id == "test_001"
    assert prop.property_type == PropertyType.HOUSE
    assert prop.price == Decimal("1500000")
    assert prop.bedrooms == 4
    assert prop.bathrooms == 3.5
    assert prop.square_feet == 2500
    assert prop.year_built == 2010
    assert prop.lot_size == 5000
    assert len(prop.features) == 3
    assert len(prop.amenities) == 2
    assert prop.status == PropertyStatus.ACTIVE
    assert prop.embedding_id is not None  # Should be auto-generated
    
    # Test UUID generation
    assert isinstance(uuid.UUID(prop.embedding_id), uuid.UUID)
    
    logger.info("✅ EnrichedProperty model test passed")
    return True


def test_enriched_neighborhood_model():
    """Test EnrichedNeighborhood model."""
    logger.info("Testing EnrichedNeighborhood model...")
    
    # Create a polygon with at least 3 points
    boundaries = GeoPolygon(points=[
        GeoLocation(lat=37.7749, lon=-122.4194),
        GeoLocation(lat=37.7750, lon=-122.4195),
        GeoLocation(lat=37.7751, lon=-122.4193),
        GeoLocation(lat=37.7749, lon=-122.4194)  # Close the polygon
    ])
    
    neighborhood = EnrichedNeighborhood(
        neighborhood_id="sf_mission",
        name="Mission District",
        city="San Francisco",
        state="California",
        boundaries=boundaries,
        center_point=GeoLocation(lat=37.7750, lon=-122.4194),
        demographics={"population": 50000, "median_income": 85000},
        poi_count=150,
        description="Vibrant cultural district",
        characteristics=["historic", "cultural", "vibrant"]
    )
    
    assert neighborhood.neighborhood_id == "sf_mission"
    assert neighborhood.name == "Mission District"
    assert neighborhood.city == "San Francisco"
    assert neighborhood.state == "California"
    assert len(neighborhood.boundaries.points) == 4
    assert neighborhood.poi_count == 150
    assert len(neighborhood.characteristics) == 3
    assert neighborhood.embedding_id is not None
    
    logger.info("✅ EnrichedNeighborhood model test passed")
    return True


def test_wikipedia_article_model():
    """Test EnrichedWikipediaArticle model."""
    logger.info("Testing EnrichedWikipediaArticle model...")
    
    article = EnrichedWikipediaArticle(
        page_id=12345,
        article_id=1,
        title="San Francisco",
        url="https://en.wikipedia.org/wiki/San_Francisco",
        full_text="San Francisco is a city in California...",
        relevance_score=0.95,
        location=LocationInfo(
            city="San Francisco",
            state="California",
            country="United States",
            latitude=37.7749,
            longitude=-122.4194
        ),
        depth=2
    )
    
    assert article.page_id == 12345
    assert article.article_id == 1
    assert article.title == "San Francisco"
    assert article.url == "https://en.wikipedia.org/wiki/San_Francisco"
    assert article.relevance_score == 0.95
    assert article.location.city == "San Francisco"
    assert article.location.latitude == 37.7749
    assert article.depth == 2
    assert article.embedding_id is not None
    
    logger.info("✅ EnrichedWikipediaArticle model test passed")
    return True


def test_wikipedia_summary_model():
    """Test WikipediaSummary model."""
    logger.info("Testing WikipediaSummary model...")
    
    summary = WikipediaSummary(
        page_id=12345,
        article_title="San Francisco",
        short_summary="San Francisco is a major city in California.",
        long_summary="San Francisco, officially the City and County of San Francisco, is a major city in California...",
        key_topics=["technology", "culture", "tourism", "finance"],
        best_city="San Francisco",
        best_county="San Francisco County",
        best_state="California",
        overall_confidence=0.92
    )
    
    assert summary.page_id == 12345
    assert summary.article_title == "San Francisco"
    assert len(summary.key_topics) == 4
    assert summary.best_city == "San Francisco"
    assert summary.best_state == "California"
    assert summary.overall_confidence == 0.92
    assert summary.embedding_id is not None
    
    # Test key topic normalization
    summary2 = WikipediaSummary(
        page_id=67890,
        article_title="Test Article",
        key_topics=["Tech", "tech", "TECH", "culture", "Culture"]
    )
    # Should deduplicate case-insensitive
    assert len(summary2.key_topics) == 2
    assert "Tech" in summary2.key_topics or "tech" in summary2.key_topics
    assert "culture" in summary2.key_topics or "Culture" in summary2.key_topics
    
    logger.info("✅ WikipediaSummary model test passed")
    return True


def test_embedding_models():
    """Test embedding data models."""
    logger.info("Testing embedding models...")
    
    # Test base EmbeddingData
    embedding_data = EmbeddingData(
        embedding_id="emb_123",
        vector=[0.1, 0.2, 0.3, 0.4, 0.5],
        dimension=5,
        model_name="text-embedding-ada-002",
        provider="openai",
        created_at=datetime.now()
    )
    
    assert embedding_data.embedding_id == "emb_123"
    assert len(embedding_data.vector) == 5
    assert embedding_data.dimension == 5
    assert embedding_data.model_name == "text-embedding-ada-002"
    
    # Test PropertyEmbedding
    prop_embedding = PropertyEmbedding(
        embedding_id="prop_emb_123",
        listing_id="prop_001",
        vector=[0.1, 0.2, 0.3],
        text="Beautiful home with ocean view",
        metadata={"chunk_index": 0}
    )
    
    assert prop_embedding.listing_id == "prop_001"
    assert prop_embedding.embedding_id == "prop_emb_123"
    assert len(prop_embedding.vector) == 3
    
    # Test WikipediaEmbedding
    wiki_embedding = WikipediaEmbedding(
        embedding_id="wiki_emb_123",
        page_id=12345,
        vector=[0.4, 0.5, 0.6],
        text="San Francisco is a city...",
        metadata={"chunk_index": 1}
    )
    
    assert wiki_embedding.page_id == 12345
    assert wiki_embedding.embedding_id == "wiki_emb_123"
    
    logger.info("✅ Embedding models test passed")
    return True


def test_property_type_enum():
    """Test PropertyType enum values."""
    logger.info("Testing PropertyType enum...")
    
    assert PropertyType.HOUSE.value == "house"
    assert PropertyType.CONDO.value == "condo"
    assert PropertyType.APARTMENT.value == "apartment"
    assert PropertyType.TOWNHOUSE.value == "townhouse"
    assert PropertyType.LAND.value == "land"
    assert PropertyType.COMMERCIAL.value == "commercial"
    assert PropertyType.OTHER.value == "other"
    
    # Test creating from value
    assert PropertyType("house") == PropertyType.HOUSE
    assert PropertyType("condo") == PropertyType.CONDO
    
    logger.info("✅ PropertyType enum test passed")
    return True


def test_property_status_enum():
    """Test PropertyStatus enum values."""
    logger.info("Testing PropertyStatus enum...")
    
    assert PropertyStatus.ACTIVE.value == "active"
    assert PropertyStatus.PENDING.value == "pending"
    assert PropertyStatus.SOLD.value == "sold"
    assert PropertyStatus.OFF_MARKET.value == "off_market"
    
    # Test creating from value
    assert PropertyStatus("active") == PropertyStatus.ACTIVE
    assert PropertyStatus("sold") == PropertyStatus.SOLD
    
    logger.info("✅ PropertyStatus enum test passed")
    return True


def run_all_tests():
    """Run all model tests."""
    logger.info("=" * 60)
    logger.info("Running Model Tests")
    logger.info("=" * 60)
    
    tests = [
        test_geo_location_model,
        test_enriched_address_model,
        test_enriched_property_model,
        test_enriched_neighborhood_model,
        test_wikipedia_article_model,
        test_wikipedia_summary_model,
        test_embedding_models,
        test_property_type_enum,
        test_property_status_enum
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test {test.__name__} failed: {e}")
            failed += 1
    
    logger.info("=" * 60)
    logger.info(f"Test Results: {passed} passed, {failed} failed")
    logger.info("=" * 60)
    
    if failed == 0:
        logger.info("🎉 All model tests passed!")
    else:
        logger.error(f"⚠️ {failed} tests failed")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)