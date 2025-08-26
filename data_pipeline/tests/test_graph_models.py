"""
Test Graph Models

Validates that the Pydantic graph models work correctly with sample data.
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
    LocatedInRelationship,
    PartOfRelationship,
    DescribesRelationship,
    NearRelationship,
    SimilarToRelationship,
    PropertyType,
    GraphConfiguration,
    create_node_id,
    validate_coordinates
)


class TestGraphModels:
    """Test suite for graph models."""
    
    def test_property_node(self):
        """Test PropertyNode model with sample data."""
        property_data = {
            "id": "prop-001",
            "address": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "zip_code": "94102",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "property_type": "condo",
            "bedrooms": 2,
            "bathrooms": 1.5,
            "square_feet": 1200,
            "lot_size": 0.1,
            "year_built": 1990,
            "stories": 1,
            "garage_spaces": 1,
            "listing_price": 850000,
            "price_per_sqft": 708.33,
            "listing_date": "2025-01-15",
            "days_on_market": 30,
            "description": "Beautiful condo in downtown SF",
            "features": ["hardwood floors", "city views", "parking"],
            "neighborhood_id": "sf-downtown"
        }
        
        # Create node
        node = PropertyNode(**property_data)
        
        # Validate
        assert node.id == "prop-001"
        assert node.city == "San Francisco"
        assert node.property_type == PropertyType.CONDO.value
        assert len(node.features) == 3
        assert node.listing_price == 850000
        print("✅ PropertyNode validation passed")
        
        return node
    
    def test_neighborhood_node(self):
        """Test NeighborhoodNode model."""
        neighborhood_data = {
            "id": "sf-pac-heights",
            "name": "Pacific Heights",
            "city": "San Francisco",
            "state": "CA",
            "county": "San Francisco",
            "latitude": 37.7925,
            "longitude": -122.4382,
            "description": "Upscale residential neighborhood",
            "walkability_score": 9,
            "transit_score": 8,
            "school_rating": 9,
            "safety_rating": 8,
            "median_home_price": 3500000,
            "price_trend": "stable",
            "median_household_income": 154264,
            "population": 20754,
            "lifestyle_tags": ["luxury", "views", "historic"],
            "amenities": ["parks", "shopping", "dining"],
            "vibe": "sophisticated residential"
        }
        
        node = NeighborhoodNode(**neighborhood_data)
        assert node.id == "sf-pac-heights"
        assert node.walkability_score == 9
        assert len(node.lifestyle_tags) == 3
        print("✅ NeighborhoodNode validation passed")
        
        return node
    
    def test_city_node(self):
        """Test CityNode model."""
        city_data = {
            "id": "san_francisco_ca",
            "name": "San Francisco",
            "state": "CA",
            "county": "San Francisco",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "population": 873965,
            "median_home_price": 1400000
        }
        
        node = CityNode(**city_data)
        assert node.id == "san_francisco_ca"
        assert node.population == 873965
        print("✅ CityNode validation passed")
        
        # Test auto ID generation
        city_data2 = {
            "name": "Park City",
            "state": "UT",
            "latitude": 40.6461,
            "longitude": -111.4980
        }
        node2 = CityNode(**city_data2)
        assert node2.id == "park_city_ut"
        print("✅ CityNode auto-ID generation passed")
        
        return node
    
    def test_state_node(self):
        """Test StateNode model."""
        state_data = {
            "id": "CA",
            "name": "California",
            "abbreviation": "CA",
            "latitude": 36.7783,
            "longitude": -119.4179
        }
        
        node = StateNode(**state_data)
        assert node.id == "CA"
        assert node.name == "California"
        print("✅ StateNode validation passed")
        
        return node
    
    def test_wikipedia_article_node(self):
        """Test WikipediaArticleNode model."""
        article_data = {
            "id": "wiki_1978628",
            "page_id": 1978628,
            "title": "Pacific Heights, San Francisco",
            "url": "https://en.wikipedia.org/wiki/Pacific_Heights,_San_Francisco",
            "short_summary": "Upscale neighborhood in San Francisco",
            "long_summary": "Pacific Heights is a neighborhood...",
            "key_topics": ["residential", "historic", "architecture"],
            "best_city": "San Francisco",
            "best_state": "CA",
            "confidence": 0.95,
            "latitude": 37.7925,
            "longitude": -122.4382,
            "processed_at": datetime.now()
        }
        
        node = WikipediaArticleNode(**article_data)
        assert node.page_id == 1978628
        assert node.confidence == 0.95
        assert len(node.key_topics) == 3
        print("✅ WikipediaArticleNode validation passed")
        
        return node
    
    def test_relationships(self):
        """Test relationship models."""
        # LocatedIn
        located_in = LocatedInRelationship(
            from_id="prop-001",
            to_id="sf-pac-heights",
            confidence=0.95,
            distance_meters=250.5
        )
        assert located_in.relationship_type == "LOCATED_IN"
        assert located_in.distance_meters == 250.5
        print("✅ LocatedInRelationship validation passed")
        
        # PartOf
        part_of = PartOfRelationship(
            from_id="san_francisco_ca",
            to_id="CA"
        )
        assert part_of.relationship_type == "PART_OF"
        print("✅ PartOfRelationship validation passed")
        
        # Describes
        describes = DescribesRelationship(
            from_id="wiki_1978628",
            to_id="sf-pac-heights",
            confidence=0.9,
            match_type="title"
        )
        assert describes.confidence == 0.9
        print("✅ DescribesRelationship validation passed")
        
        # Near
        near = NearRelationship(
            from_id="prop-001",
            to_id="amenity_golden_gate_park",
            distance_meters=1500
        )
        assert near.distance_meters == 1500
        assert near.distance_miles is not None
        assert abs(near.distance_miles - 0.932) < 0.01  # Check conversion
        print("✅ NearRelationship validation passed")
        
        # SimilarTo
        similar = SimilarToRelationship(
            from_id="prop-001",
            to_id="prop-002",
            similarity_score=0.85,
            price_similarity=0.9,
            size_similarity=0.8,
            feature_similarity=0.85
        )
        assert similar.similarity_score == 0.85
        print("✅ SimilarToRelationship validation passed")
    
    def test_graph_configuration(self):
        """Test GraphConfiguration model."""
        config = GraphConfiguration()
        assert config.near_distance_meters == 1609.34  # 1 mile
        assert config.similarity_threshold == 0.7
        assert config.node_batch_size == 1000
        print("✅ GraphConfiguration validation passed")
        
        # Test with custom values
        custom_config = GraphConfiguration(
            near_distance_meters=2000,
            similarity_threshold=0.8,
            node_batch_size=500
        )
        assert custom_config.near_distance_meters == 2000
        assert custom_config.similarity_threshold == 0.8
        print("✅ GraphConfiguration custom values passed")
    
    def test_utility_functions(self):
        """Test utility functions."""
        # Test node ID creation
        node_id = create_node_id("property", "oak", "125")
        assert node_id == "property:oak:125"
        
        node_id2 = create_node_id("city", "San Francisco", "CA")
        assert node_id2 == "city:san_francisco:ca"
        print("✅ create_node_id validation passed")
        
        # Test coordinate validation
        assert validate_coordinates(37.7749, -122.4194) == True
        assert validate_coordinates(91, -122) == False
        assert validate_coordinates(37, -181) == False
        print("✅ validate_coordinates validation passed")
    
    def test_with_real_data(self):
        """Test models with real data from files."""
        # Load sample property data
        property_file = Path("/Users/ryanknight/projects/temporal/real_estate_ai_search/real_estate_data/properties_sf.json")
        if property_file.exists():
            with open(property_file, 'r') as f:
                properties = json.load(f)
                
            # Test first property
            if properties:
                prop = properties[0]
                property_node = PropertyNode(
                    id=prop["listing_id"],
                    address=prop["address"]["street"],
                    city=prop["address"]["city"],
                    state=prop["address"]["state"],
                    zip_code=prop["address"]["zip"],
                    latitude=prop["coordinates"]["latitude"],
                    longitude=prop["coordinates"]["longitude"],
                    property_type=prop["property_details"]["property_type"],
                    bedrooms=prop["property_details"]["bedrooms"],
                    bathrooms=prop["property_details"]["bathrooms"],
                    square_feet=prop["property_details"]["square_feet"],
                    lot_size=prop["property_details"].get("lot_size"),
                    year_built=prop["property_details"].get("year_built"),
                    stories=prop["property_details"].get("stories"),
                    garage_spaces=prop["property_details"].get("garage_spaces"),
                    listing_price=prop["listing_price"],
                    price_per_sqft=prop["price_per_sqft"],
                    listing_date=prop["listing_date"],
                    days_on_market=prop["days_on_market"],
                    description=prop.get("description"),
                    features=prop.get("features", []),
                    neighborhood_id=prop.get("neighborhood_id")
                )
                print(f"✅ Real property data validation passed: {property_node.id}")
        
        # Load sample neighborhood data
        neighborhood_file = Path("/Users/ryanknight/projects/temporal/real_estate_ai_search/real_estate_data/neighborhoods_sf.json")
        if neighborhood_file.exists():
            with open(neighborhood_file, 'r') as f:
                neighborhoods = json.load(f)
                
            # Test first neighborhood
            if neighborhoods:
                hood = neighborhoods[0]
                neighborhood_node = NeighborhoodNode(
                    id=hood["neighborhood_id"],
                    name=hood["name"],
                    city=hood["city"],
                    state=hood["state"],
                    county=hood.get("county"),
                    latitude=hood["coordinates"]["latitude"],
                    longitude=hood["coordinates"]["longitude"],
                    description=hood["description"],
                    walkability_score=hood["characteristics"].get("walkability_score"),
                    transit_score=hood["characteristics"].get("transit_score"),
                    school_rating=hood["characteristics"].get("school_rating"),
                    safety_rating=hood["characteristics"].get("safety_rating"),
                    median_home_price=hood.get("median_home_price"),
                    price_trend=hood.get("price_trend"),
                    median_household_income=hood["demographics"].get("median_household_income"),
                    population=hood["demographics"].get("population"),
                    lifestyle_tags=hood.get("lifestyle_tags", []),
                    amenities=hood.get("amenities", []),
                    vibe=hood["demographics"].get("vibe")
                )
                print(f"✅ Real neighborhood data validation passed: {neighborhood_node.id}")
    
    def run_all_tests(self):
        """Run all tests."""
        print("\n" + "="*60)
        print("GRAPH MODELS TEST SUITE")
        print("="*60 + "\n")
        
        try:
            # Test individual models
            property_node = self.test_property_node()
            neighborhood_node = self.test_neighborhood_node()
            city_node = self.test_city_node()
            state_node = self.test_state_node()
            wikipedia_node = self.test_wikipedia_article_node()
            
            # Test relationships
            self.test_relationships()
            
            # Test configuration
            self.test_graph_configuration()
            
            # Test utilities
            self.test_utility_functions()
            
            # Test with real data
            self.test_with_real_data()
            
            print("\n" + "="*60)
            print("✅ ALL GRAPH MODEL TESTS PASSED!")
            print("="*60)
            return True
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point."""
    tester = TestGraphModels()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()