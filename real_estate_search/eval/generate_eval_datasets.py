#!/usr/bin/env python
"""
Generate comprehensive evaluation datasets for all demo query types.
Creates realistic test cases based on actual Elasticsearch data.
"""

import json
import random
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Load the ES data analysis
with open('es_data_analysis.json', 'r') as f:
    es_data = json.load(f)

# Create eval directory
eval_dir = Path('real_estate_search/eval')
eval_dir.mkdir(exist_ok=True)

def generate_price_values(count: int = 20) -> List[int]:
    """Generate realistic price values based on actual data distribution."""
    min_price = es_data['properties']['price_range']['min']
    max_price = es_data['properties']['price_range']['max']
    avg_price = es_data['properties']['price_range']['avg']
    
    prices = []
    # Mix of different price ranges
    for i in range(count):
        if i % 5 == 0:
            # Low end prices
            prices.append(int(random.uniform(min_price, avg_price * 0.7)))
        elif i % 5 == 1:
            # High end prices
            prices.append(int(random.uniform(avg_price * 1.5, max_price)))
        else:
            # Mid-range prices
            prices.append(int(random.uniform(avg_price * 0.8, avg_price * 1.3)))
    
    return prices

def generate_property_queries_eval():
    """Generate evaluation data for property_queries.py"""
    print("Generating property queries evaluation data...")
    
    # Sample data from analysis
    bedrooms = range(
        es_data['properties']['bedrooms_range']['min'],
        es_data['properties']['bedrooms_range']['max'] + 1
    )
    bathrooms = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
    property_types = ["Condo", "Single Family Home", "Townhouse", "Apartment", "Loft"]
    
    # Generate search terms based on common real estate keywords
    search_terms = [
        "modern kitchen",
        "spacious living room",
        "hardwood floors",
        "updated bathroom",
        "great location",
        "quiet neighborhood",
        "close to schools",
        "luxury amenities",
        "garden view",
        "waterfront property",
        "downtown location",
        "family home",
        "investment opportunity",
        "move-in ready",
        "newly renovated",
        "pet friendly",
        "open floor plan",
        "natural light",
        "private parking",
        "historic charm"
    ]
    
    # Generate geo coordinates (San Francisco area)
    sf_coords = [
        {"lat": 37.7749, "lon": -122.4194, "name": "Downtown SF"},
        {"lat": 37.7599, "lon": -122.4148, "name": "Mission District"},
        {"lat": 37.7604, "lon": -122.4346, "name": "Castro"},
        {"lat": 37.7845, "lon": -122.4082, "name": "Union Square"},
        {"lat": 37.8027, "lon": -122.4187, "name": "Marina District"},
        {"lat": 37.7609, "lon": -122.4350, "name": "Noe Valley"},
        {"lat": 37.7833, "lon": -122.4167, "name": "Tenderloin"},
        {"lat": 37.7564, "lon": -122.4926, "name": "Sunset District"},
        {"lat": 37.7806, "lon": -122.4148, "name": "SOMA"},
        {"lat": 37.7903, "lon": -122.4089, "name": "Nob Hill"}
    ]
    
    prices = generate_price_values(20)
    
    eval_data = {
        "query_type": "property_queries",
        "description": "Evaluation dataset for property search queries including basic search, filters, geo-distance, and price ranges",
        "generated_at": datetime.now().isoformat(),
        "test_cases": []
    }
    
    # 1. Basic property search queries
    for i, term in enumerate(search_terms):
        eval_data["test_cases"].append({
            "test_id": f"basic_search_{i+1}",
            "query_type": "basic_property_search",
            "parameters": {
                "search_term": term,
                "size": 10
            },
            "expected_behavior": "Should return properties matching the search term in description or amenities",
            "validation_criteria": {
                "min_results": 0,
                "max_results": 10,
                "relevance_check": True
            }
        })
    
    # 2. Filtered property searches
    for i in range(20):
        min_price = random.choice(prices)
        max_price = min_price + random.randint(100000, 1000000)
        
        eval_data["test_cases"].append({
            "test_id": f"filtered_search_{i+1}",
            "query_type": "filtered_property_search",
            "parameters": {
                "property_type": random.choice(property_types),
                "min_price": min_price,
                "max_price": max_price,
                "min_bedrooms": random.choice(list(bedrooms)),
                "min_bathrooms": random.choice(bathrooms),
                "size": 20
            },
            "expected_behavior": "Should return properties matching all filter criteria",
            "validation_criteria": {
                "filters_applied": True,
                "price_within_range": True,
                "property_type_match": True
            }
        })
    
    # 3. Geo-distance searches
    for i, coord in enumerate(sf_coords):
        for radius in [1, 5, 10, 20]:
            if i * 4 + (radius // 5) >= 20:
                break
            eval_data["test_cases"].append({
                "test_id": f"geo_distance_{i * 4 + (radius // 5) + 1}",
                "query_type": "geo_distance_search",
                "parameters": {
                    "center_lat": coord["lat"],
                    "center_lon": coord["lon"],
                    "radius_km": radius,
                    "location_name": coord["name"],
                    "size": 15
                },
                "expected_behavior": f"Should return properties within {radius}km of {coord['name']}",
                "validation_criteria": {
                    "distance_check": True,
                    "max_distance_km": radius,
                    "sort_by_distance": True
                }
            })
    
    # 4. Price range searches with aggregations
    price_ranges = [
        (200000, 500000, "Entry level"),
        (500000, 800000, "Mid-range"),
        (800000, 1200000, "Upper mid-range"),
        (1200000, 2000000, "Luxury"),
        (2000000, 5000000, "Ultra-luxury"),
        (300000, 600000, "Starter homes"),
        (600000, 1000000, "Family homes"),
        (1000000, 1500000, "Executive homes"),
        (400000, 700000, "Investment properties"),
        (700000, 1100000, "Move-up homes")
    ]
    
    for i, (min_p, max_p, category) in enumerate(price_ranges[:20]):
        eval_data["test_cases"].append({
            "test_id": f"price_range_{i+1}",
            "query_type": "price_range_search",
            "parameters": {
                "min_price": min_p,
                "max_price": max_p,
                "category": category,
                "include_aggregations": True
            },
            "expected_behavior": f"Should return {category} properties with price analytics",
            "validation_criteria": {
                "price_within_range": True,
                "aggregations_present": True,
                "statistics_accurate": True
            }
        })
    
    # Save the evaluation dataset
    output_path = eval_dir / 'property_queries_eval.json'
    with open(output_path, 'w') as f:
        json.dump(eval_data, f, indent=2)
    
    print(f"✓ Generated {len(eval_data['test_cases'])} test cases for property_queries")
    return eval_data

def generate_aggregation_queries_eval():
    """Generate evaluation data for aggregation_queries.py"""
    print("Generating aggregation queries evaluation data...")
    
    neighborhoods = es_data['neighborhoods']['neighborhood_names'][:10] if es_data['neighborhoods']['neighborhood_names'] else [
        "Pacific Heights", "Mission District", "Sunset District", "SOMA", "Noe Valley",
        "Castro", "Marina District", "Richmond District", "Hayes Valley", "Potrero Hill"
    ]
    
    eval_data = {
        "query_type": "aggregation_queries",
        "description": "Evaluation dataset for aggregation queries including neighborhood stats and price distributions",
        "generated_at": datetime.now().isoformat(),
        "test_cases": []
    }
    
    # 1. Neighborhood statistics queries
    for i, neighborhood in enumerate(neighborhoods):
        eval_data["test_cases"].append({
            "test_id": f"neighborhood_stats_{i+1}",
            "query_type": "neighborhood_stats",
            "parameters": {
                "neighborhood_name": neighborhood,
                "include_property_types": True,
                "include_price_stats": True,
                "include_size_stats": True
            },
            "expected_behavior": f"Should return comprehensive statistics for {neighborhood}",
            "validation_criteria": {
                "has_price_stats": True,
                "has_property_distribution": True,
                "has_size_metrics": True
            }
        })
    
    # 2. Price distribution queries
    price_buckets = [
        {"interval": 100000, "min": 200000, "max": 2000000},
        {"interval": 250000, "min": 0, "max": 5000000},
        {"interval": 500000, "min": 500000, "max": 3000000},
        {"interval": 50000, "min": 300000, "max": 1000000},
        {"interval": 200000, "min": 400000, "max": 2000000}
    ]
    
    for i, bucket_config in enumerate(price_buckets):
        for j, neighborhood in enumerate(neighborhoods[:2]):
            eval_data["test_cases"].append({
                "test_id": f"price_distribution_{i * 2 + j + 1}",
                "query_type": "price_distribution",
                "parameters": {
                    "bucket_interval": bucket_config["interval"],
                    "min_price": bucket_config["min"],
                    "max_price": bucket_config["max"],
                    "neighborhood": neighborhood if j == 1 else None
                },
                "expected_behavior": "Should return price distribution in specified buckets",
                "validation_criteria": {
                    "has_buckets": True,
                    "bucket_size_correct": True,
                    "total_count_accurate": True
                }
            })
    
    # Save the evaluation dataset
    output_path = eval_dir / 'aggregation_queries_eval.json'
    with open(output_path, 'w') as f:
        json.dump(eval_data, f, indent=2)
    
    print(f"✓ Generated {len(eval_data['test_cases'])} test cases for aggregation_queries")
    return eval_data

def generate_semantic_queries_eval():
    """Generate evaluation data for semantic_query_search.py"""
    print("Generating semantic queries evaluation data...")
    
    # Natural language queries that should work with semantic search
    natural_queries = [
        "I need a home with good schools nearby for my kids",
        "Looking for a quiet place to retire with a garden",
        "Want something modern and close to tech companies",
        "Need a starter home that's affordable but nice",
        "Looking for an investment property with rental potential",
        "Want a luxury condo with city views",
        "Need a family-friendly neighborhood with parks",
        "Looking for a historic home with character",
        "Want a place near public transportation",
        "Need a home office space for remote work",
        "Looking for a property with outdoor entertainment area",
        "Want a walkable neighborhood with cafes and shops",
        "Need a pet-friendly building with amenities",
        "Looking for energy-efficient modern construction",
        "Want a fixer-upper with potential",
        "Need wheelchair accessible single-story home",
        "Looking for waterfront or water views",
        "Want a property in a gated community",
        "Need multi-generational living space",
        "Looking for a sustainable eco-friendly home"
    ]
    
    eval_data = {
        "query_type": "semantic_query_search",
        "description": "Evaluation dataset for natural language semantic search queries",
        "generated_at": datetime.now().isoformat(),
        "test_cases": []
    }
    
    # Generate semantic search test cases
    for i, query in enumerate(natural_queries):
        eval_data["test_cases"].append({
            "test_id": f"semantic_search_{i+1}",
            "query_type": "natural_language_search",
            "parameters": {
                "query": query,
                "use_embeddings": True,
                "size": 10,
                "min_score": 0.7
            },
            "expected_behavior": "Should return semantically relevant properties based on the natural language query",
            "validation_criteria": {
                "uses_vector_search": True,
                "relevance_score_threshold": 0.7,
                "context_understanding": True
            },
            "semantic_concepts": extract_concepts(query)
        })
    
    # Save the evaluation dataset
    output_path = eval_dir / 'semantic_query_search_eval.json'
    with open(output_path, 'w') as f:
        json.dump(eval_data, f, indent=2)
    
    print(f"✓ Generated {len(eval_data['test_cases'])} test cases for semantic_query_search")
    return eval_data

def extract_concepts(query: str) -> List[str]:
    """Extract key concepts from a natural language query."""
    concepts = []
    
    concept_map = {
        "schools": ["education", "family", "children"],
        "quiet": ["peaceful", "residential", "low-noise"],
        "garden": ["outdoor", "yard", "landscaping"],
        "modern": ["contemporary", "updated", "new"],
        "tech": ["silicon valley", "commute", "startups"],
        "affordable": ["budget", "value", "starter"],
        "investment": ["rental", "income", "ROI"],
        "luxury": ["high-end", "premium", "upscale"],
        "family": ["children", "schools", "safe"],
        "historic": ["vintage", "character", "classic"],
        "transportation": ["transit", "commute", "accessible"],
        "remote work": ["home office", "workspace", "quiet"],
        "entertainment": ["social", "hosting", "gathering"],
        "walkable": ["urban", "pedestrian", "convenient"],
        "pet": ["animal", "dog", "cat"],
        "efficient": ["green", "sustainable", "eco"],
        "fixer": ["renovation", "potential", "project"],
        "accessible": ["ADA", "disability", "mobility"],
        "waterfront": ["water", "view", "beach"],
        "gated": ["secure", "private", "exclusive"],
        "multi-generational": ["family", "in-law", "suite"]
    }
    
    query_lower = query.lower()
    for key, values in concept_map.items():
        if key in query_lower:
            concepts.extend([key] + values[:2])
    
    return list(set(concepts))[:5]

def generate_advanced_queries_eval():
    """Generate evaluation data for advanced_queries.py"""
    print("Generating advanced queries evaluation data...")
    
    eval_data = {
        "query_type": "advanced_queries",
        "description": "Evaluation dataset for advanced search queries including multi-entity and complex filters",
        "generated_at": datetime.now().isoformat(),
        "test_cases": []
    }
    
    # 1. Multi-entity searches (combining properties, neighborhoods, and Wikipedia)
    multi_entity_queries = [
        {
            "search_term": "Victorian architecture San Francisco",
            "entities": ["properties", "neighborhoods", "wikipedia"],
            "context": "architectural history"
        },
        {
            "search_term": "Golden Gate Park area homes",
            "entities": ["properties", "wikipedia"],
            "context": "location-based"
        },
        {
            "search_term": "Tech hub neighborhoods Silicon Valley",
            "entities": ["neighborhoods", "wikipedia"],
            "context": "economic zones"
        },
        {
            "search_term": "Historic Mission District properties",
            "entities": ["properties", "neighborhoods", "wikipedia"],
            "context": "cultural heritage"
        },
        {
            "search_term": "Earthquake-safe construction Bay Area",
            "entities": ["properties", "wikipedia"],
            "context": "safety features"
        }
    ]
    
    for i, query_config in enumerate(multi_entity_queries):
        eval_data["test_cases"].append({
            "test_id": f"multi_entity_{i+1}",
            "query_type": "multi_entity_search",
            "parameters": {
                "search_term": query_config["search_term"],
                "entities": query_config["entities"],
                "use_vector_search": True,
                "cross_reference": True
            },
            "expected_behavior": f"Should search across {', '.join(query_config['entities'])} for {query_config['context']}",
            "validation_criteria": {
                "includes_all_entities": True,
                "relevance_to_context": True,
                "cross_entity_correlation": True
            }
        })
    
    # 2. Complex filter combinations
    complex_filters = []
    for i in range(15):
        filters = {
            "test_id": f"complex_filter_{i+1}",
            "query_type": "complex_filtered_search",
            "parameters": {
                "filters": {
                    "price": {
                        "min": random.randint(3, 10) * 100000,
                        "max": random.randint(15, 50) * 100000
                    },
                    "size": {
                        "min_sqft": random.randint(8, 15) * 100,
                        "max_sqft": random.randint(20, 50) * 100
                    },
                    "features": {
                        "bedrooms": random.randint(2, 5),
                        "bathrooms": random.choice([1.5, 2, 2.5, 3, 3.5]),
                        "year_built_after": random.randint(1960, 2010)
                    },
                    "location": {
                        "neighborhoods": random.sample(
                            ["SOMA", "Mission", "Marina", "Pacific Heights", "Noe Valley"],
                            k=random.randint(1, 3)
                        )
                    }
                },
                "sort_by": random.choice(["price", "size", "year_built", "relevance"]),
                "include_similar": True
            },
            "expected_behavior": "Should apply all filters and return sorted results with similar properties",
            "validation_criteria": {
                "all_filters_applied": True,
                "sorting_correct": True,
                "similar_properties_included": True
            }
        }
        eval_data["test_cases"].append(filters)
    
    # Save the evaluation dataset
    output_path = eval_dir / 'advanced_queries_eval.json'
    with open(output_path, 'w') as f:
        json.dump(eval_data, f, indent=2)
    
    print(f"✓ Generated {len(eval_data['test_cases'])} test cases for advanced_queries")
    return eval_data

def generate_wikipedia_fulltext_eval():
    """Generate evaluation data for wikipedia_fulltext.py"""
    print("Generating Wikipedia fulltext search evaluation data...")
    
    # Topics relevant to real estate and San Francisco
    wikipedia_topics = [
        "Golden Gate Bridge history and construction",
        "San Francisco earthquake 1906 building codes",
        "Victorian architecture preservation",
        "Silicon Valley tech boom housing impact",
        "Bay Area rapid transit development",
        "Alcatraz Island tourism influence",
        "California housing crisis causes",
        "Sustainable building practices Bay Area",
        "Historic Painted Ladies Victorian homes",
        "San Francisco zoning laws evolution",
        "Fisherman's Wharf commercial development",
        "Mission District gentrification history",
        "Cable car system urban planning",
        "Bay Bridge engineering marvel",
        "Climate change coastal properties",
        "Affordable housing initiatives SF",
        "Chinatown cultural preservation",
        "Golden Gate Park urban design",
        "Tech industry housing displacement",
        "Rent control policies San Francisco"
    ]
    
    eval_data = {
        "query_type": "wikipedia_fulltext",
        "description": "Evaluation dataset for Wikipedia fulltext search queries",
        "generated_at": datetime.now().isoformat(),
        "test_cases": []
    }
    
    for i, topic in enumerate(wikipedia_topics):
        eval_data["test_cases"].append({
            "test_id": f"wiki_fulltext_{i+1}",
            "query_type": "wikipedia_fulltext_search",
            "parameters": {
                "search_query": topic,
                "use_fuzzy_matching": True,
                "include_snippets": True,
                "max_results": 10,
                "min_relevance_score": 0.6
            },
            "expected_behavior": f"Should return Wikipedia articles relevant to: {topic}",
            "validation_criteria": {
                "relevance_to_topic": True,
                "has_snippets": True,
                "fuzzy_matching_works": True
            },
            "expected_themes": extract_wiki_themes(topic)
        })
    
    # Save the evaluation dataset
    output_path = eval_dir / 'wikipedia_fulltext_eval.json'
    with open(output_path, 'w') as f:
        json.dump(eval_data, f, indent=2)
    
    print(f"✓ Generated {len(eval_data['test_cases'])} test cases for wikipedia_fulltext")
    return eval_data

def extract_wiki_themes(topic: str) -> List[str]:
    """Extract themes from Wikipedia search topic."""
    themes = []
    theme_keywords = {
        "history": ["history", "historic", "evolution", "development"],
        "architecture": ["architecture", "building", "construction", "design"],
        "technology": ["tech", "Silicon Valley", "innovation"],
        "culture": ["cultural", "community", "heritage", "preservation"],
        "transportation": ["transit", "cable car", "bridge", "BART"],
        "housing": ["housing", "homes", "properties", "real estate"],
        "policy": ["laws", "zoning", "control", "policies", "initiatives"],
        "environment": ["climate", "sustainable", "coastal"],
        "tourism": ["tourism", "Wharf", "Alcatraz", "attraction"],
        "urban": ["urban", "city", "downtown", "district"]
    }
    
    topic_lower = topic.lower()
    for theme, keywords in theme_keywords.items():
        if any(keyword.lower() in topic_lower for keyword in keywords):
            themes.append(theme)
    
    return themes[:3] if themes else ["general"]

def generate_rich_listing_eval():
    """Generate evaluation data for rich_listing_demo.py"""
    print("Generating rich listing evaluation data...")
    
    eval_data = {
        "query_type": "rich_listing_demo",
        "description": "Evaluation dataset for rich property listing queries with detailed information",
        "generated_at": datetime.now().isoformat(),
        "test_cases": []
    }
    
    # Generate rich listing queries
    listing_scenarios = [
        {
            "scenario": "Luxury penthouse showcase",
            "filters": {"min_price": 2000000, "property_type": "Condo", "min_sqft": 2500},
            "enrich_with": ["neighborhood_demographics", "nearby_amenities", "market_trends"]
        },
        {
            "scenario": "Family home with schools",
            "filters": {"bedrooms": 4, "bathrooms": 3, "max_price": 1500000},
            "enrich_with": ["school_ratings", "family_amenities", "safety_scores"]
        },
        {
            "scenario": "Investment property analysis",
            "filters": {"min_price": 500000, "max_price": 1000000},
            "enrich_with": ["rental_estimates", "cap_rates", "neighborhood_growth"]
        },
        {
            "scenario": "Starter home options",
            "filters": {"max_price": 700000, "bedrooms": 2},
            "enrich_with": ["first_time_buyer_programs", "mortgage_estimates", "commute_times"]
        },
        {
            "scenario": "Waterfront properties",
            "filters": {"min_price": 1500000},
            "enrich_with": ["flood_zones", "insurance_costs", "view_quality"]
        },
        {
            "scenario": "Historic homes tour",
            "filters": {"year_built_before": 1950},
            "enrich_with": ["historical_significance", "preservation_status", "renovation_history"]
        },
        {
            "scenario": "Eco-friendly homes",
            "filters": {"year_built_after": 2010},
            "enrich_with": ["energy_ratings", "solar_potential", "green_certifications"]
        },
        {
            "scenario": "Downtown high-rise living",
            "filters": {"property_type": "Condo", "min_floor": 10},
            "enrich_with": ["building_amenities", "HOA_details", "concierge_services"]
        },
        {
            "scenario": "Suburban family estates",
            "filters": {"min_sqft": 3500, "min_lot_size": 10000},
            "enrich_with": ["lot_features", "privacy_rating", "outdoor_amenities"]
        },
        {
            "scenario": "Fixer-upper opportunities",
            "filters": {"max_price": 800000, "year_built_before": 1980},
            "enrich_with": ["renovation_potential", "contractor_estimates", "ARV_analysis"]
        }
    ]
    
    for i, scenario in enumerate(listing_scenarios):
        eval_data["test_cases"].append({
            "test_id": f"rich_listing_{i+1}",
            "query_type": "rich_property_listing",
            "parameters": {
                "scenario": scenario["scenario"],
                "filters": scenario["filters"],
                "enrichment_data": scenario["enrich_with"],
                "include_photos": True,
                "include_virtual_tour": True,
                "include_neighborhood_context": True
            },
            "expected_behavior": f"Should return detailed property listings for: {scenario['scenario']}",
            "validation_criteria": {
                "has_basic_property_data": True,
                "has_enrichment_data": True,
                "filters_correctly_applied": True,
                "presentation_quality": True
            }
        })
        
        # Add comparison queries
        if i < 10:
            eval_data["test_cases"].append({
                "test_id": f"property_comparison_{i+1}",
                "query_type": "property_comparison",
                "parameters": {
                    "scenario": f"Compare {scenario['scenario']}",
                    "base_filters": scenario["filters"],
                    "comparison_properties": 3,
                    "comparison_metrics": [
                        "price_per_sqft",
                        "neighborhood_ranking",
                        "appreciation_potential",
                        "walkability_score"
                    ]
                },
                "expected_behavior": "Should compare similar properties with detailed metrics",
                "validation_criteria": {
                    "has_comparison_table": True,
                    "metrics_calculated": True,
                    "recommendations_provided": True
                }
            })
    
    # Save the evaluation dataset
    output_path = eval_dir / 'rich_listing_demo_eval.json'
    with open(output_path, 'w') as f:
        json.dump(eval_data, f, indent=2)
    
    print(f"✓ Generated {len(eval_data['test_cases'])} test cases for rich_listing_demo")
    return eval_data

def generate_master_evaluation_index():
    """Generate a master index file linking all evaluation datasets."""
    print("\nGenerating master evaluation index...")
    
    master_index = {
        "title": "Real Estate Search Evaluation Datasets",
        "description": "Comprehensive evaluation datasets for all demo query types in the real estate search system",
        "generated_at": datetime.now().isoformat(),
        "total_test_cases": 0,
        "datasets": []
    }
    
    # List all generated eval files
    eval_files = list(eval_dir.glob('*_eval.json'))
    
    for eval_file in eval_files:
        with open(eval_file, 'r') as f:
            data = json.load(f)
            dataset_info = {
                "filename": eval_file.name,
                "query_type": data.get("query_type", "unknown"),
                "description": data.get("description", ""),
                "test_case_count": len(data.get("test_cases", [])),
                "path": str(eval_file.relative_to(eval_dir.parent.parent))
            }
            master_index["datasets"].append(dataset_info)
            master_index["total_test_cases"] += dataset_info["test_case_count"]
    
    # Save master index
    index_path = eval_dir / 'evaluation_index.json'
    with open(index_path, 'w') as f:
        json.dump(master_index, f, indent=2)
    
    print(f"✓ Generated master index with {len(master_index['datasets'])} datasets")
    print(f"✓ Total test cases across all datasets: {master_index['total_test_cases']}")
    
    return master_index

def main():
    """Main function to generate all evaluation datasets."""
    print("="*60)
    print("GENERATING COMPREHENSIVE EVALUATION DATASETS")
    print("="*60)
    
    # Generate evaluation data for each query type
    results = []
    
    results.append(generate_property_queries_eval())
    results.append(generate_aggregation_queries_eval())
    results.append(generate_semantic_queries_eval())
    results.append(generate_advanced_queries_eval())
    results.append(generate_wikipedia_fulltext_eval())
    results.append(generate_rich_listing_eval())
    
    # Generate master index
    master_index = generate_master_evaluation_index()
    
    print("\n" + "="*60)
    print("EVALUATION DATASET GENERATION COMPLETE!")
    print("="*60)
    print(f"\nGenerated {len(results)} evaluation datasets")
    print(f"Total test cases: {master_index['total_test_cases']}")
    print(f"Output directory: {eval_dir}")
    print("\nDatasets created:")
    for dataset in master_index["datasets"]:
        print(f"  • {dataset['filename']}: {dataset['test_case_count']} test cases")
    
    return results

if __name__ == "__main__":
    main()