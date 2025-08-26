"""
Test Graph Models

Validates that the Pydantic graph models work correctly with sample data.
Note: Only tests node models. Relationships are handled separately in Neo4j.
"""

import json
from datetime import date, datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_pipeline.models.graph_models import (
    PropertyNode,
    NeighborhoodNode,
    CityNode,
    StateNode,
    WikipediaArticleNode,
    FeatureNode,
    PropertyTypeNode,
    PriceRangeNode,
    CountyNode,
    TopicClusterNode,
    PropertyType,
    FeatureCategory,
    NodeConfiguration,
    create_node_id,
    validate_coordinates,
    clean_string_for_id
)


class TestGraphModels:
    """Test the graph data models."""
    
    def test_property_node(self):
        """Test PropertyNode model."""
        print("\n🏠 Testing PropertyNode...")
        
        property_data = {
            "id": "property:123456",
            "address": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "zip_code": "94102",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "property_type": PropertyType.SINGLE_FAMILY,
            "bedrooms": 3,
            "bathrooms": 2.5,
            "square_feet": 2000,
            "lot_size": 0.25,
            "year_built": 1925,
            "stories": 2,
            "garage_spaces": 2,
            "listing_price": 1200000,
            "price_per_sqft": 600.0,
            "listing_date": date(2024, 1, 15),
            "days_on_market": 30,
            "description": "Beautiful Victorian home",
            "features": ["hardwood floors", "fireplace", "garden"],
            "images": ["image1.jpg", "image2.jpg"],
            "neighborhood_id": "neighborhood:nob_hill_ca",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "data_source": "mls",
            "quality_score": 0.95
        }
        
        # Test creation and validation
        property_node = PropertyNode(**property_data)
        
        # Validate required fields
        assert property_node.id == "property:123456"
        assert property_node.address == "123 Main St"
        assert property_node.property_type == PropertyType.SINGLE_FAMILY
        assert property_node.bedrooms == 3
        assert property_node.bathrooms == 2.5
        assert property_node.listing_price == 1200000
        
        # Test enum value (converted to string due to use_enum_values=True)
        assert property_node.property_type == "single_family"
        
        print("✅ PropertyNode validation passed")
        
    def test_neighborhood_node(self):
        """Test NeighborhoodNode model."""
        print("\n🏘️ Testing NeighborhoodNode...")
        
        neighborhood_data = {
            "id": "neighborhood:nob_hill_ca",
            "name": "Nob Hill",
            "city": "San Francisco",
            "state": "CA",
            "county": "San Francisco County",
            "latitude": 37.7928,
            "longitude": -122.4194,
            "description": "Historic upscale neighborhood",
            "walkability_score": 9,
            "transit_score": 8,
            "school_rating": 7,
            "safety_rating": 8,
            "median_home_price": 1500000,
            "price_trend": "increasing",
            "median_household_income": 120000,
            "population": 15000,
            "lifestyle_tags": ["urban", "historic", "upscale"],
            "amenities": ["restaurants", "shops", "cable_cars"],
            "vibe": "sophisticated",
            "nightlife_score": 8.5,
            "family_friendly_score": 6.0,
            "cultural_score": 9.0,
            "green_space_score": 5.5,
            "knowledge_score": 0.85,
            "aggregated_topics": ["history", "architecture", "dining"],
            "wikipedia_count": 12,
            "created_at": datetime.now()
        }
        
        # Test creation and validation
        neighborhood_node = NeighborhoodNode(**neighborhood_data)
        
        # Validate required fields
        assert neighborhood_node.id == "neighborhood:nob_hill_ca"
        assert neighborhood_node.name == "Nob Hill"
        assert neighborhood_node.walkability_score == 9
        assert neighborhood_node.lifestyle_tags == ["urban", "historic", "upscale"]
        
        print("✅ NeighborhoodNode validation passed")
    
    def test_feature_node(self):
        """Test FeatureNode model."""
        print("\n🔧 Testing FeatureNode...")
        
        feature_data = {
            "id": "feature:hardwood_floors",
            "name": "hardwood floors",
            "category": FeatureCategory.STRUCTURAL,
            "description": "Beautiful hardwood flooring throughout",
            "count": 45
        }
        
        feature_node = FeatureNode(**feature_data)
        
        assert feature_node.id == "feature:hardwood_floors"
        assert feature_node.category == FeatureCategory.STRUCTURAL
        assert feature_node.category == "structural"
        
        print("✅ FeatureNode validation passed")
    
    def test_wikipedia_article_node(self):
        """Test WikipediaArticleNode model."""
        print("\n📚 Testing WikipediaArticleNode...")
        
        article_data = {
            "id": "123456",
            "page_id": 123456,
            "title": "Golden Gate Park",
            "url": "https://en.wikipedia.org/wiki/Golden_Gate_Park",
            "short_summary": "Large urban park in San Francisco",
            "long_summary": "Golden Gate Park is a large urban park...",
            "key_topics": ["parks", "recreation", "san francisco"],
            "best_city": "San Francisco",
            "best_state": "CA",
            "best_county": "San Francisco County",
            "confidence": 0.95,
            "overall_confidence": 0.90,
            "location_type": "park",
            "latitude": 37.7694,
            "longitude": -122.4862,
            "extraction_method": "coordinates",
            "topics_extracted_at": datetime.now(),
            "amenities_count": 15,
            "content_length": 5000,
            "processed_at": datetime.now()
        }
        
        article_node = WikipediaArticleNode(**article_data)
        
        assert article_node.page_id == 123456
        assert article_node.title == "Golden Gate Park"
        assert article_node.confidence == 0.95
        assert "parks" in article_node.key_topics
        
        print("✅ WikipediaArticleNode validation passed")
    
    def test_utility_functions(self):
        """Test utility functions."""
        print("\n🛠️ Testing utility functions...")
        
        # Test create_node_id
        node_id = create_node_id("property", "123", "main_st")
        assert node_id == "property:123:main_st"
        
        # Test validate_coordinates
        assert validate_coordinates(37.7749, -122.4194) == True
        assert validate_coordinates(91.0, -122.4194) == False  # Invalid latitude
        assert validate_coordinates(37.7749, -181.0) == False  # Invalid longitude
        
        # Test clean_string_for_id
        clean_id = clean_string_for_id("Nob Hill")
        assert clean_id == "nob_hill"
        
        clean_id2 = clean_string_for_id("Multi-Family Home")
        assert clean_id2 == "multi_family_home"
        
        print("✅ Utility functions validation passed")
    
    def test_configuration_models(self):
        """Test configuration models."""
        print("\n⚙️ Testing configuration models...")
        
        config_data = {
            "node_batch_size": 2000,
            "max_concurrent_batches": 6
        }
        
        config = NodeConfiguration(**config_data)
        
        assert config.node_batch_size == 2000
        assert config.max_concurrent_batches == 6
        
        print("✅ NodeConfiguration validation passed")
    
    def test_serialization(self):
        """Test JSON serialization."""
        print("\n📤 Testing serialization...")
        
        property_node = PropertyNode(
            id="property:test",
            address="123 Test St",
            city="Test City",
            state="CA",
            latitude=37.0,
            longitude=-122.0,
            property_type=PropertyType.CONDO,
            bedrooms=2,
            bathrooms=2.0,
            square_feet=1200,
            listing_price=800000,
            price_per_sqft=667.0,
            listing_date=date(2024, 1, 1)
        )
        
        # Test serialization
        json_data = property_node.model_dump_json()
        assert '"property_type":"condo"' in json_data
        
        # Test deserialization
        loaded_node = PropertyNode.model_validate_json(json_data)
        assert loaded_node.id == "property:test"
        assert loaded_node.property_type == "condo"
        
        print("✅ Serialization validation passed")
    
    def run_all_tests(self):
        """Run all tests."""
        print("="*60)
        print("🧪 RUNNING GRAPH MODELS TESTS (Node-only)")
        print("="*60)
        
        try:
            # Test node models
            self.test_property_node()
            self.test_neighborhood_node()
            self.test_feature_node()
            self.test_wikipedia_article_node()
            
            # Test utilities
            self.test_utility_functions()
            self.test_configuration_models()
            
            # Test serialization
            self.test_serialization()
            
            print("\n" + "="*60)
            print("✅ ALL GRAPH MODEL TESTS PASSED")
            print("Note: Relationships are handled separately in Neo4j")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise


if __name__ == "__main__":
    tester = TestGraphModels()
    tester.run_all_tests()