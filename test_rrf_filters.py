#!/usr/bin/env python3
"""
Test script to debug RRF query with combined city and state filters.
This tests the failing queries from demo 16:
- "Condo in San Jose CA" 
- "Family home in Salinas California"
"""

import json
import requests
from requests.auth import HTTPBasicAuth

# Elasticsearch configuration
ES_HOST = "localhost"
ES_PORT = 9200
ES_USER = "elastic"
ES_PASSWORD = "2GJXncaV"
INDEX = "properties"

def run_es_query(query_body, description):
    """Execute an Elasticsearch query and print results."""
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"{'='*60}")
    
    url = f"http://{ES_HOST}:{ES_PORT}/{INDEX}/_search"
    
    response = requests.post(
        url,
        json=query_body,
        auth=HTTPBasicAuth(ES_USER, ES_PASSWORD),
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 200:
        print(f"❌ Query failed with status {response.status_code}")
        print(response.text)
        return None
    
    result = response.json()
    total_hits = result['hits']['total']['value']
    print(f"✅ Query successful - Found {total_hits} results")
    
    if total_hits > 0:
        print("\nFirst 3 results:")
        for i, hit in enumerate(result['hits']['hits'][:3], 1):
            source = hit['_source']
            print(f"{i}. {source['property_type']} - {source['address']['city']}, {source['address']['state']} - ${source.get('price', 'N/A'):,.0f}")
    
    return result

def test_simple_filters():
    """Test basic filter queries to verify data exists."""
    
    # Test 1: Just city filter (San Jose)
    query1 = {
        "size": 5,
        "query": {
            "bool": {
                "filter": [
                    {"match": {"address.city": "San Jose"}}
                ]
            }
        }
    }
    run_es_query(query1, "Simple filter: City = San Jose")
    
    # Test 2: Just state filter (CA)
    query2 = {
        "size": 5,
        "query": {
            "bool": {
                "filter": [
                    {"term": {"address.state": "CA"}}
                ]
            }
        }
    }
    run_es_query(query2, "Simple filter: State = CA")
    
    # Test 3: Combined city + state filter
    query3 = {
        "size": 5,
        "query": {
            "bool": {
                "filter": [
                    {"match": {"address.city": "San Jose"}},
                    {"term": {"address.state": "CA"}}
                ]
            }
        }
    }
    run_es_query(query3, "Combined filter: City = San Jose AND State = CA")
    
    # Test 4: Combined with property type
    query4 = {
        "size": 5,
        "query": {
            "bool": {
                "must": [
                    {"match": {"property_type": "condo"}}
                ],
                "filter": [
                    {"match": {"address.city": "San Jose"}},
                    {"term": {"address.state": "CA"}}
                ]
            }
        }
    }
    run_es_query(query4, "Combined filter + query: Condos in San Jose, CA")

def test_rrf_queries():
    """Test RRF queries that are failing in the demo."""
    
    # Use a real embedding vector from an actual San Jose condo (prop-sf-017)
    # This ensures we have the correct dimensions (1024) and realistic values
    import json
    with open('/tmp/sample_property.json', 'r') as f:
        sample_data = json.load(f)
        dummy_vector = sample_data['hits']['hits'][0]['_source']['embedding']
    print(f"Using real embedding vector with {len(dummy_vector)} dimensions")
    
    # Test 1: RRF with city filter only
    query1 = {
        "retriever": {
            "rrf": {
                "retrievers": [
                    {
                        "standard": {
                            "query": {
                                "bool": {
                                    "must": {
                                        "multi_match": {
                                            "query": "condo",
                                            "fields": ["description^2", "features^1.5", "amenities^1.5"]
                                        }
                                    },
                                    "filter": [
                                        {"match": {"address.city": "San Jose"}}
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "knn": {
                            "field": "embedding",
                            "query_vector": dummy_vector,
                            "k": 10,
                            "num_candidates": 50,
                            "filter": [
                                {"match": {"address.city": "San Jose"}}
                            ]
                        }
                    }
                ]
            }
        },
        "size": 5
    }
    run_es_query(query1, "RRF Query: City filter only (San Jose)")
    
    # Test 2: RRF with city AND state filters (this is what's failing)
    query2 = {
        "retriever": {
            "rrf": {
                "retrievers": [
                    {
                        "standard": {
                            "query": {
                                "bool": {
                                    "must": {
                                        "multi_match": {
                                            "query": "condo",
                                            "fields": ["description^2", "features^1.5", "amenities^1.5"]
                                        }
                                    },
                                    "filter": [
                                        {"match": {"address.city": "San Jose"}},
                                        {"term": {"address.state": "CA"}}
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "knn": {
                            "field": "embedding",
                            "query_vector": dummy_vector,
                            "k": 10,
                            "num_candidates": 50,
                            "filter": [
                                {"match": {"address.city": "San Jose"}},
                                {"term": {"address.state": "CA"}}
                            ]
                        }
                    }
                ]
            }
        },
        "size": 5
    }
    run_es_query(query2, "RRF Query: City + State filters (San Jose, CA) - FAILING CASE")
    
    # Test 3: RRF with filters as single bool query
    query3 = {
        "retriever": {
            "rrf": {
                "retrievers": [
                    {
                        "standard": {
                            "query": {
                                "bool": {
                                    "must": {
                                        "multi_match": {
                                            "query": "condo",
                                            "fields": ["description^2", "features^1.5", "amenities^1.5"]
                                        }
                                    },
                                    "filter": {
                                        "bool": {
                                            "must": [
                                                {"match": {"address.city": "San Jose"}},
                                                {"term": {"address.state": "CA"}}
                                            ]
                                        }
                                    }
                                }
                            }
                        }
                    },
                    {
                        "knn": {
                            "field": "embedding",
                            "query_vector": dummy_vector,
                            "k": 10,
                            "num_candidates": 50,
                            "filter": {
                                "bool": {
                                    "must": [
                                        {"match": {"address.city": "San Jose"}},
                                        {"term": {"address.state": "CA"}}
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        },
        "size": 5
    }
    run_es_query(query3, "RRF Query: Filters wrapped in bool query")

def test_alternative_approaches():
    """Test alternative approaches to applying filters in RRF."""
    
    # Use the same real embedding vector
    import json
    with open('/tmp/sample_property.json', 'r') as f:
        sample_data = json.load(f)
        dummy_vector = sample_data['hits']['hits'][0]['_source']['embedding']
    
    # Test 1: Using a global query filter (post_filter style but in query)
    query1 = {
        "query": {
            "bool": {
                "filter": [
                    {"match": {"address.city": "San Jose"}},
                    {"term": {"address.state": "CA"}}
                ]
            }
        },
        "retriever": {
            "rrf": {
                "retrievers": [
                    {
                        "standard": {
                            "query": {
                                "multi_match": {
                                    "query": "condo",
                                    "fields": ["description^2", "features^1.5", "amenities^1.5"]
                                }
                            }
                        }
                    },
                    {
                        "knn": {
                            "field": "embedding",
                            "query_vector": dummy_vector,
                            "k": 10,
                            "num_candidates": 50
                        }
                    }
                ]
            }
        },
        "size": 5
    }
    
    try:
        run_es_query(query1, "Alternative: Global query filter with RRF")
    except Exception as e:
        print(f"❌ This approach failed: {e}")
    
    # Test 2: Using min_score to filter after RRF
    query2 = {
        "retriever": {
            "rrf": {
                "retrievers": [
                    {
                        "standard": {
                            "query": {
                                "bool": {
                                    "should": [
                                        {
                                            "multi_match": {
                                                "query": "condo San Jose CA",
                                                "fields": ["description^2", "features^1.5", "address.city^3", "address.state"]
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "knn": {
                            "field": "embedding",
                            "query_vector": dummy_vector,
                            "k": 10,
                            "num_candidates": 50
                        }
                    }
                ]
            }
        },
        "size": 5,
        "post_filter": {
            "bool": {
                "must": [
                    {"match": {"address.city": "San Jose"}},
                    {"term": {"address.state": "CA"}}
                ]
            }
        }
    }
    
    try:
        run_es_query(query2, "Alternative: Post-filter after RRF")
    except Exception as e:
        print(f"❌ This approach failed: {e}")

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("ELASTICSEARCH RRF FILTER DEBUGGING")
    print("Testing why 'Condo in San Jose CA' returns no results")
    print("="*60)
    
    print("\n📝 PHASE 1: Testing Simple Filters")
    print("-"*60)
    test_simple_filters()
    
    print("\n\n📝 PHASE 2: Testing RRF Queries") 
    print("-"*60)
    test_rrf_queries()
    
    print("\n\n📝 PHASE 3: Testing Alternative Approaches")
    print("-"*60)
    test_alternative_approaches()
    
    print("\n\n" + "="*60)
    print("DEBUGGING COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()