#!/usr/bin/env python3
"""
Full-scale embedding creation script for Elasticsearch.
Creates all Wikipedia embeddings and provides detailed progress monitoring.
"""

import json
import sys
import time
import psutil
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import wiki_embed modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wiki_embed.models import Config, EmbeddingMethod
from wiki_embed.utils import configure_from_config
from wiki_embed.pipeline import WikipediaEmbeddingPipeline


def check_system_resources():
    """Check available system resources."""
    print("💻 System Resources Check:")
    
    # Memory
    memory = psutil.virtual_memory()
    print(f"   RAM: {memory.available / (1024**3):.1f}GB available / {memory.total / (1024**3):.1f}GB total")
    
    # Disk space
    disk = psutil.disk_usage('/')
    print(f"   Disk: {disk.free / (1024**3):.1f}GB available / {disk.total / (1024**3):.1f}GB total")
    
    # CPU
    cpu_count = psutil.cpu_count()
    print(f"   CPU: {cpu_count} cores")
    
    return {
        'memory_available_gb': memory.available / (1024**3),
        'disk_available_gb': disk.free / (1024**3),
        'cpu_count': cpu_count
    }


def check_elasticsearch_health():
    """Check Elasticsearch cluster health and available space."""
    print("\n🔍 Elasticsearch Health Check:")
    
    try:
        from elasticsearch import Elasticsearch
        client = Elasticsearch(["http://localhost:9200"])
        
        # Cluster health
        health = client.cluster.health()
        print(f"   Status: {health['status']}")
        print(f"   Nodes: {health['number_of_nodes']}")
        
        # Cluster stats for storage info
        stats = client.cluster.stats()
        indices_size = stats['indices']['store']['size_in_bytes']
        print(f"   Current indices size: {indices_size / (1024**3):.2f}GB")
        
        return health['status'] in ['green', 'yellow']
        
    except Exception as e:
        print(f"   ❌ Elasticsearch health check failed: {e}")
        return False


def estimate_embedding_requirements():
    """Estimate storage and time requirements for full embedding creation."""
    print("\n📊 Estimating Requirements:")
    
    try:
        # Load a limited config to check article count
        config = Config.from_yaml("../config.yaml")
        
        from wiki_embed.utils import load_wikipedia_articles
        
        # Count total articles (without loading full content)
        print("   Counting Wikipedia articles...")
        articles = load_wikipedia_articles(
            config.data.source_dir,
            config.data.registry_path,
            max_articles=None
        )
        
        total_articles = len(articles)
        print(f"   Total articles: {total_articles}")
        
        # Estimate based on typical values
        avg_chunks_per_article = 8  # Conservative estimate
        embedding_size_bytes = 768 * 4  # 768 dimensions * 4 bytes per float
        metadata_overhead = 1024  # Estimated metadata size per chunk
        
        total_chunks = total_articles * avg_chunks_per_article
        storage_per_chunk = embedding_size_bytes + metadata_overhead
        total_storage_mb = (total_chunks * storage_per_chunk) / (1024**2)
        
        # Time estimates (based on ~2 seconds per chunk for embedding generation)
        estimated_time_minutes = (total_chunks * 2) / 60
        
        print(f"   Estimated chunks: {total_chunks:,}")
        print(f"   Estimated storage: {total_storage_mb:.1f}MB")
        print(f"   Estimated time: {estimated_time_minutes:.1f} minutes")
        
        return {
            'total_articles': total_articles,
            'estimated_chunks': total_chunks,
            'estimated_storage_mb': total_storage_mb,
            'estimated_time_minutes': estimated_time_minutes
        }
        
    except Exception as e:
        print(f"   ❌ Estimation failed: {e}")
        return None


def create_elasticsearch_config():
    """Create configuration for full Elasticsearch embedding creation."""
    config_path = Path("config_elasticsearch_full.yaml")
    
    config_content = """
embedding:
  provider: ollama
  ollama_base_url: "http://localhost:11434"
  ollama_model: "nomic-embed-text"

vector_store:
  provider: elasticsearch
  elasticsearch:
    host: "localhost"
    port: 9200
    index_prefix: "wiki_embeddings"

data:
  source_dir: "../../data/wikipedia/pages"
  registry_path: "../../data/wikipedia/REGISTRY.json"
  attribution_path: "../../data/wikipedia/attribution/WIKIPEDIA_ATTRIBUTION.json"
  wikipedia_db: "../../data/wikipedia/wikipedia.db"
  # max_articles: null  # Process all articles

chunking:
  method: semantic
  breakpoint_percentile: 90
  buffer_size: 2
  chunk_size: 800
  chunk_overlap: 100
  embedding_method: traditional

testing:
  queries_path: "../../data/wiki_test_queries.json"
  top_k: 5
  min_similarity: 0.3
"""
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    return str(config_path)


def monitor_progress(start_time, current_chunk, total_chunks):
    """Monitor and display progress statistics."""
    elapsed = time.time() - start_time
    
    if current_chunk > 0:
        rate = current_chunk / elapsed
        remaining_chunks = total_chunks - current_chunk
        eta_seconds = remaining_chunks / rate if rate > 0 else 0
        
        print(f"   Progress: {current_chunk:,}/{total_chunks:,} chunks ({current_chunk/total_chunks*100:.1f}%)")
        print(f"   Rate: {rate:.1f} chunks/second")
        print(f"   Elapsed: {elapsed/60:.1f} minutes")
        print(f"   ETA: {eta_seconds/60:.1f} minutes")
        
        # Memory usage
        memory = psutil.virtual_memory()
        print(f"   Memory: {memory.percent:.1f}% used")


