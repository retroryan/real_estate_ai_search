#!/usr/bin/env python3
"""
Simple test for Wikipedia location extraction.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from real_estate_search.hybrid.location import LocationUnderstandingModule


def test_location_extraction():
    """Test location extraction from Wikipedia queries."""
    
    print("\n" + "="*80)
    print("TESTING LOCATION EXTRACTION FOR WIKIPEDIA QUERIES")
    print("="*80)
    
    # Initialize location module
    location_module = LocationUnderstandingModule()
    
    # Test queries
    test_queries = [
        "museums in San Francisco",
        "parks in Oakland",
        "Temescal neighborhood history",
        "Golden Gate Bridge construction",
        "restaurants in SOMA",
        "Berkeley campus buildings",
        "Silicon Valley tech companies",
        "Napa Valley wineries",
        "history of California",
        "San Francisco Bay Area transportation"
    ]
    
    print("\nExtracting locations from queries:")
    print("-" * 60)
    
    for query in test_queries:
        try:
            # Extract location
            location_intent = location_module(query)
            
            print(f"\n📍 Query: '{query}'")
            print(f"   Has location: {location_intent.has_location}")
            if location_intent.has_location:
                print(f"   City: {location_intent.city}")
                print(f"   State: {location_intent.state}")
                print(f"   Neighborhood: {location_intent.neighborhood}")
            print(f"   Cleaned query: '{location_intent.cleaned_query}'")
            print(f"   Confidence: {location_intent.confidence:.2f}")
            
        except Exception as e:
            print(f"\n❌ Error with query '{query}': {e}")
    
    print("\n" + "="*80)
    print("✅ Location extraction test completed!")
    print("="*80)


if __name__ == "__main__":
    test_location_extraction()