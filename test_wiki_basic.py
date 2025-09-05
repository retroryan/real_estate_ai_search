#!/usr/bin/env python3
"""
Basic test to verify the Wikipedia search service can be initialized.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded .env from: {env_path}")

# Check if required environment variables are set
print("\nEnvironment Check:")
print("-" * 40)
print(f"OPENROUTER_API_KEY: {'✓ Set' if os.getenv('OPENROUTER_API_KEY') else '✗ Missing'}")
print(f"OPENAI_API_KEY: {'✓ Set' if os.getenv('OPENAI_API_KEY') else '✗ Missing'}")
print(f"ES_HOST: {os.getenv('ES_HOST', 'localhost')}")
print(f"ES_PORT: {os.getenv('ES_PORT', '9200')}")
print(f"ES_USERNAME: {'✓ Set' if os.getenv('ES_USERNAME') else '✗ Missing'}")
print(f"ES_PASSWORD: {'✓ Set' if os.getenv('ES_PASSWORD') else '✗ Missing'}")

print("\n" + "="*80)
print("Testing basic imports and initialization...")
print("="*80)

try:
    # Test imports
    print("\n1. Testing imports...")
    from real_estate_search.hybrid.location import LocationUnderstandingModule, LocationFilterBuilder
    from real_estate_search.mcp_server.services.wikipedia_search import WikipediaSearchService
    from real_estate_search.mcp_server.models.search import WikipediaSearchRequest
    print("   ✓ All imports successful")
    
    # Test location module can be created
    print("\n2. Testing LocationUnderstandingModule initialization...")
    location_module = LocationUnderstandingModule()
    print("   ✓ LocationUnderstandingModule created")
    
    # Test filter builder
    print("\n3. Testing LocationFilterBuilder initialization...")
    filter_builder = LocationFilterBuilder()
    print("   ✓ LocationFilterBuilder created")
    
    # Test a simple extraction
    print("\n4. Testing simple location extraction...")
    print("   Query: 'museums in San Francisco'")
    location_intent = location_module("museums in San Francisco")
    print(f"   ✓ Extraction completed")
    print(f"   - Has location: {location_intent.has_location}")
    print(f"   - City: {location_intent.city}")
    print(f"   - Cleaned query: '{location_intent.cleaned_query}'")
    
    print("\n✅ All basic tests passed!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()