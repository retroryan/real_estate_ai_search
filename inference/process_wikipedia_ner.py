#!/usr/bin/env python3
"""
Enhanced Wikipedia NER Processing Script with Flexible Sampling
"""

import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, scan
from dotenv import load_dotenv
from typing import List, Dict, Tuple

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Elasticsearch configuration
ES_HOST = os.getenv('ES_HOST', 'localhost')
ES_PORT = int(os.getenv('ES_PORT', 9200))
ES_USERNAME = os.getenv('ES_USERNAME', 'elastic')
ES_PASSWORD = os.getenv('ES_PASSWORD')
ES_SCHEME = os.getenv('ES_SCHEME', 'http')

class WikipediaNERProcessor:
    def __init__(self, es_client):
        self.es = es_client
        self.stats = {
            'total_articles': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None
        }
    
    def get_source_indices(self) -> List[str]:
        """Get available Wikipedia source indices."""
        indices = self.es.indices.get(index="wiki*,wikipedia*")
        available = []
        
        for index_name in indices:
            # Check if index has documents
            count = self.es.count(index=index_name)['count']
            if count > 0:
                available.append(index_name)
                print(f"  📚 Found index '{index_name}' with {count:,} documents")
        
        return available
    
    def get_articles(self, source_index: str, sample_size: str, skip_existing: bool = True) -> List[Dict]:
        """Fetch articles from source index based on sampling strategy."""
        
        # Get already processed IDs if skipping existing
        processed_ids = set()
        if skip_existing and self.es.indices.exists(index='wikipedia_ner'):
            processed_ids = self._get_all_processed_ids()
            if processed_ids:
                print(f"  ℹ️ Found {len(processed_ids)} already processed articles to skip")
        
        if sample_size == 'all':
            print(f"📥 Fetching ALL unprocessed articles from '{source_index}'...")
            return self._get_all_articles(source_index, processed_ids)
        else:
            size = int(sample_size)
            print(f"📥 Fetching {size} sample articles from '{source_index}'...")
            return self._get_sample_articles(source_index, size, processed_ids)
    
    def _get_all_processed_ids(self) -> set:
        """Get all already processed article IDs from the NER index."""
        processed_ids = set()
        
        query = {
            "query": {
                "bool": {
                    "should": [
                        {"term": {"ner_processed": True}},
                        {"exists": {"field": "ner_entities"}}
                    ]
                }
            },
            "_source": ["page_id"]
        }
        
        try:
            for hit in scan(
                self.es,
                query=query,
                index='wikipedia_ner',
                scroll='2m',
                size=1000
            ):
                processed_ids.add(hit['_source']['page_id'])
        except Exception as e:
            print(f"  ⚠️ Error fetching processed IDs: {str(e)[:100]}")
        
        return processed_ids
    
    def _get_all_articles(self, index: str, exclude_ids: set = None) -> List[Dict]:
        """Fetch all articles using scan for efficiency."""
        articles = []
        exclude_ids = exclude_ids or set()
        
        query = {
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
        
        # Use scan for efficient retrieval of large result sets
        for hit in scan(
            self.es,
            query=query,
            index=index,
            scroll='2m',
            size=100
        ):
            source = hit['_source']
            page_id = source.get('page_id', hit['_id'])
            
            # Skip if already processed
            if page_id in exclude_ids:
                continue
            
            content = self._get_content(source)
            
            if content and len(content) > 50:
                articles.append(self._prepare_article(source, hit['_id'], content))
        
        return articles
    
    def _get_sample_articles(self, index: str, size: int, exclude_ids: set = None) -> List[Dict]:
        """Fetch a sample of articles."""
        exclude_ids = exclude_ids or set()
        
        # If we have many excludes, we need to fetch more to get enough unprocessed
        fetch_size = size * 2 if exclude_ids else size
        
        query = {
            "size": fetch_size,
            "query": {
                "function_score": {
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
                    "random_score": {}  # Random sampling
                }
            },
            "_source": ["title", "full_content", "page_id", "url", "city", "state", 
                       "short_summary", "long_summary", "categories", "key_topics"]
        }
        
        response = self.es.search(index=index, body=query)
        articles = []
        
        for hit in response['hits']['hits']:
            source = hit['_source']
            page_id = source.get('page_id', hit['_id'])
            
            # Skip if already processed
            if page_id in exclude_ids:
                continue
            
            content = self._get_content(source)
            
            if content and len(content) > 50:
                articles.append(self._prepare_article(source, hit['_id'], content))
                
                # Stop when we have enough articles
                if len(articles) >= size:
                    break
        
        return articles
    
    def _get_content(self, source: Dict) -> str:
        """Extract content from document, prioritizing full_content."""
        content = source.get('full_content')
        if not content or len(content) < 100:
            content = source.get('long_summary', '')
            if not content or len(content) < 100:
                content = source.get('short_summary', '')
        return content
    
    def _prepare_article(self, source: Dict, doc_id: str, content: str) -> Dict:
        """Prepare article document for processing."""
        return {
            'page_id': source.get('page_id', doc_id),
            'title': source.get('title', 'Unknown'),
            'full_content': content[:10000],  # Limit for NER processing
            'url': source.get('url', ''),
            'city': source.get('city', ''),
            'state': source.get('state', ''),
            'categories': source.get('categories', []),
            'key_topics': source.get('key_topics', [])
        }
    
    def check_already_processed(self, page_ids: List[str]) -> Tuple[List[str], List[str]]:
        """Check which articles have already been processed."""
        if not page_ids:
            return [], []
        
        # Check if index exists first
        if not self.es.indices.exists(index='wikipedia_ner'):
            return [], page_ids
        
        # Process in chunks if we have many IDs (terms query has limits)
        chunk_size = 1000
        all_processed = set()
        
        for i in range(0, len(page_ids), chunk_size):
            chunk_ids = page_ids[i:i + chunk_size]
            
            # Query to check existing documents
            query = {
                "size": chunk_size,
                "query": {
                    "terms": {
                        "page_id": chunk_ids
                    }
                },
                "_source": ["page_id", "ner_processed", "ner_entities"]
            }
            
            try:
                response = self.es.search(index='wikipedia_ner', body=query)
                
                for hit in response['hits']['hits']:
                    source = hit['_source']
                    # Consider processed if it has ner_processed=true OR has ner_entities
                    if source.get('ner_processed', False) or source.get('ner_entities'):
                        all_processed.add(source['page_id'])
                
            except Exception as e:
                print(f"  ⚠️ Error checking processed status: {str(e)[:100]}")
                # If there's an error, assume not processed
                pass
        
        new_ids = [pid for pid in page_ids if pid not in all_processed]
        return list(all_processed), new_ids
    
    def process_batch(self, articles: List[Dict], batch_size: int = 10) -> None:
        """Process articles in batches through the NER pipeline."""
        total_batches = (len(articles) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(articles))
            batch = articles[start_idx:end_idx]
            
            print(f"\n📦 Processing batch {batch_num + 1}/{total_batches} ({len(batch)} articles)")
            
            # Prepare bulk operations
            operations = []
            for article in batch:
                operations.append({
                    '_index': 'wikipedia_ner',
                    '_id': article['page_id'],
                    '_source': article,
                    'pipeline': 'wikipedia_ner_pipeline'
                })
            
            # Execute bulk indexing with pipeline
            try:
                success, errors = bulk(
                    self.es,
                    operations,
                    raise_on_error=False,
                    raise_on_exception=False
                )
                
                self.stats['successful'] += success
                
                if errors:
                    self.stats['failed'] += len(errors)
                    for error in errors[:3]:  # Show first 3 errors
                        print(f"  ⚠️ Error: {error}")
                
                print(f"  ✅ Processed: {success}/{len(batch)} articles")
                
                # Show sample of extracted entities
                self._show_sample_entities(batch[0]['page_id'])
                
            except Exception as e:
                self.stats['failed'] += len(batch)
                print(f"  ❌ Batch failed: {str(e)[:100]}")
            
            # Small delay between batches
            if batch_num < total_batches - 1:
                time.sleep(0.5)
    
    def _show_sample_entities(self, page_id: str) -> None:
        """Show entities from a processed document as an example."""
        try:
            doc = self.es.get(index='wikipedia_ner', id=page_id)
            source = doc['_source']
            
            if source.get('ner_processed'):
                orgs = source.get('ner_organizations', [])[:3]
                locs = source.get('ner_locations', [])[:3]
                pers = source.get('ner_persons', [])[:3]
                
                print(f"  📋 Sample entities from '{source['title'][:40]}...':")
                if orgs:
                    print(f"     🏢 Orgs: {', '.join(orgs)}")
                if locs:
                    print(f"     📍 Locs: {', '.join(locs)}")
                if pers:
                    print(f"     👤 Persons: {', '.join(pers)}")
        except:
            pass
    
    def process(self, source_index: str = None, sample_size: str = '10', 
                skip_existing: bool = True, batch_size: int = 10) -> Dict:
        """Main processing function."""
        
        self.stats['start_time'] = datetime.now()
        
        # Get source indices
        if not source_index:
            indices = self.get_source_indices()
            if not indices:
                print("❌ No Wikipedia indices found!")
                return self.stats
            source_index = indices[0]  # Use first available
        
        # Get articles
        articles = self.get_articles(source_index, sample_size, skip_existing)
        print(f"✅ Retrieved {len(articles)} articles")
        
        if not articles:
            print("❌ No articles to process")
            return self.stats
        
        self.stats['total_articles'] = len(articles)
        
        # Double-check for already processed articles (belt and suspenders approach)
        # This catches any that might have been processed since we fetched the list
        if skip_existing:
            page_ids = [a['page_id'] for a in articles]
            processed_ids, new_ids = self.check_already_processed(page_ids)
            
            if processed_ids:
                print(f"⏭️  Found {len(processed_ids)} recently processed articles, skipping...")
                self.stats['skipped'] = len(processed_ids)
                
                # Filter to only new articles
                articles = [a for a in articles if a['page_id'] in new_ids]
                
                if not articles:
                    print("✅ All articles already processed!")
                    return self.stats
        
        print(f"\n🔄 Processing {len(articles)} articles through NER pipeline...")
        print("=" * 60)
        
        # Process in batches
        self.process_batch(articles, batch_size)
        
        self.stats['end_time'] = datetime.now()
        
        return self.stats
    
    def show_statistics(self) -> None:
        """Display processing statistics."""
        print("\n" + "=" * 60)
        print("📊 Processing Statistics:")
        print(f"  📚 Total articles: {self.stats['total_articles']}")
        print(f"  ✅ Successful: {self.stats['successful']}")
        print(f"  ❌ Failed: {self.stats['failed']}")
        print(f"  ⏭️  Skipped: {self.stats['skipped']}")
        
        if self.stats['start_time'] and self.stats['end_time']:
            duration = self.stats['end_time'] - self.stats['start_time']
            print(f"  ⏱️  Duration: {duration.total_seconds():.1f} seconds")
            
            if self.stats['successful'] > 0:
                rate = self.stats['successful'] / duration.total_seconds()
                print(f"  📈 Processing rate: {rate:.1f} articles/second")
        
        success_rate = 0
        if self.stats['successful'] + self.stats['failed'] > 0:
            success_rate = (self.stats['successful'] / 
                          (self.stats['successful'] + self.stats['failed']) * 100)
            print(f"  🎯 Success rate: {success_rate:.1f}%")

def create_elasticsearch_client():
    """Create and return Elasticsearch client."""
    client = Elasticsearch(
        [f"{ES_SCHEME}://{ES_HOST}:{ES_PORT}"],
        basic_auth=(ES_USERNAME, ES_PASSWORD),
        verify_certs=False
    )
    return client

def verify_setup(es):
    """Verify NER model and pipeline are set up."""
    # Check model
    try:
        response = es.ml.get_trained_models_stats(
            model_id="elastic__distilbert-base-uncased-finetuned-conll03-english"
        )
        
        if response['trained_model_stats']:
            stats = response['trained_model_stats'][0]
            state = stats.get('deployment_stats', {}).get('state', 'not_deployed')
            
            if state != 'started':
                print(f"⚠️  Model state is '{state}'. Please run ./inference/install_ner_model.sh")
                return False
        else:
            print("❌ NER model not found! Please run ./inference/install_ner_model.sh")
            return False
    except:
        print("❌ Cannot check model status. Please run ./inference/install_ner_model.sh")
        return False
    
    # Check pipeline
    try:
        es.ingest.get_pipeline(id='wikipedia_ner_pipeline')
    except:
        print("❌ NER pipeline not found! Please run: python inference/setup_ner_pipeline.py")
        return False
    
    # Check index
    if not es.indices.exists(index='wikipedia_ner'):
        print("❌ NER index not found! Please run: python inference/setup_ner_pipeline.py")
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(
        description='Process Wikipedia articles through NER pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process 10 random articles (default)
  python process_wikipedia_ner.py
  
  # Process 100 articles
  python process_wikipedia_ner.py --sample 100
  
  # Process ALL articles (warning: this may take a while)
  python process_wikipedia_ner.py --sample all
  
  # Process from specific index
  python process_wikipedia_ner.py --source wiki_summaries --sample 50
  
  # Force reprocess existing articles
  python process_wikipedia_ner.py --sample 20 --force
  
  # Adjust batch size for performance
  python process_wikipedia_ner.py --sample 1000 --batch-size 25
        """
    )
    
    parser.add_argument(
        '--sample',
        default='10',
        help='Number of articles to process or "all" for entire index (default: 10)'
    )
    
    parser.add_argument(
        '--source',
        help='Source index name (default: auto-detect)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force reprocess articles that already exist in NER index'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Batch size for bulk processing (default: 10)'
    )
    
    args = parser.parse_args()
    
    print("🚀 Wikipedia NER Processing")
    print("=" * 60)
    
    # Create Elasticsearch client
    es = create_elasticsearch_client()
    
    # Verify connection
    if not es.ping():
        print("❌ Cannot connect to Elasticsearch!")
        return 1
    
    print("✅ Connected to Elasticsearch")
    
    # Verify setup
    if not verify_setup(es):
        print("\n⚠️  Please complete setup first:")
        print("  1. Run: ./inference/install_ner_model.sh")
        print("  2. Run: python inference/setup_ner_pipeline.py")
        return 1
    
    print("✅ NER model and pipeline verified")
    
    # Create processor and run
    processor = WikipediaNERProcessor(es)
    
    # Process articles
    stats = processor.process(
        source_index=args.source,
        sample_size=args.sample,
        skip_existing=not args.force,
        batch_size=args.batch_size
    )
    
    # Show statistics
    processor.show_statistics()
    
    # Show index statistics
    print("\n📈 Index Statistics:")
    count = es.count(index='wikipedia_ner')['count']
    print(f"  📚 Total documents in wikipedia_ner: {count:,}")
    
    print("\n✨ Processing complete!")
    print("Run 'python inference/search_ner.py' to test entity-based searches")
    
    return 0

if __name__ == "__main__":
    exit(main())