#!/usr/bin/env python3
"""
Setup Elasticsearch NER inference ingest pipeline for Wikipedia articles
"""

import os
import json
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Elasticsearch configuration
ES_HOST = os.getenv('ES_HOST', 'localhost')
ES_PORT = int(os.getenv('ES_PORT', 9200))
ES_USERNAME = os.getenv('ES_USERNAME', 'elastic')
ES_PASSWORD = os.getenv('ES_PASSWORD')
ES_SCHEME = os.getenv('ES_SCHEME', 'http')

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

def create_ner_index(es, index_name='wikipedia_ner'):
    """Create the NER index with proper mapping."""
    template_path = Path('real_estate_search/elasticsearch/templates/wikipedia_ner.json')
    
    with open(template_path, 'r') as f:
        mapping = json.load(f)
    
    # Add settings for the index
    index_body = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
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
        print(f"Deleting existing index: {index_name}")
        es.indices.delete(index=index_name)
    
    # Create the index
    print(f"Creating index: {index_name}")
    es.indices.create(index=index_name, body=index_body)
    print(f"✅ Index '{index_name}' created successfully")

def create_ner_pipeline(es, pipeline_name='wikipedia_ner_pipeline'):
    """Create the NER inference ingest pipeline."""
    
    # Load pipeline definition from JSON file
    pipeline_file = Path(__file__).parent / 'ner_pipeline.json'
    
    if not pipeline_file.exists():
        print(f"❌ Pipeline definition file not found: {pipeline_file}")
        return False
    
    print(f"📄 Loading pipeline definition from: {pipeline_file}")
    
    with open(pipeline_file, 'r') as f:
        pipeline_body = json.load(f)
    
    # Delete pipeline if it exists
    try:
        es.ingest.delete_pipeline(id=pipeline_name)
        print(f"Deleted existing pipeline: {pipeline_name}")
    except:
        pass
    
    # Create the pipeline
    print(f"Creating pipeline: {pipeline_name}")
    es.ingest.put_pipeline(id=pipeline_name, body=pipeline_body)
    print(f"✅ Pipeline '{pipeline_name}' created successfully")

def verify_model_deployment(es):
    """Verify the NER model is deployed and running."""
    try:
        response = es.ml.get_trained_models_stats(
            model_id="elastic__distilbert-base-uncased-finetuned-conll03-english"
        )
        
        if response['trained_model_stats']:
            stats = response['trained_model_stats'][0]
            deployment_stats = stats.get('deployment_stats', {})
            state = deployment_stats.get('state', 'not_deployed')
            
            print(f"\n📊 Model Status:")
            print(f"  Model ID: {stats['model_id']}")
            print(f"  State: {state}")
            
            if state == 'started':
                print(f"  ✅ Model is deployed and ready!")
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

def test_pipeline(es, pipeline_name='wikipedia_ner_pipeline'):
    """Test the pipeline with sample text."""
    test_doc = {
        "docs": [
            {
                "_source": {
                    "full_content": "Elastic is headquartered in Mountain View, California. "
                                   "The company was founded by Shay Banon and has offices in Amsterdam."
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
            print(f"  Organizations found: {doc.get('ner_organizations', [])}")
            print(f"  Locations found: {doc.get('ner_locations', [])}")
            print(f"  Persons found: {doc.get('ner_persons', [])}")
            print(f"  Total entities: {len(doc.get('ner_entities', []))}")
            
            return True
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        return False

def main():
    print("🚀 Setting up NER Pipeline for Wikipedia Articles")
    print("=" * 50)
    
    # Create Elasticsearch client
    es = create_elasticsearch_client()
    
    # Verify connection
    if not es.ping():
        print("❌ Cannot connect to Elasticsearch!")
        return
    
    print("✅ Connected to Elasticsearch")
    
    # Verify model deployment
    if not verify_model_deployment(es):
        print("\n⚠️  Model not deployed. Please run ./install_ner_model.sh first!")
        return
    
    # Create NER index
    create_ner_index(es)
    
    # Create NER pipeline
    create_ner_pipeline(es)
    
    # Test the pipeline
    test_pipeline(es)
    
    print("\n" + "=" * 50)
    print("🎉 Setup complete! The NER pipeline is ready to use.")
    print("\nNext steps:")
    print("1. Run the test script to process Wikipedia articles")
    print("2. Use the pipeline with: PUT wikipedia_ner/_doc/1?pipeline=wikipedia_ner_pipeline")

if __name__ == "__main__":
    main()