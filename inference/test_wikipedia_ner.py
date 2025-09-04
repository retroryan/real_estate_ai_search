#!/usr/bin/env python3
"""
Test script to process first 10 Wikipedia articles through NER pipeline
"""

import os
import json
import time
from pathlib import Path
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Elasticsearch configuration
ES_HOST = os.getenv('ES_HOST', 'localhost')
ES_PORT = int(os.getenv('ES_PORT', 9200))
ES_USERNAME = os.getenv('ES_USERNAME', 'elastic')
ES_PASSWORD = os.getenv('ES_PASSWORD')
ES_SCHEME = os.getenv('ES_SCHEME', 'http')

def create_elasticsearch_client():
    """Create and return Elasticsearch client."""
    client = Elasticsearch(
        [f"{ES_SCHEME}://{ES_HOST}:{ES_PORT}"],
        basic_auth=(ES_USERNAME, ES_PASSWORD),
        verify_certs=False
    )
    return client

def get_wikipedia_articles_from_index(es, limit=10):
    """Fetch existing Wikipedia articles from the main index."""
    
    # First, check which Wikipedia indices exist
    indices = es.indices.get(index="wiki*")
    
    if not indices:
        print("❌ No Wikipedia indices found. Please run the data pipeline first.")
        return []
    
    # Try to get articles from wiki_summaries first (has full content)
    wiki_index = None
    if 'wiki_summaries' in indices:
        wiki_index = 'wiki_summaries'
    elif 'wikipedia' in indices:
        wiki_index = 'wikipedia'
    else:
        wiki_index = list(indices.keys())[0]
    
    print(f"📚 Reading articles from index: {wiki_index}")
    
    # Query to get articles with content
    query = {
        "size": limit,
        "query": {
            "bool": {
                "must": [
                    {"exists": {"field": "full_content"}}
                ],
                "must_not": [
                    {"term": {"full_content": ""}}
                ]
            }
        },
        "_source": ["title", "full_content", "page_id", "url", "city", "state", 
                   "short_summary", "long_summary", "categories", "key_topics"]
    }
    
    try:
        response = es.search(index=wiki_index, body=query)
        articles = []
        
        for hit in response['hits']['hits']:
            source = hit['_source']
            
            # Use full_content if available, otherwise try summaries
            content = source.get('full_content')
            if not content or len(content) < 100:
                content = source.get('long_summary', '')
                if not content or len(content) < 100:
                    content = source.get('short_summary', '')
            
            if content and len(content) > 50:  # Skip very short content
                articles.append({
                    'page_id': source.get('page_id', hit['_id']),
                    'title': source.get('title', 'Unknown'),
                    'full_content': content[:10000],  # Limit content length
                    'url': source.get('url', ''),
                    'city': source.get('city', ''),
                    'state': source.get('state', ''),
                    'categories': source.get('categories', []),
                    'key_topics': source.get('key_topics', [])
                })
        
        print(f"✅ Found {len(articles)} articles with content")
        return articles
        
    except Exception as e:
        print(f"❌ Error fetching articles: {e}")
        return []

def process_articles_with_ner(es, articles):
    """Process articles through the NER pipeline."""
    
    if not articles:
        print("❌ No articles to process")
        return
    
    print(f"\n🔄 Processing {len(articles)} articles through NER pipeline...")
    print("=" * 60)
    
    successful = 0
    failed = 0
    
    for i, article in enumerate(articles, 1):
        print(f"\n📄 [{i}/{len(articles)}] Processing: {article['title'][:60]}...")
        print(f"   Content length: {len(article['full_content'])} chars")
        
        # Prepare document for indexing
        doc = {
            '_index': 'wikipedia_ner',
            '_id': article['page_id'],
            '_source': article,
            'pipeline': 'wikipedia_ner_pipeline'
        }
        
        try:
            # Index with pipeline
            response = es.index(
                index='wikipedia_ner',
                id=article['page_id'],
                document=article,
                pipeline='wikipedia_ner_pipeline'
            )
            
            if response['result'] in ['created', 'updated']:
                successful += 1
                
                # Retrieve the processed document to show entities
                time.sleep(0.5)  # Small delay to ensure indexing is complete
                
                processed = es.get(index='wikipedia_ner', id=article['page_id'])
                source = processed['_source']
                
                # Display extracted entities
                orgs = source.get('ner_organizations', [])
                locs = source.get('ner_locations', [])
                pers = source.get('ner_persons', [])
                misc = source.get('ner_misc', [])
                
                print(f"   ✅ Success!")
                print(f"   🏢 Organizations: {', '.join(orgs[:5])}{'...' if len(orgs) > 5 else ''}")
                print(f"   📍 Locations: {', '.join(locs[:5])}{'...' if len(locs) > 5 else ''}")
                print(f"   👤 Persons: {', '.join(pers[:5])}{'...' if len(pers) > 5 else ''}")
                if misc:
                    print(f"   🏷️  Misc: {', '.join(misc[:3])}{'...' if len(misc) > 3 else ''}")
                
                total_entities = len(source.get('ner_entities', []))
                print(f"   📊 Total entities found: {total_entities}")
            else:
                failed += 1
                print(f"   ⚠️  Unexpected result: {response['result']}")
                
        except Exception as e:
            failed += 1
            print(f"   ❌ Error: {str(e)[:100]}")
            
            # Check if it's a pipeline error
            if "ingest" in str(e).lower():
                print(f"   💡 Pipeline error - content may be too long or complex")
    
    print("\n" + "=" * 60)
    print(f"\n📊 Processing Summary:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📈 Success rate: {(successful/(successful+failed)*100):.1f}%")
    
    return successful, failed

