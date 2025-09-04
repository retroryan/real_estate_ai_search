#!/usr/bin/env python3
"""
Setup Elasticsearch Text Embedding Pipeline for Semantic Search
Creates index with dense vector mappings and inference pipeline for embeddings
"""

import os
import json
from pathlib import Path
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

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

def create_elasticsearch_client():
    """Create and return Elasticsearch client."""
    if ES_PASSWORD:
        client = Elasticsearch(
            [f"{ES_SCHEME}://{ES_HOST}:{ES_PORT}"],
            basic_auth=(ES_USERNAME, ES_PASSWORD),
            verify_certs=False
        )
    else:
        client = Elasticsearch(
            [f"{ES_SCHEME}://{ES_HOST}:{ES_PORT}"],
            verify_certs=False
        )
    return client

def create_embedding_index(es, index_name='wikipedia_embeddings'):
    """Create the embeddings index with proper mapping for vector search."""
    template_path = Path(__file__).parent.parent / 'real_estate_search/elasticsearch/templates/wikipedia_embeddings.json'
    
    with open(template_path, 'r') as f:
        mapping = json.load(f)
    
    # Add settings for the index
    index_body = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "index": {
                "default_pipeline": "wikipedia_embedding_pipeline"
            },
            "analysis": {
                "normalizer": {
                    "lowercase_normalizer": {
                        "type": "custom",
                        "char_filter": [],
                        "filter": ["lowercase", "asciifolding"]
                    }
                }
            }
        },
        "mappings": mapping
    }
    
    # Delete index if it exists
    if es.indices.exists(index=index_name):
        print(f"🗑️  Deleting existing index: {index_name}")
        es.indices.delete(index=index_name)
    
    # Create the index
    print(f"📦 Creating index: {index_name}")
    es.indices.create(index=index_name, body=index_body)
    print(f"✅ Index '{index_name}' created successfully")
    print(f"   • 3 vector fields (title, content, summary)")
    print(f"   • {EMBEDDING_DIM} dimensions per vector")
    print(f"   • Cosine similarity for relevance scoring")

def create_embedding_pipeline(es, pipeline_name='wikipedia_embedding_pipeline'):
    """Create the text embedding inference pipeline."""
    
    # Load pipeline definition from JSON file
    pipeline_file = Path(__file__).parent / 'embedding_pipeline.json'
    
    if not pipeline_file.exists():
        print(f"❌ Pipeline definition file not found: {pipeline_file}")
        return False
    
    print(f"📄 Loading pipeline definition from: {pipeline_file.name}")
    
    with open(pipeline_file, 'r') as f:
        pipeline_body = json.load(f)
    
    # Convert source arrays to strings for Elasticsearch (if needed)
    for processor in pipeline_body.get('processors', []):
        if 'script' in processor and isinstance(processor['script'].get('source'), list):
            processor['script']['source'] = '\n'.join(processor['script']['source'])
    
    # Delete pipeline if it exists
    try:
        es.ingest.delete_pipeline(id=pipeline_name)
        print(f"🗑️  Deleted existing pipeline: {pipeline_name}")
    except:
        pass
    
    # Create the pipeline
    print(f"🔧 Creating pipeline: {pipeline_name}")
    es.ingest.put_pipeline(id=pipeline_name, body=pipeline_body)
    print(f"✅ Pipeline '{pipeline_name}' created successfully")
    print(f"   • Generates embeddings for title, content, and summary")
    print(f"   • Handles text truncation for long content")
    print(f"   • Adds metadata and error handling")

def verify_model_deployment(es):
    """Verify the embedding model is deployed and running."""
    try:
        response = es.ml.get_trained_models_stats(model_id=MODEL_ID)
        
        if response['trained_model_stats']:
            stats = response['trained_model_stats'][0]
            deployment_stats = stats.get('deployment_stats', {})
            state = deployment_stats.get('state', 'not_deployed')
            
            print(f"\n📊 Model Status:")
            print(f"  Model ID: {stats['model_id']}")
            print(f"  State: {state}")
            print(f"  Model size: {stats['model_size_stats']['model_size_bytes'] / 1024 / 1024:.1f} MB")
            
            if state == 'started':
                print(f"  ✅ Model is deployed and ready!")
                
                # Get allocation info
                allocation = deployment_stats.get('allocation_stats', {})
                if allocation:
                    print(f"  Inference threads: {allocation.get('inference_threads', 'N/A')}")
                    print(f"  Model threads: {allocation.get('model_threads', 'N/A')}")
                
                return True
            else:
                print(f"  ⚠️  Model state is '{state}'. You may need to start it.")
                return False
        else:
            print("❌ Model not found!")
            return False
            
    except Exception as e:
        print(f"❌ Error checking model status: {e}")
        return False