def create_full_embeddings():
    """Create full-scale embeddings with progress monitoring."""
    print("\n🚀 Starting Full-Scale Embedding Creation")
    print("=" * 60)
    
    # Create config
    config_path = create_elasticsearch_config()
    
    try:
        # Load config and configure global settings
        config = Config.from_yaml(config_path)
        configure_from_config(config)
        
        print("✅ Configuration loaded")
        print(f"   Provider: {config.embedding.provider}")
        print(f"   Vector Store: {config.vector_store.provider}")
        print(f"   Embedding Method: {config.chunking.embedding_method}")
        
        # Create pipeline
        pipeline = WikipediaEmbeddingPipeline(config)
        print("✅ Pipeline initialized")
        
        # Record start time and system state
        start_time = time.time()
        start_memory = psutil.virtual_memory().percent
        
        print(f"\n🕐 Starting embedding creation at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Initial memory usage: {start_memory:.1f}%")
        
        # Create embeddings
        count = pipeline.create_embeddings(
            force_recreate=True,  # Ensure clean creation
            method=EmbeddingMethod.TRADITIONAL
        )
        
        # Record completion
        end_time = time.time()
        total_time = end_time - start_time
        end_memory = psutil.virtual_memory().percent
        
        print("\n" + "=" * 60)
        print("✅ EMBEDDING CREATION COMPLETE!")
        print("=" * 60)
        print(f"📊 Final Statistics:")
        print(f"   Total embeddings: {count:,}")
        print(f"   Total time: {total_time/60:.1f} minutes")
        print(f"   Average rate: {count/total_time:.1f} embeddings/second")
        print(f"   Memory change: {start_memory:.1f}% → {end_memory:.1f}%")
        
        # Save statistics
        stats = {
            'completion_time': datetime.now().isoformat(),
            'total_embeddings': count,
            'total_time_seconds': total_time,
            'rate_per_second': count / total_time,
            'start_memory_percent': start_memory,
            'end_memory_percent': end_memory,
            'config_used': config.dict()
        }
        
        stats_file = Path("elasticsearch_embedding_stats.json")
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"📈 Statistics saved to: {stats_file}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Embedding creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up config file
        if Path(config_path).exists():
            Path(config_path).unlink()


def validate_embeddings():
    """Validate the created embeddings."""
    print("\n🔍 Validating Created Embeddings")
    print("=" * 40)
    
    try:
        from elasticsearch import Elasticsearch
        client = Elasticsearch(["http://localhost:9200"])
        
        # List all wiki embedding indices
        indices = client.cat.indices(index="wiki_embeddings*", format="json")
        
        if not indices:
            print("❌ No wiki embedding indices found")
            return False
        
        total_docs = 0
        for index in indices:
            index_name = index['index']
            doc_count = int(index['docs.count'])
            size = index['store.size']
            
            print(f"   📄 {index_name}: {doc_count:,} documents ({size})")
            total_docs += doc_count
        
        print(f"\n✅ Total embeddings: {total_docs:,}")
        
        # Test a simple search
        if indices:
            test_index = indices[0]['index']
            search_result = client.search(
                index=test_index,
                body={"query": {"match_all": {}}, "size": 1}
            )
            
            if search_result['hits']['total']['value'] > 0:
                print("✅ Search test successful")
                return True
            else:
                print("❌ Search test failed - no documents found")
                return False
    
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False


def main():
    """Main execution function."""
    print("🔧 Full-Scale Elasticsearch Embedding Creation")
    print("=" * 60)
    
    # Pre-flight checks
    print("🔍 Pre-flight Checks:")
    
    # System resources
    resources = check_system_resources()
    
    # Elasticsearch health
    if not check_elasticsearch_health():
        print("\n❌ Elasticsearch is not healthy. Please check your setup.")
        return 1
    
    # Estimate requirements
    estimates = estimate_embedding_requirements()
    if not estimates:
        return 1
    
    # Resource checks
    if resources['memory_available_gb'] < 2:
        print("\n⚠️  Warning: Low available memory (< 2GB)")
    
    if resources['disk_available_gb'] < estimates['estimated_storage_mb'] / 1024 + 1:
        print(f"\n⚠️  Warning: Might not have enough disk space")
    
    # Confirmation
    print(f"\n📋 Ready to create embeddings:")
    print(f"   Articles: ~{estimates['total_articles']:,}")
    print(f"   Estimated chunks: ~{estimates['estimated_chunks']:,}")
    print(f"   Estimated time: ~{estimates['estimated_time_minutes']:.0f} minutes")
    print(f"   Estimated storage: ~{estimates['estimated_storage_mb']:.0f}MB")
    
    response = input("\n❓ Continue with embedding creation? (y/N): ")
    if response.lower() != 'y':
        print("❌ Cancelled by user")
        return 0
    
    # Create embeddings
    success = create_full_embeddings()
    
    if success:
        # Validate results
        validate_embeddings()
        print("\n🎉 Full-scale embedding creation completed successfully!")
        return 0
    else:
        print("\n❌ Embedding creation failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())