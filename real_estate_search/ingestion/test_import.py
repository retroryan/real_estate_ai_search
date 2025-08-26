#!/usr/bin/env python
"""
Quick test to verify all imports work correctly.
Run: python real_estate_search/ingestion/test_import.py
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_imports():
    """Test that all required imports work."""
    print("Testing imports...")
    
    try:
        # Test wiki_embed imports
        from wiki_embed.models import Config
        print("✓ wiki_embed.models imported")
        
        from wiki_embed.pipeline import WikipediaEmbeddingPipeline
        print("✓ wiki_embed.pipeline imported")
        
        from wiki_embed.embedding import create_embedding_model
        print("✓ wiki_embed.embedding imported")
        
        from wiki_embed.elasticsearch import ElasticsearchStore
        print("✓ wiki_embed.archive_elasticsearch imported")
        
        from wiki_embed.utils import load_summaries_from_db, configure_from_config
        print("✓ wiki_embed.utils imported")
        
        # Test real_estate_search imports
        from real_estate_search.indexer import PropertyIndexer
        print("✓ real_estate_search.indexer imported")
        
        from real_estate_search.config.settings import Settings
        print("✓ real_estate_search.config imported")
        
        # Test LlamaIndex imports
        from llama_index.core import Document
        print("✓ llama_index.core imported")
        
        from llama_index.core.node_parser import SimpleNodeParser
        print("✓ llama_index.core.node_parser imported")
        
        # Test local imports
        from real_estate_search.ingestion import IngestionOrchestrator
        print("✓ IngestionOrchestrator imported")
        
        print("\n✅ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import failed: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)