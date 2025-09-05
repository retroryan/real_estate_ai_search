#!/usr/bin/env python3
"""
Simple standalone script to test neighborhood extraction using DSPy.
Compares extracted neighborhoods against those stored in Elasticsearch.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import dspy
from elasticsearch import Elasticsearch
from tabulate import tabulate
import json

# Load environment variables from parent directory
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded .env from: {env_path}")
else:
    print("⚠ No .env file found, using environment variables")

# Simple extraction signature for neighborhoods
class NeighborhoodExtractionSignature(dspy.Signature):
    """Extract neighborhood names from real estate queries."""
    
    query_text: str = dspy.InputField(
        desc="Natural language real estate search query"
    )
    
    neighborhood: str = dspy.OutputField(
        desc="Extracted neighborhood name, or 'none' if not found",
        prefix="Neighborhood: "
    )
    
    confidence: float = dspy.OutputField(
        desc="Confidence score between 0 and 1",
        prefix="Confidence: "
    )


def setup_dspy():
    """Initialize DSPy with OpenRouter or OpenAI."""
    # Try OpenRouter first, then OpenAI
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    if openrouter_key:
        print("✓ Using OpenRouter API")
        lm = dspy.LM(
            model='openrouter/openai/gpt-4o-mini',
            api_key=openrouter_key,
            api_base="https://openrouter.ai/api/v1",
            temperature=0.3,
            max_tokens=100
        )
    elif openai_key:
        print("✓ Using OpenAI API")
        lm = dspy.LM(
            model='gpt-4o-mini',
            api_key=openai_key,
            temperature=0.3,
            max_tokens=100
        )
    else:
        print("❌ No API key found! Set OPENROUTER_API_KEY or OPENAI_API_KEY in .env")
        sys.exit(1)
    
    dspy.configure(lm=lm)
    return dspy.Predict(NeighborhoodExtractionSignature)


def get_elasticsearch_neighborhoods() -> List[str]:
    """Fetch all unique neighborhoods from Elasticsearch."""
    # Setup Elasticsearch connection
    es_host = os.getenv('ES_HOST', 'localhost')
    es_port = int(os.getenv('ES_PORT', 9200))
    es_username = os.getenv('ES_USERNAME')
    es_password = os.getenv('ES_PASSWORD')
    es_scheme = os.getenv('ES_SCHEME', 'http')
    
    # Create client with authentication
    if es_username and es_password:
        es = Elasticsearch(
            [f"{es_scheme}://{es_host}:{es_port}"],
            basic_auth=(es_username, es_password),
            verify_certs=False
        )
        print(f"✓ Connected to Elasticsearch at {es_host}:{es_port} (authenticated)")
    else:
        es = Elasticsearch([f"{es_scheme}://{es_host}:{es_port}"])
        print(f"✓ Connected to Elasticsearch at {es_host}:{es_port}")
    
    neighborhoods = []
    
    # Try to get neighborhoods from the neighborhoods index first
    try:
        # Check if neighborhoods index exists
        if es.indices.exists(index="neighborhoods"):
            # Get all neighborhoods from the neighborhoods index
            response = es.search(
                index="neighborhoods",
                body={
                    "size": 1000,  # Get all neighborhoods
                    "_source": ["name"]
                }
            )
            
            neighborhoods = [
                hit['_source']['name'] 
                for hit in response['hits']['hits']
                if 'name' in hit['_source']
            ]
            print(f"✓ Found {len(neighborhoods)} neighborhoods in 'neighborhoods' index")
        
        # If no neighborhoods found, try properties index
        if not neighborhoods:
            response = es.search(
                index="properties",
                body={
                    "size": 0,
                    "aggs": {
                        "unique_neighborhoods": {
                            "terms": {
                                "field": "neighborhood.name.keyword",
                                "size": 1000
                            }
                        }
                    }
                }
            )
            
            neighborhoods = [
                bucket['key'] 
                for bucket in response.get('aggregations', {}).get('unique_neighborhoods', {}).get('buckets', [])
            ]
            
            if neighborhoods:
                print(f"✓ Found {len(neighborhoods)} neighborhoods from 'properties' index")
        
        return neighborhoods
        
    except Exception as e:
        print(f"⚠ Could not fetch neighborhoods from Elasticsearch: {e}")
        print("  Using sample neighborhood list instead")
        # Fallback to some known neighborhoods
        return [
            "SOMA", "Mission District", "Pacific Heights", "Castro",
            "Nob Hill", "Russian Hill", "Marina District", "Haight-Ashbury",
            "Financial District", "North Beach", "Chinatown", "Tenderloin"
        ]


def test_extraction(extractor, es_neighborhoods: List[str]) -> None:
    """Test neighborhood extraction with various queries."""
    
    # Build test queries using actual ES neighborhoods
    test_queries = []
    
    # Use first 6 ES neighborhoods for test queries
    for i, neighborhood in enumerate(es_neighborhoods[:6]):
        if i % 2 == 0:
            test_queries.append(f"Modern condo in {neighborhood}")
        else:
            test_queries.append(f"Family home near {neighborhood} area")
    
    # Add specific neighborhoods including Temescal
    test_queries.extend([
        "Charming bungalow in Temescal neighborhood",
        "Victorian house in Temescal Oakland",
        "Temescal area near restaurants and shops",
        "Looking for rentals in Rockridge or Temescal",
        "SOMA loft with exposed brick",
        "Sunset District family home near Golden Gate Park",
        "Noe Valley townhouse with backyard",
        "Deer Valley ski-in ski-out property",
    ])
    
    # Complex queries with multiple potential locations
    test_queries.extend([
        "2 bedroom in either SOMA or Mission District",
        "Looking for homes in Pacific Heights, Noe Valley, or Sunset District",
        "Apartment near downtown, preferably SOMA or South Beach",
        "Property in Temescal close to Berkeley border",
        "Condo between Rockridge and Temescal neighborhoods",
        "Investment property in up-and-coming areas like Temescal",
    ])
    
    # Queries with location at different positions
    test_queries.extend([
        "I need a place in Willow Glen with good schools",
        "Santana Row luxury condo with concierge",
        "Affordable options, maybe Oakley or Creekbridge area",
        "Downtown Coalville near the ski resorts",
        "Something modern, thinking Park Meadows or Summit Park",
    ])
    
    # Add some without neighborhoods
    test_queries.extend([
        "Modern kitchen with stainless steel appliances",
        "Three bedroom house with two-car garage",
        "Waterfront property with panoramic ocean views",
        "Affordable starter home with renovation potential",
        "Luxury penthouse with rooftop deck",
        "Ranch style home on large lot",
    ])
    
    # Add some ambiguous ones using partial names
    if es_neighborhoods:
        # Take first word of some neighborhoods for ambiguous tests
        for neigh in es_neighborhoods[6:9]:
            first_word = neigh.split()[0]
            test_queries.append(f"Property in {first_word}")
    
    # Add some that might not be in ES but are common neighborhoods
    test_queries.extend([
        "Loft in North Beach near Coit Tower",
        "House near Russian Hill with city views",
        "Studio apartment downtown Financial District",
        "Marina District flat with parking",
        "Castro Victorian near Dolores Park",
        "Hayes Valley boutique condo",
    ])
    
    results = []
    correct = 0
    total_with_neighborhood = 0
    
    print("\n" + "="*80)
    print("TESTING NEIGHBORHOOD EXTRACTION")
    print("="*80)
    
    for query in test_queries:
        try:
            # Extract neighborhood
            result = extractor(query_text=query)
            
            extracted = result.neighborhood
            confidence = float(result.confidence) if result.confidence else 0.0
            
            # Clean up extraction
            if extracted.lower() in ['none', 'unknown', '']:
                extracted = None
            
            # Check if it's in our ES neighborhoods (case-insensitive)
            es_match = None
            if extracted:
                for es_neigh in es_neighborhoods:
                    if extracted.lower() == es_neigh.lower():
                        es_match = es_neigh
                        break
            
            # Determine if query actually contains ANY neighborhood (not just ES ones)
            query_lower = query.lower()
            
            # List of known neighborhoods (including those not in ES)
            all_known_neighborhoods = es_neighborhoods + [
                "North Beach", "Russian Hill", "Financial District", 
                "Marina District", "Castro", "Hayes Valley", "South Beach"
            ]
            
            # Check if query contains an ES neighborhood
            actual_es_neighborhood = None
            for es_neigh in es_neighborhoods:
                if es_neigh.lower() in query_lower:
                    actual_es_neighborhood = es_neigh
                    total_with_neighborhood += 1
                    break
            
            # Check if query contains ANY neighborhood mention
            query_has_neighborhood = False
            expected_neighborhood = None
            for neigh in all_known_neighborhoods:
                if neigh.lower() in query_lower:
                    query_has_neighborhood = True
                    expected_neighborhood = neigh
                    break
            
            # Check correctness - DSPy should extract a neighborhood if one is mentioned
            is_correct = False
            if query_has_neighborhood and extracted:
                # Query has a neighborhood and DSPy extracted something
                # Check if the extraction is reasonable (contained in query)
                if extracted.lower() in query_lower or any(word in query_lower for word in extracted.lower().split()):
                    is_correct = True
                    correct += 1
            elif not query_has_neighborhood and not extracted:
                # Query has no neighborhood and DSPy extracted nothing
                is_correct = True
                correct += 1
            
            results.append({
                "Query": query[:40] + "..." if len(query) > 40 else query,
                "Extracted": extracted or "-",
                "In ES?": "✓" if es_match else "✗" if extracted else "-",
                "Confidence": f"{confidence:.2f}",
                "Correct": "✓" if is_correct else "✗"
            })
            
        except Exception as e:
            results.append({
                "Query": query[:40] + "..." if len(query) > 40 else query,
                "Extracted": f"ERROR: {e}",
                "In ES?": "-",
                "Confidence": "0.00",
                "Correct": "✗"
            })
    
    # Display results in a more compact format for many queries
    print("\nExtraction Results:")
    
    # Group results by correctness for better readability
    correct_results = [r for r in results if r["Correct"] == "✓"]
    incorrect_results = [r for r in results if r["Correct"] == "✗"]
    
    if len(results) > 30:
        # For many results, show summary first
        print(f"\n✅ Correct Extractions ({len(correct_results)}):")
        for r in correct_results[:10]:
            print(f"   {r['Query'][:50]:50} → {r['Extracted'] or 'None':20} (conf: {r['Confidence']})")
        if len(correct_results) > 10:
            print(f"   ... and {len(correct_results) - 10} more correct extractions")
        
        print(f"\n❌ Incorrect Extractions ({len(incorrect_results)}):")
        for r in incorrect_results[:10]:
            print(f"   {r['Query'][:50]:50} → {r['Extracted'] or 'None':20} (conf: {r['Confidence']})")
        if len(incorrect_results) > 10:
            print(f"   ... and {len(incorrect_results) - 10} more incorrect extractions")
    else:
        # For fewer results, show full table
        print(tabulate(results, headers="keys", tablefmt="grid"))
    
    # Summary statistics
    accuracy = (correct / len(test_queries)) * 100
    print(f"\n📊 SUMMARY:")
    print(f"   Total queries tested: {len(test_queries)}")
    print(f"   Queries with neighborhoods: {total_with_neighborhood}")
    print(f"   Correct extractions: {correct}/{len(test_queries)}")
    print(f"   Accuracy: {accuracy:.1f}%")
    
    # Breakdown by category
    queries_with_es_neighborhoods = sum(1 for r in results if r["In ES?"] == "✓")
    queries_correctly_none = sum(1 for r in results if r["Extracted"] == "-" and r["Correct"] == "✓")
    print(f"\n📈 Detailed Analysis:")
    print(f"   Extracted neighborhoods in ES: {queries_with_es_neighborhoods}")
    print(f"   Correctly identified no neighborhood: {queries_correctly_none}")
    print(f"   False positives (extracted but not in ES): {len([r for r in results if r['In ES?'] == '✗' and r['Extracted'] != '-'])}") 
    print(f"   False negatives (missed ES neighborhoods): {len([r for r in results if r['Correct'] == '✗' and any(n.lower() in r['Query'].lower() for n in es_neighborhoods)])}")
    
    # Show available neighborhoods for reference
    print(f"\n📍 Available neighborhoods in Elasticsearch ({len(es_neighborhoods)}):")
    # Group into columns for better display
    cols = 4
    for i in range(0, len(es_neighborhoods), cols):
        row = es_neighborhoods[i:i+cols]
        print("   " + " | ".join(f"{n:20}" for n in row))


def main():
    """Main execution function."""
    print("🏘️  Neighborhood Extraction Test Tool")
    print("="*80)
    
    # Setup DSPy
    print("\n1️⃣  Setting up DSPy...")
    extractor = setup_dspy()
    
    # Get neighborhoods from Elasticsearch
    print("\n2️⃣  Fetching neighborhoods from Elasticsearch...")
    es_neighborhoods = get_elasticsearch_neighborhoods()
    
    # Run tests
    print("\n3️⃣  Running extraction tests...")
    test_extraction(extractor, es_neighborhoods)
    
    print("\n✅ Test complete!")


if __name__ == "__main__":
    main()