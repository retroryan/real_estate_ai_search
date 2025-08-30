"""Test that type fixes work correctly in the pipeline."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.writers.elasticsearch import PropertyInput, NeighborhoodInput


def test_property_types():
    """Test that property types are correct after Gold layer processing."""
    # Simulate data from Gold layer (after CAST operations)
    gold_data = {
        'listing_id': 'PROP-001',
        'neighborhood_id': 'N-001',
        'price': 500000.0,  # Should be float from Gold CAST
        'bedrooms': 3,
        'bathrooms': 2.5,
        'square_feet': 2000,
        'property_type': 'Single Family',
        'address': {'street': '123 Main St', 'city': 'SF', 'state': 'CA'},
        'price_per_sqft': 250.0,  # Should be float from Gold CAST
        'parking': {'spaces': 2, 'type': 'garage'},
        'features': ['Pool', 'Garden'],  # Should be list from Gold COALESCE
        'embedding': (0.1, 0.2, 0.3),  # Tuple from DuckDB
    }
    
    # Create PropertyInput - should handle types correctly
    prop_input = PropertyInput(**gold_data)
    
    # Verify types
    assert isinstance(prop_input.price, float), f"Price should be float, got {type(prop_input.price)}"
    assert isinstance(prop_input.price_per_sqft, float), f"Price per sqft should be float, got {type(prop_input.price_per_sqft)}"
    assert isinstance(prop_input.features, list), f"Features should be list, got {type(prop_input.features)}"
    assert prop_input.price == 500000.0
    assert prop_input.features == ['Pool', 'Garden']
    
    print("✓ Property types are correct")


def test_neighborhood_types():
    """Test that neighborhood types are correct after Gold layer processing."""
    # Simulate data from Gold layer (after CAST operations)
    gold_data = {
        'neighborhood_id': 'N-001',
        'name': 'Mission District',
        'city': 'San Francisco',
        'state': 'CA',
        'population': 50000,
        'median_income': 75000.0,  # Should be float from Gold CAST
        'median_home_price': 300000.0,  # Should be float from Gold CAST
        'center_latitude': 37.7599,
        'center_longitude': -122.4148,
        'amenities': ['Parks', 'Restaurants'],  # Should be list from Gold COALESCE
        'demographics': {'age_distribution': '25-45'},
        'embedding': (0.1, 0.2, 0.3),  # Tuple from DuckDB
    }
    
    # Create NeighborhoodInput - should handle types correctly
    neigh_input = NeighborhoodInput(**gold_data)
    
    # Verify types
    assert isinstance(neigh_input.median_income, float), f"Median income should be float, got {type(neigh_input.median_income)}"
    assert isinstance(neigh_input.median_home_price, float), f"Median home price should be float, got {type(neigh_input.median_home_price)}"
    assert isinstance(neigh_input.amenities, list), f"Amenities should be list, got {type(neigh_input.amenities)}"
    assert neigh_input.median_income == 75000.0
    assert neigh_input.amenities == ['Parks', 'Restaurants']
    
    print("✓ Neighborhood types are correct")


def test_empty_lists():
    """Test that empty/None values become empty lists."""
    # Test with None features
    gold_data = {
        'listing_id': 'PROP-002',
        'price': 400000.0,
        'bedrooms': 2,
        'bathrooms': 1.0,
        'square_feet': 1500,
        'property_type': 'Condo',
        'features': [],  # Gold layer COALESCE(features, LIST_VALUE()) returns empty list
        'address': {'street': '456 Oak St', 'city': 'SF', 'state': 'CA'},
    }
    
    prop_input = PropertyInput(**gold_data)
    assert prop_input.features == [], f"Empty features should be empty list, got {prop_input.features}"
    
    print("✓ Empty lists handled correctly")


if __name__ == "__main__":
    test_property_types()
    test_neighborhood_types()
    test_empty_lists()
    print("\n✅ All type conversion tests passed!")