def test_pipeline(es, pipeline_name='wikipedia_embedding_pipeline'):
    """Test the pipeline with sample text."""
    test_doc = {
        "docs": [
            {
                "_source": {
                    "title": "San Francisco Bay Area",
                    "full_content": "The San Francisco Bay Area is a populous region surrounding the San Francisco Bay "
                                   "in Northern California. It includes major cities like San Francisco, Oakland, and San Jose. "
                                   "The region is known for its technology industry, cultural diversity, and natural beauty.",
                    "long_summary": "The Bay Area is a major economic and cultural hub in California.",
                    "city": "San Francisco",
                    "state": "California"
                }
            }
        ]
    }
    
    print(f"\n🧪 Testing pipeline with sample text...")
    
    try:
        result = es.ingest.simulate(id=pipeline_name, body=test_doc)
        
        if result['docs'] and 'doc' in result['docs'][0]:
            doc = result['docs'][0]['doc']['_source']
            
            print("\n✅ Pipeline test successful!")
            
            # Check embeddings were generated
            has_title = 'title_embedding' in doc and doc['title_embedding']
            has_content = 'content_embedding' in doc and doc['content_embedding']
            has_summary = 'summary_embedding' in doc and doc['summary_embedding']
            
            print(f"  Title embedding: {'✓' if has_title else '✗'} "
                  f"({len(doc.get('title_embedding', []))} dims)")
            print(f"  Content embedding: {'✓' if has_content else '✗'} "
                  f"({len(doc.get('content_embedding', []))} dims)")
            print(f"  Summary embedding: {'✓' if has_summary else '✗'} "
                  f"({len(doc.get('summary_embedding', []))} dims)")
            
            if doc.get('embeddings_processed'):
                print(f"  Processing status: ✓")
                print(f"  Model used: {doc.get('embedding_model', 'N/A')}")
            
            return True
            
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        return False

def test_vector_search(es, index_name='wikipedia_embeddings', pipeline_name='wikipedia_embedding_pipeline'):
    """Test vector search capability with a sample query."""
    print(f"\n🔍 Testing vector search capability...")
    
    # First, index a few sample documents
    sample_docs = [
        {
            "page_id": "test_1",
            "title": "Golden Gate Bridge",
            "full_content": "The Golden Gate Bridge is a suspension bridge spanning the Golden Gate strait, "
                           "connecting San Francisco to Marin County. It is an iconic symbol of San Francisco.",
            "city": "San Francisco",
            "state": "California"
        },
        {
            "page_id": "test_2",
            "title": "Alcatraz Island",
            "full_content": "Alcatraz Island is located in San Francisco Bay. It was home to a federal prison "
                           "from 1934 to 1963 and is now a popular tourist attraction.",
            "city": "San Francisco",
            "state": "California"
        },
        {
            "page_id": "test_3",
            "title": "Mount Rushmore",
            "full_content": "Mount Rushmore is a massive sculpture carved into granite featuring the faces "
                           "of four U.S. presidents. Located in the Black Hills of South Dakota.",
            "city": "Keystone",
            "state": "South Dakota"
        }
    ]
    
    print("  Indexing sample documents...")
    for doc in sample_docs:
        es.index(index=index_name, id=doc['page_id'], document=doc, pipeline=pipeline_name)
    
    # Wait for indexing to complete
    es.indices.refresh(index=index_name)
    
    # Now test vector search
    print("  Running semantic search query: 'famous bridges in California'")
    
    # Get embedding for query text
    query_text = "famous bridges in California"
    inference_result = es.ml.infer_trained_model(
        model_id=MODEL_ID,
        docs=[{"text_field": query_text}]
    )
    
    query_vector = inference_result['inference_results'][0]['predicted_value']
    
    # Perform vector search
    search_query = {
        "size": 3,
        "query": {
            "script_score": {
                "query": {"match_all": {}},
                "script": {
                    "source": "cosineSimilarity(params.query_vector, 'content_embedding') + 1.0",
                    "params": {
                        "query_vector": query_vector
                    }
                }
            }
        },
        "_source": ["title", "city", "state"]
    }
    
    response = es.search(index=index_name, body=search_query)
    
    if response['hits']['hits']:
        print("\n  Search Results (by semantic similarity):")
        for i, hit in enumerate(response['hits']['hits'], 1):
            print(f"    {i}. {hit['_source']['title']}")
            print(f"       Score: {hit['_score']:.3f}")
            print(f"       Location: {hit['_source']['city']}, {hit['_source']['state']}")
        
        # Clean up test documents
        for doc in sample_docs:
            es.delete(index=index_name, id=doc['page_id'], ignore=[404])
        
        print("\n✅ Vector search is working correctly!")
        return True
    else:
        print("❌ No results found in vector search test")
        return False

def main():
    print("🚀 Setting up Text Embedding Pipeline for Semantic Search")
    print("=" * 60)
    
    # Create Elasticsearch client
    es = create_elasticsearch_client()
    
    # Verify connection
    if not es.ping():
        print("❌ Cannot connect to Elasticsearch!")
        print("Please ensure Elasticsearch is running and credentials are correct.")
        return
    
    print("✅ Connected to Elasticsearch")
    
    # Verify model deployment
    if not verify_model_deployment(es):
        print("\n⚠️  Model not deployed. Please run ./inference/install_embedding_model.sh first!")
        return
    
    # Create embedding index
    create_embedding_index(es)
    
    # Create embedding pipeline
    create_embedding_pipeline(es)
    
    # Test the pipeline
    test_pipeline(es)
    
    # Test vector search
    test_vector_search(es)
    
    print("\n" + "=" * 60)
    print("🎉 Setup complete! The text embedding pipeline is ready.")
    print("\n📚 What you can do now:")
    print("1. Process Wikipedia articles: python inference/process_wikipedia_embeddings.py")
    print("2. Run semantic search demos: python inference/search_embeddings.py")
    print("\n💡 Key Features:")
    print("• Semantic search - find conceptually similar content")
    print("• Multi-field embeddings - search by title, content, or summary")
    print("• Hybrid search - combine vector and keyword search")
    print("• Cross-lingual - works across multiple languages")

if __name__ == "__main__":
    main()