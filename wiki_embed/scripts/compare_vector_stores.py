#!/usr/bin/env python3
"""
Vector store comparison script.
Compares search results and performance between ChromaDB and Elasticsearch.
"""

import json
import sys
import time
import statistics
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path to import wiki_embed modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from wiki_embed.models import Config, LocationQuery, QueryType, EmbeddingMethod
from wiki_embed.utils import configure_from_config
from wiki_embed.query import WikipediaQueryTester


def create_config(provider: str) -> str:
    """Create temporary config for the specified provider."""
    config_path = f"temp_config_{provider}.yaml"
    
    if provider == "chromadb":
        config_content = """
embedding:
  provider: ollama
  ollama_base_url: "http://localhost:11434"
  ollama_model: "nomic-embed-text"

vector_store:
  provider: chromadb
  chromadb:
    path: "./data/wiki_chroma_db"
    collection_prefix: "wiki_embeddings"

data:
  source_dir: "../../data/wikipedia/pages"
  registry_path: "../../data/wikipedia/REGISTRY.json"
  attribution_path: "../../data/wikipedia/attribution/WIKIPEDIA_ATTRIBUTION.json"
  wikipedia_db: "../../data/wikipedia/wikipedia.db"

chunking:
  method: semantic
  embedding_method: traditional

testing:
  queries_path: "../../data/wiki_test_queries.json"
  top_k: 5
  min_similarity: 0.3
"""
    else:  # elasticsearch
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

chunking:
  method: semantic
  embedding_method: traditional

testing:
  queries_path: "../../data/wiki_test_queries.json"
  top_k: 5
  min_similarity: 0.3
