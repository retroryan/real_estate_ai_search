#!/usr/bin/env python3
"""
NER-Enhanced Search Testing Script
Test various entity-based searches on the Wikipedia NER index
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
from tabulate import tabulate

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Elasticsearch configuration
ES_HOST = os.getenv('ES_HOST', 'localhost')
ES_PORT = int(os.getenv('ES_PORT', 9200))
ES_USERNAME = os.getenv('ES_USERNAME', 'elastic')
ES_PASSWORD = os.getenv('ES_PASSWORD')
ES_SCHEME = os.getenv('ES_SCHEME', 'http')

class NERSearchTester:
    def __init__(self, es_client):
        self.es = es_client
        self.test_results = []
    
    def run_search(self, query: Dict, description: str, max_results: int = 5) -> Dict:
        """Execute a search query and return results."""
        print(f"\n🔍 {description}")
        print("-" * 60)
        
        try:
            response = self.es.search(index='wikipedia_ner', body=query)
            hits = response['hits']
            
            result = {
                'description': description,
                'total_hits': hits['total']['value'],
                'max_score': hits['max_score'],
                'results': []
            }
            
            if hits['hits']:
                print(f"Found {hits['total']['value']} results (showing top {min(max_results, len(hits['hits']))})")
                print()
                
                for i, hit in enumerate(hits['hits'][:max_results], 1):
                    source = hit['_source']
                    result['results'].append({
                        'title': source['title'],
                        'score': hit['_score']
                    })
                    
                    print(f"{i}. {source['title']}")
                    print(f"   Score: {hit['_score']:.3f}")
                    
                    # Show relevant entities
                    self._show_entities(source)
                    
                    # Show highlights if available
                    if 'highlight' in hit:
                        self._show_highlights(hit['highlight'])
                    
                    print()
            else:
                print("No results found")
            
            self.test_results.append(result)
            return result
            
        except Exception as e:
            print(f"❌ Search failed: {e}")
            return {'error': str(e)}
    
    def _show_entities(self, source: Dict, max_per_type: int = 5) -> None:
        """Display entities from a document."""
        entities = []
        
        orgs = source.get('ner_organizations', [])[:max_per_type]
        if orgs:
            entities.append(f"🏢 Orgs: {', '.join(orgs)}")
        
        locs = source.get('ner_locations', [])[:max_per_type]
        if locs:
            entities.append(f"📍 Locs: {', '.join(locs)}")
        
        pers = source.get('ner_persons', [])[:max_per_type]
        if pers:
            entities.append(f"👤 People: {', '.join(pers)}")
        
        misc = source.get('ner_misc', [])[:max_per_type]
        if misc:
            entities.append(f"🏷️ Misc: {', '.join(misc)}")
        
        if entities:
            for entity_line in entities:
                print(f"   {entity_line}")
    
    def _show_highlights(self, highlights: Dict) -> None:
        """Display search highlights."""
        for field, fragments in highlights.items():
            if fragments:
                print(f"   📝 Excerpt: ...{fragments[0][:150]}...")
    
    def _explain_test(self, test_type: str, explanation: str) -> None:
        """Display explanation for what the test does."""
        print(f"\n💡 **{test_type}**: {explanation}")
        print()
    
    def test_entity_searches(self) -> None:
        """Run a series of test searches demonstrating different capabilities."""
        
        print("\n" + "=" * 70)
        print("🧪 TESTING NER-ENHANCED SEARCH CAPABILITIES")
        print("=" * 70)
        
        # Test 1: Search by organization
        org_query = {
            "size": 5,
            "query": {
                "term": {
                    "ner_organizations": "university"
                }
            },
            "_source": ["title", "ner_organizations", "ner_locations"]
        }
        self.run_search(org_query, "Test 1: Find articles mentioning universities")
        self._explain_test(
            "Organization Search",
            "Uses exact term matching on the 'ner_organizations' field to find articles containing "
            "specific organizations. The NER model identifies and extracts organization names from text."
        )
        
        # Test 2: Search by location
        location_query = {
            "size": 5,
            "query": {
                "terms": {
                    "ner_locations": ["california", "san francisco", "los angeles"]
                }
            },
            "_source": ["title", "ner_locations", "city", "state"]
        }
        self.run_search(location_query, "Test 2: Find articles about California locations")
        self._explain_test(
            "Location Search",
            "Uses 'terms' query to match multiple location values at once. Searches the 'ner_locations' "
            "field which contains all geographical entities extracted by the NER model."
        )
        
        # Test 3: Search by person (if any found)
        person_query = {
            "size": 5,
            "query": {
                "exists": {
                    "field": "ner_persons"
                }
            },
            "_source": ["title", "ner_persons", "ner_organizations"]
        }
        self.run_search(person_query, "Test 3: Find articles mentioning people")
        self._explain_test(
            "Person Entity Search",
            "Uses 'exists' query to find any documents that have person entities. Useful for finding "
            "biographical content or articles that mention specific individuals."
        )
        
        # Test 4: Multi-entity search
        multi_entity_query = {
            "size": 5,
            "query": {
                "bool": {
                    "should": [
                        {"term": {"ner_organizations": "college"}},
                        {"term": {"ner_locations": "park"}},
                        {"term": {"ner_misc": "american"}}
                    ],
                    "minimum_should_match": 2
                }
            },
            "_source": ["title", "ner_organizations", "ner_locations", "ner_misc"]
        }
        self.run_search(multi_entity_query, "Test 4: Multi-entity search (at least 2 entity types)")
        self._explain_test(
            "Multi-Entity Boolean Search",
            "Combines multiple entity types using 'should' clauses with 'minimum_should_match=2'. "
            "Finds documents that contain at least 2 of the specified entity types, useful for complex queries."
        )
        
        # Test 5: Combined full-text and entity search
        combined_query = {
            "size": 5,
            "query": {
                "bool": {
                    "must": [
                        {"match": {"full_content": "history"}}
                    ],
                    "should": [
                        {"term": {"ner_organizations": "museum"}},
                        {"term": {"ner_locations": "california"}}
                    ]
                }
            },
            "_source": ["title", "ner_organizations", "ner_locations"],
            "highlight": {
                "fields": {
                    "full_content": {
                        "fragment_size": 100,
                        "number_of_fragments": 1
                    }
                }
            }
        }
        self.run_search(combined_query, "Test 5: Combined text + entity search (history + museum/california)")
        self._explain_test(
            "Hybrid Search",
            "Combines full-text search on content with entity-based filtering. 'must' clause requires "
            "text match while 'should' clauses boost documents with specific entities. Demonstrates semantic + structured search."
        )
        
        # Test 6: Entity aggregation
        agg_query = {
            "size": 0,
            "aggs": {
                "top_organizations": {
                    "terms": {
                        "field": "ner_organizations",
                        "size": 10
                    }
                },
                "top_locations": {
                    "terms": {
                        "field": "ner_locations",
                        "size": 10
                    }
                },
                "top_persons": {
                    "terms": {
                        "field": "ner_persons",
                        "size": 10
                    }
                }
            }
        }
        self.run_aggregations(agg_query, "Test 6: Entity frequency analysis")
        self._explain_test(
            "Entity Aggregations",
            "Analyzes entity distribution across the corpus using 'terms' aggregations. Returns the most "
            "frequent organizations, locations, and persons without returning documents (size=0)."
        )
        
        # Test 7: Geo + Entity search
        if self.check_geo_data():
            geo_entity_query = {
                "size": 5,
                "query": {
                    "bool": {
                        "must": [
                            {"exists": {"field": "location"}}
                        ],
                        "should": [
                            {"term": {"ner_organizations": "airport"}},
                            {"term": {"ner_locations": "bay"}}
                        ]
                    }
                },
                "_source": ["title", "city", "state", "ner_organizations", "ner_locations"]
            }
            self.run_search(geo_entity_query, "Test 7: Geo-located articles with specific entities")
            self._explain_test(
                "Geo + Entity Combined Search",
                "Requires documents to have geographic coordinates AND matches entity criteria. Useful for "
                "location-aware entity searches like 'airports near San Francisco'."
            )
        
        # Test 8: Entity co-occurrence
        cooccurrence_query = {
            "size": 5,
            "query": {
                "bool": {
                    "must": [
                        {"exists": {"field": "ner_organizations"}},
                        {"exists": {"field": "ner_locations"}}
                    ]
                }
            },
            "_source": ["title", "ner_organizations", "ner_locations"],
            "sort": [
                {"_score": "desc"}
            ]
        }
        self.run_search(cooccurrence_query, "Test 8: Articles with both organizations and locations")
        self._explain_test(
            "Entity Co-occurrence",
            "Finds documents containing multiple entity types using 'exists' queries with 'must' clauses. "
            "Useful for relationship discovery and finding documents with rich entity content."
        )
    
    def run_aggregations(self, query: Dict, description: str) -> None:
        """Run aggregation query and display results."""
        print(f"\n📊 {description}")
        print("-" * 60)
        
        try:
            response = self.es.search(index='wikipedia_ner', body=query)
            aggs = response['aggregations']
            
            total_entities_found = 0
            
            # Display top organizations
            if 'top_organizations' in aggs:
                print("\n🏢 Top Organizations:")
                for bucket in aggs['top_organizations']['buckets'][:5]:
                    print(f"   {bucket['key']}: {bucket['doc_count']} articles")
                total_entities_found += len(aggs['top_organizations']['buckets'])
            
            # Display top locations
            if 'top_locations' in aggs:
                print("\n📍 Top Locations:")
                for bucket in aggs['top_locations']['buckets'][:5]:
                    print(f"   {bucket['key']}: {bucket['doc_count']} articles")
                total_entities_found += len(aggs['top_locations']['buckets'])
            
            # Display top persons
            if 'top_persons' in aggs:
                persons = aggs['top_persons']['buckets']
                if persons:
                    print("\n👤 Top People:")
                    for bucket in persons[:5]:
                        print(f"   {bucket['key']}: {bucket['doc_count']} articles")
                    total_entities_found += len(persons)
                else:
                    print("\n👤 No people entities found in the index")
            
            # Add result summary for aggregations with meaningful counts
            self.test_results.append({
                'description': description,
                'total_hits': f'{total_entities_found} unique',
                'max_score': 'Aggregation',
                'results': []
            })
            
        except Exception as e:
            print(f"❌ Aggregation failed: {e}")
    
    def check_geo_data(self) -> bool:
        """Check if geo data is available."""
        try:
            response = self.es.count(
                index='wikipedia_ner',
                body={"query": {"exists": {"field": "location"}}}
            )
            return response['count'] > 0
        except:
            return False
    
    def custom_search(self) -> None:
        """Allow user to run custom searches."""
        print("\n" + "=" * 70)
        print("🎯 CUSTOM ENTITY SEARCH")
        print("=" * 70)
        print("\nEnter entity searches (or 'quit' to exit):")
        print("Format: <entity_type>:<search_term>")
        print("Types: org, loc, per, misc")
        print("Example: org:microsoft")
        print("         loc:seattle")
        print()
        
        while True:
            search_input = input("Search > ").strip()
            
            if search_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if ':' not in search_input:
                print("Invalid format. Use <type>:<term> (e.g., org:google)")
                continue
            
            entity_type, search_term = search_input.split(':', 1)
            entity_type = entity_type.lower().strip()
            search_term = search_term.lower().strip()
            
            # Map short names to field names
            field_map = {
                'org': 'ner_organizations',
                'loc': 'ner_locations',
                'per': 'ner_persons',
                'misc': 'ner_misc'
            }
            
            if entity_type not in field_map:
                print(f"Unknown entity type: {entity_type}. Use: org, loc, per, or misc")
                continue
            
            field = field_map[entity_type]
            
            # Build and run query
            query = {
                "size": 5,
                "query": {
                    "term": {
                        field: search_term
                    }
                },
                "_source": ["title", field],
                "highlight": {
                    "fields": {
                        "full_content": {
                            "fragment_size": 150,
                            "number_of_fragments": 1,
                            "pre_tags": ["**"],
                            "post_tags": ["**"]
                        }
                    }
                }
            }
            
            self.run_search(query, f"Custom search: {entity_type}={search_term}")
    
    def show_summary(self) -> None:
        """Display summary of all test results."""
        print("\n" + "=" * 70)
        print("📋 SEARCH TEST SUMMARY")
        print("=" * 70)
        
        if not self.test_results:
            print("No test results to display")
            return
        
        # Create summary table
        table_data = []
        for result in self.test_results:
            if 'error' not in result:
                # Handle different result types
                total_hits = result['total_hits']
                max_score = result['max_score']
                
                # Format max_score appropriately
                if isinstance(max_score, str):
                    score_str = max_score
                elif max_score is not None:
                    score_str = f"{max_score:.2f}"
                else:
                    score_str = "N/A"
                
                # For aggregations, show entity count instead of result count
                if score_str == "Aggregation":
                    shown = total_hits.split()[0] if isinstance(total_hits, str) and 'unique' in total_hits else len(result['results'])
                else:
                    shown = len(result['results'])
                    
                table_data.append([
                    result['description'][:40] + "...",
                    total_hits,
                    score_str,
                    shown
                ])
        
        if table_data:
            print(tabulate(
                table_data,
                headers=['Test', 'Total Hits', 'Max Score', 'Shown'],
                tablefmt='grid'
            ))
        
        # Add score explanation
        print("\n📊 **Understanding Elasticsearch Scores:**")
        print("-" * 60)
        print("• **Score Range**: 0 to unbounded (typically 0-10 for most queries)")
        print("• **Score Calculation**: Based on TF-IDF, field length, and query complexity")
        print("• **Score Interpretation**:")
        print("  - **> 5.0**: Excellent match - highly relevant")
        print("  - **2.0-5.0**: Good match - relevant")
        print("  - **1.0-2.0**: Fair match - somewhat relevant")
        print("  - **< 1.0**: Weak match - marginally relevant")
        print("\n• **Factors Affecting Score**:")
        print("  - Term frequency (TF): How often the term appears")
        print("  - Inverse document frequency (IDF): How rare the term is")
        print("  - Field boost: Some fields weighted more heavily")
        print("  - Query type: 'term' queries score differently than 'match'")
        print("  - Multiple matches: Documents matching multiple criteria score higher")
        
        # Show index statistics
        try:
            stats = self.es.count(index='wikipedia_ner')
            print(f"\n📊 Index Statistics:")
            print(f"   Total documents: {stats['count']:,}")
            
            # Get processing stats
            processed = self.es.count(
                index='wikipedia_ner',
                body={"query": {"term": {"ner_processed": True}}}
            )
            print(f"   NER processed: {processed['count']:,}")
            
        except Exception as e:
            print(f"Could not retrieve index statistics: {e}")

def create_elasticsearch_client():
    """Create and return Elasticsearch client."""
    client = Elasticsearch(
        [f"{ES_SCHEME}://{ES_HOST}:{ES_PORT}"],
        basic_auth=(ES_USERNAME, ES_PASSWORD),
        verify_certs=False
    )
    return client

def main():
    print("🔬 NER-Enhanced Search Testing Suite")
    print("=" * 70)
    
    # Create Elasticsearch client
    es = create_elasticsearch_client()
    
    # Verify connection
    if not es.ping():
        print("❌ Cannot connect to Elasticsearch!")
        return 1
    
    print("✅ Connected to Elasticsearch")
    
    # Check if NER index exists
    if not es.indices.exists(index='wikipedia_ner'):
        print("❌ Wikipedia NER index not found!")
        print("Please run: python inference/process_wikipedia_ner.py")
        return 1
    
    # Check document count
    count = es.count(index='wikipedia_ner')['count']
    if count == 0:
        print("❌ NER index is empty!")
        print("Please run: python inference/process_wikipedia_ner.py")
        return 1
    
    print(f"✅ Found {count:,} documents in wikipedia_ner index")
    
    # Create tester and run tests
    tester = NERSearchTester(es)
    
    # Run automated tests
    tester.test_entity_searches()
    
    # Show summary
    tester.show_summary()
    
    # Offer custom search
    print("\n" + "=" * 70)
    response = input("\nWould you like to try custom entity searches? (y/n): ")
    if response.lower() == 'y':
        tester.custom_search()
    
    print("\n✨ Search testing complete!")
    
    return 0

if __name__ == "__main__":
    exit(main())