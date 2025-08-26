#!/usr/bin/env python3
"""Simple test script for Phase 1 components."""

import sys
from datetime import date
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from squack_pipeline.models import Property, WikipediaArticle
from squack_pipeline.config import PipelineSettings


def test_models():
    """Test Pydantic V2 models."""
    print("🧪 Testing Pydantic V2 models...")
    
    # Test Property model
    prop_data = {
        'listing_id': 'test-001',
        'address': {
            'street': '123 Test St', 
            'city': 'TestCity', 
            'county': 'TestCounty', 
            'state': 'CA', 
            'zip': '12345'
        },
        'coordinates': {'latitude': 37.0, 'longitude': -122.0},
        'property_details': {
            'square_feet': 1500, 
            'bedrooms': 3, 
            'bathrooms': 2.0, 
            'property_type': 'house', 
            'year_built': 2000, 
            'lot_size': 0.25, 
            'stories': 2, 
            'garage_spaces': 2
        },
        'listing_price': 500000.0,
        'price_per_sqft': 333.33,
        'description': 'Test property',
        'listing_date': date(2025, 1, 1),
        'days_on_market': 10
    }
    
    prop = Property(**prop_data)
    print(f"✓ Property: {prop.listing_id} - ${prop.listing_price:,.2f}")
    
    # Test Wikipedia model
    wiki_data = {
        'page_id': 123,
        'title': 'Test Article',
        'content': 'Test content',
        'url': 'https://test.com'
    }
    
    wiki = WikipediaArticle(**wiki_data)
    print(f"✓ Wikipedia: {wiki.title} (ID: {wiki.page_id})")


def test_config():
    """Test configuration system."""
    print("⚙️  Testing configuration...")
    
    settings = PipelineSettings()
    print(f"✓ Pipeline: {settings.pipeline_name} v{settings.pipeline_version}")
    print(f"✓ Environment: {settings.environment}")
    print(f"✓ DuckDB Memory: {settings.duckdb.memory_limit}")
    print(f"✓ DuckDB Threads: {settings.duckdb.threads}")


def test_schema():
    """Test JSON schema generation."""
    print("📋 Testing schema generation...")
    
    schema = Property.model_json_schema()
    field_count = len(schema['properties'])
    print(f"✓ Property schema: {field_count} fields")
    print(f"✓ Required fields: {len(schema['required'])}")


def main():
    """Run all Phase 1 tests."""
    print("🚀 SQUACK Pipeline - Phase 1 Tests\n")
    
    try:
        test_models()
        print()
        
        test_config()
        print()
        
        test_schema()
        print()
        
        print("✅ All Phase 1 tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()