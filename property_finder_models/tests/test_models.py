"""
Unit tests for Property Finder models.

Tests model instantiation, validation, and serialization.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from typing import List

from property_finder_models import (
    # Core
    BaseEnrichedModel,
    BaseMetadata,
    generate_uuid,
    # Enums
    PropertyType,
    PropertyStatus,
    EntityType,
    SourceType,
    EmbeddingProvider,
    ChunkingMethod,
    # Geographic
    GeoLocation,
    GeoPolygon,
    EnrichedAddress,
    LocationInfo,
    # Entities
    EnrichedProperty,
    EnrichedNeighborhood,
    EnrichedWikipediaArticle,
    WikipediaSummary,
    # Embeddings
    EmbeddingData,
    PropertyEmbedding,
    # Config
    EmbeddingConfig,
    ChromaDBConfig,
    ChunkingConfig,
    ProcessingConfig,
    Config,
    # API
    PaginationParams,
    PropertyFilter,
    ResponseMetadata,
    ErrorResponse,
    # Exceptions
    PropertyFinderError,
    ValidationError,
)


class TestCoreModels:
    """Test core base models."""
    
    def test_base_enriched_model(self):
        """Test BaseEnrichedModel instantiation."""
        model = BaseEnrichedModel()
        assert isinstance(model.created_at, datetime)
        assert model.enrichment_version == "1.0.0"
    
    def test_base_metadata(self):
        """Test BaseMetadata instantiation."""
        model = BaseMetadata(
            source_file="test.json",
            source_collection="test_collection",
            source_timestamp=datetime.utcnow(),
            embedding_model="test-model",
            embedding_dimension=384,
            text_hash="abcd1234"
        )
        assert model.embedding_id is not None
        assert model.embedding_version == "1.0"
    
    def test_generate_uuid(self):
        """Test UUID generation."""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        assert uuid1 != uuid2
        assert len(uuid1) == 36  # Standard UUID length


class TestGeographicModels:
    """Test geographic models."""
    
    def test_geo_location(self):
        """Test GeoLocation validation."""
        loc = GeoLocation(lat=37.7749, lon=-122.4194)
        assert loc.lat == 37.7749
        assert loc.lon == -122.4194
        
        # Test invalid latitude
        with pytest.raises(ValueError):
            GeoLocation(lat=91, lon=0)
        
        # Test invalid longitude
        with pytest.raises(ValueError):
            GeoLocation(lat=0, lon=181)
    
    def test_geo_polygon(self):
        """Test GeoPolygon validation."""
        points = [
            GeoLocation(lat=0, lon=0),
            GeoLocation(lat=0, lon=1),
            GeoLocation(lat=1, lon=1),
        ]
        polygon = GeoPolygon(points=points)
        assert len(polygon.points) == 3
        
        # Test minimum points validation
        with pytest.raises(ValueError):
            GeoPolygon(points=points[:2])
    
    def test_enriched_address(self):
        """Test EnrichedAddress validation."""
        addr = EnrichedAddress(
            street="123 Main St",
            city="San Francisco",
            state="California",
            zip_code="94102"
        )
        assert addr.city == "San Francisco"
        
        # Test optional coordinates
        addr_with_coords = EnrichedAddress(
            street="123 Main St",
            city="San Francisco",
            state="California",
            zip_code="94102",
            coordinates=GeoLocation(lat=37.7749, lon=-122.4194)
        )
        assert addr_with_coords.coordinates.lat == 37.7749


class TestEntityModels:
    """Test business entity models."""
    
    def test_enriched_property(self):
        """Test EnrichedProperty model."""
        prop = EnrichedProperty(
            listing_id="PROP123",
            property_type=PropertyType.HOUSE,
            price=Decimal("500000"),
            bedrooms=3,
            bathrooms=2.5,
            address=EnrichedAddress(
                street="123 Main St",
                city="San Francisco",
                state="California",
                zip_code="94102"
            )
        )
        assert prop.listing_id == "PROP123"
        assert prop.property_type == PropertyType.HOUSE
        assert prop.status == PropertyStatus.ACTIVE
        assert prop.embedding_id is not None
    
    def test_enriched_neighborhood(self):
        """Test EnrichedNeighborhood model."""
        neighborhood = EnrichedNeighborhood(
            name="Mission District",
            city="San Francisco",
            state="California"
        )
        assert neighborhood.name == "Mission District"
        assert neighborhood.neighborhood_id is not None
        assert neighborhood.poi_count == 0
    
    def test_enriched_wikipedia_article(self):
        """Test EnrichedWikipediaArticle model."""
        article = EnrichedWikipediaArticle(
            page_id=12345,
            article_id=1,
            title="San Francisco",
            url="https://en.wikipedia.org/wiki/San_Francisco",
            full_text="San Francisco is a city in California..."
        )
        assert article.page_id == 12345
        assert article.title == "San Francisco"
        assert article.relevance_score == 0.0
    
    def test_wikipedia_summary(self):
        """Test WikipediaSummary model."""
        summary = WikipediaSummary(
            page_id=12345,
            article_title="San Francisco",
            short_summary="A major city in California",
            key_topics=["California", "Bay Area", "Tech Hub"]
        )
        assert summary.page_id == 12345
        assert len(summary.key_topics) == 3
        assert summary.overall_confidence == 0.0


class TestEmbeddingModels:
    """Test embedding-related models."""
    
    def test_embedding_data(self):
        """Test EmbeddingData model."""
        vector = [0.1, 0.2, 0.3, 0.4]
        embedding = EmbeddingData(
            embedding_id="emb123",
            vector=vector,
            dimension=4,
            model_name="test-model",
            provider="ollama"
        )
        assert embedding.embedding_id == "emb123"
        assert len(embedding.vector) == 4
        assert embedding.dimension == 4
        
        # Test dimension validation
        with pytest.raises(ValueError):
            EmbeddingData(
                embedding_id="emb123",
                vector=vector,
                dimension=5,  # Mismatch
                model_name="test-model",
                provider="ollama"
            )
    
    def test_property_embedding(self):
        """Test PropertyEmbedding model."""
        embedding = PropertyEmbedding(
            embedding_id="emb123",
            listing_id="PROP123",
            vector=[0.1, 0.2, 0.3],
            text="Beautiful house in San Francisco"
        )
        assert embedding.listing_id == "PROP123"
        assert len(embedding.vector) == 3


class TestConfigModels:
    """Test configuration models."""
    
    def test_embedding_config(self):
        """Test EmbeddingConfig model."""
        config = EmbeddingConfig()
        assert config.provider == EmbeddingProvider.OLLAMA
        assert config.ollama_model == "nomic-embed-text"
        assert config.ollama_base_url == "http://localhost:11434"
    
    def test_chromadb_config(self):
        """Test ChromaDBConfig model."""
        config = ChromaDBConfig()
        assert config.host == "localhost"
        assert config.port == 8000
        assert "property_{model}_v{version}" in config.property_collection_pattern
    
    def test_chunking_config(self):
        """Test ChunkingConfig model."""
        config = ChunkingConfig()
        assert config.method == ChunkingMethod.SEMANTIC
        assert config.chunk_size == 800
        assert config.chunk_overlap == 100
    
    def test_main_config(self):
        """Test main Config model."""
        config = Config()
        assert config.metadata_version == "1.0"
        assert isinstance(config.embedding, EmbeddingConfig)
        assert isinstance(config.chromadb, ChromaDBConfig)
        assert isinstance(config.chunking, ChunkingConfig)
        assert isinstance(config.processing, ProcessingConfig)


class TestAPIModels:
    """Test API request/response models."""
    
    def test_pagination_params(self):
        """Test PaginationParams model."""
        params = PaginationParams(page=2, page_size=10)
        assert params.page == 2
        assert params.page_size == 10
        assert params.offset == 10
        assert params.limit == 10
    
    def test_property_filter(self):
        """Test PropertyFilter model."""
        filter_params = PropertyFilter(
            city="San Francisco",
            min_price=100000,
            max_price=1000000,
            min_bedrooms=2
        )
        assert filter_params.city == "San Francisco"
        assert filter_params.min_price == 100000
        assert filter_params.include_embeddings is False
    
    def test_response_metadata(self):
        """Test ResponseMetadata model."""
        metadata = ResponseMetadata.from_pagination(
            total_count=100,
            page=3,
            page_size=20
        )
        assert metadata.total_count == 100
        assert metadata.page == 3
        assert metadata.page_size == 20
        assert metadata.page_count == 5
    
    def test_error_response(self):
        """Test ErrorResponse model."""
        error = ErrorResponse(
            error="ValidationError",
            message="Invalid input",
            status_code=400
        )
        assert error.error == "ValidationError"
        assert error.status_code == 400
        assert error.timestamp > 0


class TestEnums:
    """Test enum values."""
    
    def test_property_type_enum(self):
        """Test PropertyType enum."""
        assert PropertyType.HOUSE.value == "house"
        assert PropertyType.CONDO.value == "condo"
    
    def test_entity_type_enum(self):
        """Test EntityType enum."""
        assert EntityType.PROPERTY.value == "property"
        assert EntityType.NEIGHBORHOOD.value == "neighborhood"
        assert EntityType.WIKIPEDIA_ARTICLE.value == "wikipedia_article"
    
    def test_embedding_provider_enum(self):
        """Test EmbeddingProvider enum."""
        assert EmbeddingProvider.OLLAMA.value == "ollama"
        assert EmbeddingProvider.OPENAI.value == "openai"
        assert EmbeddingProvider.GEMINI.value == "gemini"


class TestExceptions:
    """Test custom exceptions."""
    
    def test_exception_hierarchy(self):
        """Test exception inheritance."""
        assert issubclass(ValidationError, PropertyFinderError)
        assert issubclass(ValidationError, Exception)
        
        # Test raising exceptions
        with pytest.raises(PropertyFinderError):
            raise ValidationError("Test error")


if __name__ == "__main__":
    pytest.main([__file__])