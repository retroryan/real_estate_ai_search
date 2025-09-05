#!/usr/bin/env python3
"""
Test Temescal neighborhood extraction specifically.
"""

from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

from real_estate_search.hybrid.location import LocationUnderstandingModule

# Test the specific Temescal query
location_module = LocationUnderstandingModule()

query = "Tell me about the Temescal neighborhood in Oakland - what amenities and culture does it offer?"
print(f"Query: {query}")
print("-" * 60)

location_intent = location_module(query)

print(f"Extracted:")
print(f"  Has location: {location_intent.has_location}")
print(f"  City: {location_intent.city}")
print(f"  State: {location_intent.state}")
print(f"  Neighborhood: {location_intent.neighborhood}")
print(f"  Cleaned query: '{location_intent.cleaned_query}'")
print(f"  Confidence: {location_intent.confidence}")

if location_intent.city == "Oakland":
    print("\n✅ Successfully extracted Oakland from Temescal query!")
else:
    print(f"\n❌ Expected Oakland but got: {location_intent.city}")