#!/usr/bin/env python
"""
Analyze Elasticsearch data to understand available values for evaluation dataset generation.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Set
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

def connect_elasticsearch():
    """Connect to Elasticsearch"""
    return Elasticsearch(
        ['http://localhost:9200'],
        basic_auth=('elastic', os.getenv('ES_PASSWORD', '')) if os.getenv('ES_PASSWORD') else None
    )

def analyze_properties(es: Elasticsearch) -> Dict[str, Any]:
    """Analyze property data"""
    print("Analyzing properties index...")
    
    # Get sample properties
    result = es.search(
        index='properties',
        body={
            'size': 100,
            'query': {'match_all': {}},
            'aggs': {
                'property_types': {
                    'terms': {'field': 'property_type.keyword', 'size': 20}
                },
                'price_stats': {
                    'stats': {'field': 'price'}
                },
                'bedroom_stats': {
                    'stats': {'field': 'bedrooms'}
                },
                'bathroom_stats': {
                    'stats': {'field': 'bathrooms'}
                },
                'sqft_stats': {
                    'stats': {'field': 'square_feet'}
                },
                'cities': {
                    'terms': {'field': 'address.city.keyword', 'size': 20}
                },
                'neighborhoods': {
                    'terms': {'field': 'neighborhood_id.keyword', 'size': 50}
                },
                'year_built_stats': {
                    'stats': {'field': 'year_built'}
                }
            }
        }
    )
    
    properties = []
    amenities_set = set()
    descriptions = []
    
    for hit in result['hits']['hits']:
        prop = hit['_source']
        properties.append(prop)
        
        # Collect amenities
        if 'amenities' in prop:
            if isinstance(prop['amenities'], list):
                amenities_set.update(prop['amenities'])
        
        # Collect descriptions for text search examples
        if 'description' in prop:
            descriptions.append(prop['description'][:200])
    
    # Extract aggregation results
    aggs = result.get('aggregations', {})
    
    return {
        'total_count': result['hits']['total']['value'],
        'property_types': [bucket['key'] for bucket in aggs.get('property_types', {}).get('buckets', [])],
        'price_range': {
            'min': aggs.get('price_stats', {}).get('min', 0),
            'max': aggs.get('price_stats', {}).get('max', 0),
            'avg': aggs.get('price_stats', {}).get('avg', 0)
        },
        'bedrooms_range': {
            'min': int(aggs.get('bedroom_stats', {}).get('min', 0)) if aggs.get('bedroom_stats', {}).get('min') else 0,
            'max': int(aggs.get('bedroom_stats', {}).get('max', 0)) if aggs.get('bedroom_stats', {}).get('max') else 0,
            'avg': aggs.get('bedroom_stats', {}).get('avg', 0)
        },
        'bathrooms_range': {
            'min': aggs.get('bathroom_stats', {}).get('min', 0),
            'max': aggs.get('bathroom_stats', {}).get('max', 0),
            'avg': aggs.get('bathroom_stats', {}).get('avg', 0)
        },
        'sqft_range': {
            'min': aggs.get('sqft_stats', {}).get('min', 0),
            'max': aggs.get('sqft_stats', {}).get('max', 0),
            'avg': aggs.get('sqft_stats', {}).get('avg', 0)
        },
        'cities': [bucket['key'] for bucket in aggs.get('cities', {}).get('buckets', [])],
        'neighborhood_ids': [bucket['key'] for bucket in aggs.get('neighborhoods', {}).get('buckets', [])[:20]],
        'amenities': list(amenities_set)[:30],
        'sample_descriptions': descriptions[:5],
        'year_built_range': {
            'min': int(aggs.get('year_built_stats', {}).get('min', 1900)) if aggs.get('year_built_stats', {}).get('min') else 1900,
            'max': int(aggs.get('year_built_stats', {}).get('max', 2024)) if aggs.get('year_built_stats', {}).get('max') else 2024
        },
        'sample_properties': properties[:3]  # Keep a few full examples
    }

def analyze_neighborhoods(es: Elasticsearch) -> Dict[str, Any]:
    """Analyze neighborhood data"""
    print("Analyzing neighborhoods index...")
    
    result = es.search(
        index='neighborhoods',
        body={
            'size': 50,
            'query': {'match_all': {}},
            'aggs': {
                'avg_price_stats': {
                    'stats': {'field': 'average_price'}
                },
                'population_stats': {
                    'stats': {'field': 'population'}
                },
                'crime_rate_stats': {
                    'stats': {'field': 'crime_rate'}
                }
            }
        }
    )
    
    neighborhoods = []
    names = []
    descriptions = []
    
    for hit in result['hits']['hits']:
        n = hit['_source']
        neighborhoods.append({
            'neighborhood_id': n.get('neighborhood_id'),
            'name': n.get('name'),
            'city': n.get('city'),
            'state': n.get('state')
        })
        if 'name' in n:
            names.append(n['name'])
        if 'description' in n:
            descriptions.append(n['description'][:200])
    
    aggs = result.get('aggregations', {})
    
    return {
        'total_count': result['hits']['total']['value'],
        'neighborhood_names': names[:20],
        'sample_descriptions': descriptions[:5],
        'avg_price_range': {
            'min': aggs.get('avg_price_stats', {}).get('min', 0) if aggs.get('avg_price_stats', {}).get('count', 0) > 0 else 0,
            'max': aggs.get('avg_price_stats', {}).get('max', 0) if aggs.get('avg_price_stats', {}).get('count', 0) > 0 else 0
        },
        'population_range': {
            'min': aggs.get('population_stats', {}).get('min', 0) if aggs.get('population_stats', {}).get('count', 0) > 0 else 0,
            'max': aggs.get('population_stats', {}).get('max', 0) if aggs.get('population_stats', {}).get('count', 0) > 0 else 0
        },
        'sample_neighborhoods': neighborhoods[:10]
    }

def analyze_wikipedia(es: Elasticsearch) -> Dict[str, Any]:
    """Analyze Wikipedia data"""
    print("Analyzing Wikipedia indices...")
    
    # Check wikipedia index
    try:
        wikipedia_result = es.search(
            index='wikipedia',
            body={
                'size': 20,
                'query': {'match_all': {}},
                'aggs': {
                    'categories': {
                        'terms': {'field': 'categories.keyword', 'size': 30}
                    }
                }
            }
        )
    except Exception as e:
        print(f"  wikipedia index not found: {e}")
        wikipedia_result = {'hits': {'total': {'value': 0}, 'hits': []}}
    
    # For backwards compatibility
    summaries_result = wikipedia_result
    chunks_result = wikipedia_result
    
    titles = []
    sample_content = []
    categories = set()
    
    for hit in summaries_result['hits']['hits']:
        wiki = hit['_source']
        if 'title' in wiki:
            titles.append(wiki['title'])
        if 'summary' in wiki:
            sample_content.append(wiki['summary'][:200])
        if 'categories' in wiki and isinstance(wiki['categories'], list):
            categories.update(wiki['categories'])
    
    return {
        'summaries_count': summaries_result['hits']['total']['value'],
        'chunks_count': chunks_result['hits']['total']['value'],
        'sample_titles': titles[:15],
        'sample_content': sample_content[:5],
        'categories': list(categories)[:20]
    }

def get_sample_coordinates(es: Elasticsearch) -> List[Dict[str, float]]:
    """Get sample property coordinates for geo queries"""
    print("Getting sample coordinates...")
    
    result = es.search(
        index='properties',
        body={
            'size': 20,
            'query': {'exists': {'field': 'location'}},
            '_source': ['location', 'address.city']
        }
    )
    
    coords = []
    for hit in result['hits']['hits']:
        if 'location' in hit['_source']:
            loc = hit['_source']['location']
            coords.append({
                'lat': loc['lat'],
                'lon': loc['lon'],
                'city': hit['_source'].get('address', {}).get('city', 'Unknown')
            })
    
    return coords[:10]

def main():
    """Main analysis function"""
    es = connect_elasticsearch()
    
    # Check connection
    if not es.ping():
        print("ERROR: Cannot connect to Elasticsearch")
        return
    
    print("Connected to Elasticsearch successfully!")
    
    # Check available indices
    indices = es.indices.get_alias(index="*")
    print(f"\nAvailable indices: {', '.join(indices.keys())}")
    
    # Analyze each index
    analysis = {
        'properties': analyze_properties(es),
        'neighborhoods': analyze_neighborhoods(es),
        'wikipedia': analyze_wikipedia(es),
        'sample_coordinates': get_sample_coordinates(es)
    }
    
    # Save analysis results
    output_path = Path('es_data_analysis.json')
    with open(output_path, 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    
    print(f"\nAnalysis complete! Results saved to {output_path}")
    
    # Print summary
    print("\n=== DATA SUMMARY ===")
    print(f"Properties: {analysis['properties']['total_count']} documents")
    print(f"Property Types: {', '.join(analysis['properties']['property_types'][:5])}")
    print(f"Cities: {', '.join(analysis['properties']['cities'][:5])}")
    print(f"Price Range: ${analysis['properties']['price_range']['min']:,.0f} - ${analysis['properties']['price_range']['max']:,.0f}")
    
    print(f"\nNeighborhoods: {analysis['neighborhoods']['total_count']} documents")
    print(f"Sample Names: {', '.join(analysis['neighborhoods']['neighborhood_names'][:5])}")
    
    print(f"\nWikipedia Summaries: {analysis['wikipedia']['summaries_count']} documents")
    print(f"Wikipedia Chunks: {analysis['wikipedia']['chunks_count']} documents")
    
    return analysis

if __name__ == '__main__':
    main()