def analyze_ner_results(es):
    """Analyze and display statistics about NER results."""
    
    print("\n📈 Analyzing NER Results...")
    print("=" * 60)
    
    # Get aggregations
    agg_query = {
        "size": 0,
        "aggs": {
            "total_docs": {
                "value_count": {"field": "page_id"}
            },
            "processed_docs": {
                "filter": {"term": {"ner_processed": True}},
                "aggs": {
                    "count": {"value_count": {"field": "page_id"}}
                }
            },
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
    
    try:
        response = es.search(index='wikipedia_ner', body=agg_query)
        aggs = response['aggregations']
        
        # Display top entities
        print("\n🏆 Top Entities Found:")
        
        print("\n📍 Top Locations:")
        for bucket in aggs['top_locations']['buckets'][:5]:
            print(f"   • {bucket['key']}: {bucket['doc_count']} occurrences")
        
        print("\n🏢 Top Organizations:")
        for bucket in aggs['top_organizations']['buckets'][:5]:
            print(f"   • {bucket['key']}: {bucket['doc_count']} occurrences")
        
        print("\n👤 Top Persons:")
        for bucket in aggs['top_persons']['buckets'][:5]:
            print(f"   • {bucket['key']}: {bucket['doc_count']} occurrences")
            
    except Exception as e:
        print(f"❌ Error analyzing results: {e}")

def run_sample_search(es):
    """Run a sample search to demonstrate NER-enhanced search."""
    
    print("\n🔍 Sample NER-Enhanced Search")
    print("=" * 60)
    
    # Search for documents mentioning specific organizations
    search_query = {
        "size": 3,
        "query": {
            "bool": {
                "should": [
                    {"term": {"ner_organizations": "university"}},
                    {"term": {"ner_locations": "san francisco"}},
                    {"term": {"ner_persons": "steve jobs"}}
                ]
            }
        },
        "_source": ["title", "ner_organizations", "ner_locations", "ner_persons"],
        "highlight": {
            "fields": {
                "full_content": {
                    "fragment_size": 150,
                    "number_of_fragments": 2
                }
            }
        }
    }
    
    try:
        response = es.search(index='wikipedia_ner', body=search_query)
        
        print("\n📝 Search Results (entities-based):")
        for hit in response['hits']['hits']:
            source = hit['_source']
            print(f"\n   📄 {source['title']}")
            print(f"      Score: {hit['_score']:.2f}")
            
            orgs = source.get('ner_organizations', [])[:3]
            locs = source.get('ner_locations', [])[:3]
            pers = source.get('ner_persons', [])[:3]
            
            if orgs:
                print(f"      🏢 Orgs: {', '.join(orgs)}")
            if locs:
                print(f"      📍 Locs: {', '.join(locs)}")
            if pers:
                print(f"      👤 Persons: {', '.join(pers)}")
                
    except Exception as e:
        print(f"❌ Error running search: {e}")

def main():
    print("🚀 Wikipedia NER Processing Test")
    print("=" * 60)
    
    # Create Elasticsearch client
    es = create_elasticsearch_client()
    
    # Verify connection
    if not es.ping():
        print("❌ Cannot connect to Elasticsearch!")
        return
    
    print("✅ Connected to Elasticsearch")
    
    # Check if NER index exists
    if not es.indices.exists(index='wikipedia_ner'):
        print("❌ NER index doesn't exist. Please run setup_ner_pipeline.py first!")
        return
    
    # Get Wikipedia articles
    articles = get_wikipedia_articles_from_index(es, limit=10)
    
    if not articles:
        print("\n⚠️  No Wikipedia articles found in existing indices.")
        print("Please run the data pipeline first to load Wikipedia data.")
        return
    
    # Process articles through NER pipeline
    successful, failed = process_articles_with_ner(es, articles)
    
    if successful > 0:
        # Analyze results
        analyze_ner_results(es)
        
        # Run sample search
        run_sample_search(es)
    
    print("\n" + "=" * 60)
    print("🎉 Test complete!")
    print(f"\n✨ Successfully processed {successful} Wikipedia articles with NER")
    print("You can now search the 'wikipedia_ner' index with entity-based queries!")
    
    print("\n💡 Example queries to try:")
    print("  • Find articles mentioning specific organizations")
    print("  • Search for articles about specific people")
    print("  • Locate articles discussing certain locations")
    print("  • Combine entity searches with full-text search")

if __name__ == "__main__":
    main()