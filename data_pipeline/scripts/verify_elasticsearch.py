#!/usr/bin/env python3
"""
Elasticsearch Data Verification Script

This script verifies that Elasticsearch has received data from the pipeline
by checking cluster health, indices, and document counts.
"""

import requests
import json
import os
import sys
from typing import Dict, List, Optional
from requests.auth import HTTPBasicAuth

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If dotenv not available, user needs to source .env manually
    pass


def get_es_connection_info() -> tuple:
    """Get Elasticsearch connection details from environment variables."""
    es_host = os.environ.get('ES_HOST', 'localhost')
    es_port = os.environ.get('ES_PORT', '9200')
    es_username = os.environ.get('ES_USERNAME', 'elastic')
    es_password = os.environ.get('ES_PASSWORD', '')
    
    base_url = f'http://{es_host}:{es_port}'
    auth = HTTPBasicAuth(es_username, es_password) if es_password else None
    
    return base_url, auth


def check_cluster_health(base_url: str, auth: Optional[HTTPBasicAuth]) -> Dict:
    """Check Elasticsearch cluster health."""
    try:
        response = requests.get(f'{base_url}/_cluster/health', auth=auth, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to check cluster health: {e}")


def get_indices(base_url: str, auth: Optional[HTTPBasicAuth]) -> List[Dict]:
    """Get list of all indices with their statistics."""
    try:
        response = requests.get(f'{base_url}/_cat/indices?format=json', auth=auth)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get indices: {e}")


def get_sample_documents(base_url: str, auth: Optional[HTTPBasicAuth], 
                        index_name: str, size: int = 3) -> List[Dict]:
    """Get sample documents from an index."""
    try:
        query = {
            "query": {"match_all": {}},
            "size": size
        }
        response = requests.post(
            f'{base_url}/{index_name}/_search',
            auth=auth,
            headers={'Content-Type': 'application/json'},
            json=query
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get('hits', {}).get('hits', [])
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Could not get sample documents from {index_name}: {e}")
        return []


def print_cluster_info(health: Dict):
    """Print cluster health information."""
    status_emoji = {'green': '🟢', 'yellow': '🟡', 'red': '🔴'}.get(health['status'], '❓')
    
    print(f'{status_emoji} Cluster Status: {health["status"]}')
    print(f'📊 Active Shards: {health["active_shards"]}')
    print(f'🏃 Active Nodes: {health["number_of_nodes"]}')
    print(f'💾 Data Nodes: {health["number_of_data_nodes"]}')


def print_indices_info(indices: List[Dict]):
    """Print information about real estate indices."""
    # Filter for real estate indices
    real_estate_indices = [idx for idx in indices if 'real_estate' in idx.get('index', '')]
    
    print(f'\n📋 Found {len(real_estate_indices)} Real Estate Indices:')
    print('-' * 60)
    
    total_docs = 0
    
    for idx in real_estate_indices:
        index_name = idx['index']
        doc_count = idx.get('docs.count', 'N/A')
        store_size = idx.get('store.size', 'N/A')
        status = idx.get('status', 'unknown')
        
        # Try to convert doc_count to int for totaling
        try:
            total_docs += int(doc_count) if doc_count != 'N/A' else 0
        except (ValueError, TypeError):
            pass
        
        status_emoji = '✅' if status == 'open' else '❌'
        print(f'{status_emoji} {index_name}')
        print(f'   📄 Documents: {doc_count}')
        print(f'   💾 Size: {store_size}')
        print(f'   🏷️  Status: {status}')
        print()
    
    if real_estate_indices:
        print(f'📊 Total Documents: {total_docs:,}')
    else:
        print('❌ No real estate indices found!')
        return False
    
    return True


def print_test_indices(indices: List[Dict]):
    """Print information about test indices."""
    test_indices = [idx for idx in indices if 'test' in idx.get('index', '')]
    
    if test_indices:
        print(f'\n🧪 Found {len(test_indices)} Test Indices:')
        print('-' * 40)
        for idx in test_indices:
            doc_count = idx.get('docs.count', 'N/A')
            print(f'   • {idx["index"]} ({doc_count} docs)')


def show_sample_documents(base_url: str, auth: Optional[HTTPBasicAuth], indices: List[Dict]):
    """Show sample documents from each index."""
    real_estate_indices = [idx for idx in indices if 'real_estate' in idx.get('index', '')]
    
    if not real_estate_indices:
        return
    
    print(f'\n📄 Sample Documents:')
    print('=' * 60)
    
    for idx in real_estate_indices[:3]:  # Limit to first 3 indices
        index_name = idx['index']
        doc_count = idx.get('docs.count', '0')
        
        if doc_count == '0' or doc_count == 'N/A':
            continue
            
        print(f'\n📝 {index_name} (showing max 2 documents):')
        print('-' * 40)
        
        samples = get_sample_documents(base_url, auth, index_name, size=2)
        
        for i, doc in enumerate(samples, 1):
            source = doc.get('_source', {})
            doc_id = doc.get('_id', 'N/A')
            
            print(f'   Document {i} (ID: {doc_id}):')
            
            # Show key fields based on index type
            if 'properties' in index_name:
                fields = ['listing_id', 'listing_price', 'street', 'city', 'bedrooms']
            elif 'neighborhoods' in index_name:
                fields = ['neighborhood_id', 'name', 'median_income']  
            elif 'wikipedia' in index_name:
                fields = ['page_id', 'title', 'short_summary']
            else:
                fields = list(source.keys())[:5]  # First 5 fields
            
            for field in fields:
                if field in source:
                    value = str(source[field])[:100]  # Truncate long values
                    print(f'     {field}: {value}')
            print()


def main():
    """Main verification function."""
    print('🔍 Elasticsearch Data Verification')
    print('=' * 50)
    
    try:
        # Get connection info
        base_url, auth = get_es_connection_info()
        print(f'📍 Connecting to: {base_url}')
        
        # Debug mode - show what credentials we're using
        if '--debug' in sys.argv:
            username = os.environ.get('ES_USERNAME', 'elastic')
            password_set = bool(os.environ.get('ES_PASSWORD'))
            print(f'🔐 Username: {username}')
            print(f'🔑 Password: {"✅ Set" if password_set else "❌ Not set"}')
        
        # Check cluster health
        health = check_cluster_health(base_url, auth)
        print_cluster_info(health)
        
        # Get indices
        indices = get_indices(base_url, auth)
        
        # Print main indices info
        has_data = print_indices_info(indices)
        
        # Print test indices
        print_test_indices(indices)
        
        # Show sample documents if we have data
        if has_data and '--samples' in sys.argv:
            show_sample_documents(base_url, auth, indices)
        elif has_data:
            print('\n💡 Add --samples flag to see sample documents')
        
        print('\n✅ Verification complete!')
        
        if not has_data:
            print('\n⚠️  No data found in Elasticsearch.')
            print('   Make sure you have run the pipeline to load data.')
            sys.exit(1)
            
    except Exception as e:
        print(f'\n❌ Verification failed: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()