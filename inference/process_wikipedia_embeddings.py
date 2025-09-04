#!/usr/bin/env python3
"""
Process Wikipedia Articles to Generate Text Embeddings for Semantic Search
Supports flexible sampling, batch processing, and incremental updates
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
import numpy as np

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Elasticsearch configuration
ES_HOST = os.getenv('ES_HOST', 'localhost')
ES_PORT = int(os.getenv('ES_PORT', 9200))
ES_USERNAME = os.getenv('ES_USERNAME', 'elastic')
ES_PASSWORD = os.getenv('ES_PASSWORD')
ES_SCHEME = os.getenv('ES_SCHEME', 'http')

# Model configuration
MODEL_ID = "sentence-transformers__all-minilm-l6-v2"
EMBEDDING_DIM = 384

class WikipediaEmbeddingProcessor:
    def __init__(self, es_client):
        self.es = es_client
        self.stats = {
            'total_articles': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None,
            'total_embeddings_created': 0
        }
    
    def get_source_indices(self) -> List[str]:
        """Get available Wikipedia source indices."""
        indices = self.es.indices.get(index="wiki*,wikipedia*")
        available = []
        
        for index_name in indices:
            # Skip our embedding indices
            if 'embedding' in index_name or 'ner' in index_name:
                continue
                
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
        if skip_existing and self.es.indices.exists(index='wikipedia_embeddings'):
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
        """Get all already processed article IDs from the embeddings index."""
        processed_ids = set()
        
        query = {
            "query": {
                "term": {
                    "embeddings_processed": True
                }
            },
            "_source": ["page_id"]
        }
        
        try:
            for hit in scan(
                self.es,
                query=query,
                index='wikipedia_embeddings',
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
                       "short_summary", "long_summary", "categories", "key_topics",
                       "location", "relevance_score"]
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
        
        # Fetch extra to account for excluded articles
        fetch_size = size * 3 if exclude_ids else size
        
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
                       "short_summary", "long_summary", "categories", "key_topics",
                       "location", "relevance_score"]
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
            'full_content': content[:10000],  # Limit for processing
            'url': source.get('url', ''),
            'city': source.get('city', ''),
            'state': source.get('state', ''),
            'categories': source.get('categories', []),
            'key_topics': source.get('key_topics', []),
            'location': source.get('location'),
            'relevance_score': source.get('relevance_score'),
            'short_summary': source.get('short_summary', ''),
            'long_summary': source.get('long_summary', '')
        }
    
    def check_already_processed(self, page_ids: List[str]) -> Tuple[List[str], List[str]]:
        """Check which articles have already been processed."""
        if not page_ids:
            return [], []
        
        # Check if index exists first
        if not self.es.indices.exists(index='wikipedia_embeddings'):
            return [], page_ids
        
        # Process in chunks if we have many IDs
        chunk_size = 1000
        all_processed = set()
        
        for i in range(0, len(page_ids), chunk_size):
            chunk_ids = page_ids[i:i + chunk_size]
            
            query = {
                "size": chunk_size,
                "query": {
                    "terms": {
                        "page_id": chunk_ids
                    }
                },
                "_source": ["page_id", "embeddings_processed"]
            }
            
            try:
                response = self.es.search(index='wikipedia_embeddings', body=query)
                
                for hit in response['hits']['hits']:
                    source = hit['_source']
                    if source.get('embeddings_processed', False):
                        all_processed.add(source['page_id'])
                
            except Exception as e:
                print(f"  ⚠️ Error checking processed status: {str(e)[:100]}")
                pass
        
        new_ids = [pid for pid in page_ids if pid not in all_processed]
        return list(all_processed), new_ids
    
    def process_batch(self, articles: List[Dict], batch_size: int = 10) -> None:
        """Process articles in batches through the embedding pipeline."""
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
                    '_index': 'wikipedia_embeddings',
                    '_id': article['page_id'],
                    '_source': article,
                    'pipeline': 'wikipedia_embedding_pipeline'
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
                self.stats['total_embeddings_created'] += success * 3  # 3 embeddings per doc
                
                if errors:
                    self.stats['failed'] += len(errors)
                    for error in errors[:3]:  # Show first 3 errors
                        print(f"  ⚠️ Error: {error}")
                
                print(f"  ✅ Processed: {success}/{len(batch)} articles")
                print(f"  🔢 Generated: {success * 3} embeddings (title, content, summary)")
                
                # Show sample similarity for verification
                if success > 0:
                    self._verify_embeddings(batch[0]['page_id'])
                
            except Exception as e:
                self.stats['failed'] += len(batch)
                print(f"  ❌ Batch failed: {str(e)[:100]}")
            
            # Small delay between batches
            if batch_num < total_batches - 1:
                time.sleep(0.5)
    
    def _verify_embeddings(self, page_id: str) -> None:
        """Verify embeddings were generated and show sample similarity."""
        try:
            doc = self.es.get(index='wikipedia_embeddings', id=page_id)
            source = doc['_source']
            
            if source.get('embeddings_processed'):
                # Check if embeddings exist
                has_title = 'title_embedding' in source and len(source['title_embedding']) == EMBEDDING_DIM
                has_content = 'content_embedding' in source and len(source['content_embedding']) == EMBEDDING_DIM
                has_summary = 'summary_embedding' in source and len(source['summary_embedding']) == EMBEDDING_DIM
                
                if has_title and has_content:
                    # Calculate similarity between title and content embeddings
                    title_vec = np.array(source['title_embedding'])
                    content_vec = np.array(source['content_embedding'])
                    
                    # Cosine similarity
                    similarity = np.dot(title_vec, content_vec) / (np.linalg.norm(title_vec) * np.linalg.norm(content_vec))
                    
                    print(f"  📊 Sample: '{source['title'][:40]}...'")
                    print(f"     Title↔Content similarity: {similarity:.3f}")
                    print(f"     Embeddings: Title✓ Content✓ Summary{'✓' if has_summary else '✗'}")
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
        
        # Double-check for already processed articles
        if skip_existing:
            page_ids = [a['page_id'] for a in articles]
            processed_ids, new_ids = self.check_already_processed(page_ids)
            
            if processed_ids:
                print(f"⏭️  Found {len(processed_ids)} recently processed articles, skipping...")
                self.stats['skipped'] = len(processed_ids)
                
                # Filter to only new articles
                articles = [a for a in articles if a['page_id'] in new_ids]
                
                if not articles:
                    print("✅ All articles already have embeddings!")
                    return self.stats
        
        print(f"\n🔄 Generating embeddings for {len(articles)} articles...")
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
        print(f"  🔢 Embeddings created: {self.stats['total_embeddings_created']:,}")
        
        if self.stats['start_time'] and self.stats['end_time']:
            duration = self.stats['end_time'] - self.stats['start_time']
            print(f"  ⏱️  Duration: {duration.total_seconds():.1f} seconds")
            
            if self.stats['successful'] > 0:
                rate = self.stats['successful'] / duration.total_seconds()
                print(f"  📈 Processing rate: {rate:.1f} articles/second")
                emb_rate = self.stats['total_embeddings_created'] / duration.total_seconds()
                print(f"  🚀 Embedding rate: {emb_rate:.1f} vectors/second")
        
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
    """Verify embedding model and pipeline are set up."""
    # Check model
    try:
        response = es.ml.get_trained_models_stats(
            model_id="sentence-transformers__all-minilm-l6-v2"
        )
        
        if response['trained_model_stats']:
            stats = response['trained_model_stats'][0]
            state = stats.get('deployment_stats', {}).get('state', 'not_deployed')
            
            if state != 'started':
                print(f"⚠️  Model state is '{state}'. Please run ./inference/install_embedding_model.sh")
                return False
        else:
            print("❌ Embedding model not found! Please run ./inference/install_embedding_model.sh")
            return False
    except:
        print("❌ Cannot check model status. Please run ./inference/install_embedding_model.sh")
        return False
    
    # Check pipeline
    try:
        es.ingest.get_pipeline(id='wikipedia_embedding_pipeline')
    except:
        print("❌ Embedding pipeline not found! Please run: python inference/setup_embedding_pipeline.py")
        return False
    
    # Check index
    if not es.indices.exists(index='wikipedia_embeddings'):
        print("❌ Embeddings index not found! Please run: python inference/setup_embedding_pipeline.py")
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(
        description='Generate text embeddings for Wikipedia articles',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process 10 random articles (default)
  python process_wikipedia_embeddings.py
  
  # Process 100 articles
  python process_wikipedia_embeddings.py --sample 100
  
  # Process ALL articles (warning: this may take a while)
  python process_wikipedia_embeddings.py --sample all
  
  # Process from specific index
  python process_wikipedia_embeddings.py --source wiki_summaries --sample 50
  
  # Force regenerate embeddings for existing articles
  python process_wikipedia_embeddings.py --sample 20 --force
  
  # Adjust batch size for performance
  python process_wikipedia_embeddings.py --sample 1000 --batch-size 25
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
        help='Force regenerate embeddings for articles that already have them'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Batch size for bulk processing (default: 10)'
    )
    
    args = parser.parse_args()
    
    print("🚀 Wikipedia Embedding Generation for Semantic Search")
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
        print("  1. Run: ./inference/install_embedding_model.sh")
        print("  2. Run: python inference/setup_embedding_pipeline.py")
        return 1
    
    print("✅ Embedding model and pipeline verified")
    
    # Create processor and run
    processor = WikipediaEmbeddingProcessor(es)
    
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
    count = es.count(index='wikipedia_embeddings')['count']
    print(f"  📚 Total documents in wikipedia_embeddings: {count:,}")
    
    # Count documents with embeddings
    processed = es.count(
        index='wikipedia_embeddings',
        body={"query": {"term": {"embeddings_processed": True}}}
    )['count']
    print(f"  🔢 Documents with embeddings: {processed:,}")
    print(f"  📊 Total vectors in index: {processed * 3:,}")
    
    print("\n✨ Processing complete!")
    print("Run 'python inference/search_embeddings.py' to test semantic search")
    
    return 0

if __name__ == "__main__":
    exit(main())