"""
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    return config_path


def load_test_queries() -> List[LocationQuery]:
    """Load test queries from file or create sample queries."""
    
    # Try to load from file first
    queries_file = Path("../../data/wiki_test_queries.json")
    
    if queries_file.exists():
        print(f"📖 Loading queries from {queries_file}")
        with open(queries_file) as f:
            data = json.load(f)
        
        test_queries = []
        for q in data["queries"]:
            query_type = QueryType(q["query_type"]) if "query_type" in q else QueryType.GEOGRAPHIC
            test_queries.append(LocationQuery(
                query=q["query"],
                expected_articles=q["expected_articles"],
                location_context=q.get("location_context"),
                query_type=query_type,
                description=q.get("description")
            ))
        
        return test_queries[:10]  # Limit to first 10 for comparison
    
    else:
        print("📝 Creating sample test queries")
        # Create sample queries for testing
        return [
            LocationQuery(
                query="ski resorts and winter recreation",
                expected_articles=["any"],
                location_context="Utah",
                query_type=QueryType.RECREATIONAL,
                description="Winter sports facilities"
            ),
            LocationQuery(
                query="downtown historic district",
                expected_articles=["any"], 
                location_context="Park City",
                query_type=QueryType.HISTORICAL,
                description="Historic downtown area"
            ),
            LocationQuery(
                query="mountain hiking trails",
                expected_articles=["any"],
                location_context="Utah",
                query_type=QueryType.RECREATIONAL,
                description="Hiking and outdoor recreation"
            ),
            LocationQuery(
                query="local museums and cultural sites",
                expected_articles=["any"],
                location_context="Park City",
                query_type=QueryType.CULTURAL,
                description="Museums and cultural attractions"
            ),
            LocationQuery(
                query="city government and administration",
                expected_articles=["any"],
                location_context="Park City",
                query_type=QueryType.ADMINISTRATIVE,
                description="City government information"
            )
        ]


def test_vector_store(provider: str, queries: List[LocationQuery]) -> Dict[str, Any]:
    """Test a specific vector store with the given queries."""
    print(f"\n🔍 Testing {provider.upper()} vector store...")
    
    # Create config and initialize
    config_path = create_config(provider)
    
    try:
        config = Config.from_yaml(config_path)
        configure_from_config(config)
        
        # Create query tester
        tester = WikipediaQueryTester(config, method=EmbeddingMethod.TRADITIONAL)
        print(f"✅ {provider} tester initialized")
        
        results = []
        query_times = []
        
        for i, query in enumerate(queries, 1):
            print(f"  Query {i}/{len(queries)}: {query.query[:50]}...")
            
            try:
                # Time the query
                start_time = time.time()
                
                # Get embedding and search
                query_embedding = tester.embed_model.get_text_embedding(query.query)
                search_results = tester.vector_searcher.similarity_search(query_embedding, 5)
                
                query_time = time.time() - start_time
                query_times.append(query_time)
                
                # Extract page IDs and scores
                page_ids = []
                scores = []
                
                if search_results and 'metadatas' in search_results:
                    for metadata_list in search_results['metadatas']:
                        for metadata in metadata_list:
                            if 'page_id' in metadata:
                                page_ids.append(metadata['page_id'])
                
                if search_results and 'distances' in search_results:
                    scores = search_results['distances'][0] if search_results['distances'] else []
                
                results.append({
                    'query': query.query,
                    'page_ids': page_ids,
                    'scores': scores,
                    'query_time': query_time,
                    'num_results': len(page_ids)
                })
                
                print(f"    ✅ {len(page_ids)} results in {query_time:.3f}s")
                
            except Exception as e:
                print(f"    ❌ Error: {e}")
                results.append({
                    'query': query.query,
                    'page_ids': [],
                    'scores': [],
                    'query_time': 0,
                    'num_results': 0,
                    'error': str(e)
                })
        
        # Calculate statistics
        successful_queries = [r for r in results if 'error' not in r]
        avg_query_time = statistics.mean(query_times) if query_times else 0
        total_results = sum(r['num_results'] for r in successful_queries)
        
        return {
            'provider': provider,
            'total_queries': len(queries),
            'successful_queries': len(successful_queries),
            'failed_queries': len(queries) - len(successful_queries),
            'avg_query_time': avg_query_time,
            'total_results': total_results,
            'results': results
        }
        
    except Exception as e:
        print(f"❌ {provider} testing failed: {e}")
        return {
            'provider': provider,
            'error': str(e),
            'results': []
        }
    
    finally:
        # Clean up config file
        if Path(config_path).exists():
            Path(config_path).unlink()


def compare_results(chromadb_results: Dict, elasticsearch_results: Dict, queries: List[LocationQuery]):
    """Compare results between the two vector stores."""
    print("\n⚖️  Comparing Results Between Vector Stores")
    print("=" * 60)
    
    if 'error' in chromadb_results or 'error' in elasticsearch_results:
        print("❌ Cannot compare - one or both vector stores failed")
        return
    
    # Overall statistics
    print("📊 Overall Performance:")
    print(f"   ChromaDB queries: {chromadb_results['successful_queries']}/{chromadb_results['total_queries']}")
    print(f"   Elasticsearch queries: {elasticsearch_results['successful_queries']}/{elasticsearch_results['total_queries']}")
    print(f"   ChromaDB avg time: {chromadb_results['avg_query_time']:.3f}s")
    print(f"   Elasticsearch avg time: {elasticsearch_results['avg_query_time']:.3f}s")
    
    # Compare individual query results
    print("\n🔍 Query-by-Query Comparison:")
    
    mismatches = 0
    total_comparisons = 0
    
    for i, query in enumerate(queries):
        if i >= len(chromadb_results['results']) or i >= len(elasticsearch_results['results']):
            continue
            
        chroma_result = chromadb_results['results'][i]
        elastic_result = elasticsearch_results['results'][i]
        
        print(f"\n  Query {i+1}: {query.query[:60]}...")
        
        if 'error' in chroma_result or 'error' in elastic_result:
            print("    ❌ One or both queries failed")
            continue
        
        chroma_ids = set(chroma_result['page_ids'])
        elastic_ids = set(elastic_result['page_ids'])
        
        # Calculate overlap
        overlap = len(chroma_ids & elastic_ids)
        union = len(chroma_ids | elastic_ids)
        jaccard = overlap / union if union > 0 else 0
        
        print(f"    ChromaDB: {len(chroma_ids)} results")
        print(f"    Elasticsearch: {len(elastic_ids)} results")
        print(f"    Overlap: {overlap} results")
        print(f"    Jaccard similarity: {jaccard:.3f}")
        
        # Time comparison
        time_diff = abs(chroma_result['query_time'] - elastic_result['query_time'])
        faster = "ChromaDB" if chroma_result['query_time'] < elastic_result['query_time'] else "Elasticsearch"
        print(f"    Faster: {faster} (Δ {time_diff:.3f}s)")
        
        if jaccard < 0.5:  # Less than 50% overlap
            mismatches += 1
        
        total_comparisons += 1
    
    # Summary
    print(f"\n📈 Comparison Summary:")
    print(f"   Total comparisons: {total_comparisons}")
    print(f"   High similarity (>50% overlap): {total_comparisons - mismatches}")
    print(f"   Low similarity (<50% overlap): {mismatches}")
    
    if total_comparisons > 0:
        similarity_rate = (total_comparisons - mismatches) / total_comparisons * 100
        print(f"   Overall similarity rate: {similarity_rate:.1f}%")
        
        if similarity_rate >= 80:
            print("   ✅ Vector stores show high consistency")
        elif similarity_rate >= 60:
            print("   ⚠️  Vector stores show moderate consistency")
        else:
            print("   ❌ Vector stores show low consistency - investigate differences")


def main():
    """Run vector store comparison."""
    print("⚖️  Vector Store Comparison Tool")
    print("=" * 60)
    
    # Load test queries
    queries = load_test_queries()
    print(f"📝 Loaded {len(queries)} test queries")
    
    # Test both vector stores
    print("\n🧪 Running Tests on Both Vector Stores")
    
    chromadb_results = test_vector_store("chromadb", queries)
    elasticsearch_results = test_vector_store("elasticsearch", queries)
    
    # Compare results
    compare_results(chromadb_results, elasticsearch_results, queries)
    
    # Save detailed results
    comparison_data = {
        'timestamp': time.time(),
        'queries': [q.dict() for q in queries],
        'chromadb_results': chromadb_results,
        'elasticsearch_results': elasticsearch_results
    }
    
    results_file = Path("vector_store_comparison.json")
    with open(results_file, 'w') as f:
        json.dump(comparison_data, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    
    # Final assessment
    if 'error' not in chromadb_results and 'error' not in elasticsearch_results:
        print("\n🎉 Comparison completed successfully!")
        print("✅ Both vector stores are functional")
        return 0
    else:
        print("\n❌ Some vector stores failed - check logs above")
        return 1


if __name__ == "__main__":
    sys.exit(main())