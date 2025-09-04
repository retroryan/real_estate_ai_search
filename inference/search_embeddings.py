#!/usr/bin/env python3
"""
Semantic Search Demo using Text Embeddings
Demonstrates various vector search capabilities with Wikipedia articles
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
from tabulate import tabulate
import time

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

class EmbeddingSearchTester:
    def __init__(self, es_client):
        self.es = es_client
        self.test_results = []
    
    def get_query_embedding(self, query_text: str) -> List[float]:
        """Get embedding vector for query text."""
        try:
            result = self.es.ml.infer_trained_model(
                model_id=MODEL_ID,
                docs=[{"text_field": query_text}]
            )
            return result['inference_results'][0]['predicted_value']
        except Exception as e:
            print(f"❌ Error getting embedding: {e}")
            return None
    
    def run_vector_search(self, query: Dict, description: str, max_results: int = 5) -> Dict:
        """Execute a vector search query and return results."""
        print(f"\n🔍 {description}")
        print("-" * 60)
        
        try:
            response = self.es.search(index='wikipedia_embeddings', body=query)
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
                    
                    # Show location if available
                    if source.get('city') and source.get('state'):
                        print(f"   📍 Location: {source['city']}, {source['state']}")
                    
                    # Show categories if available
                    if source.get('categories'):
                        cats = source['categories'][:3]
                        print(f"   🏷️  Categories: {', '.join(cats)}")
                    
                    # Show snippet if available
                    if 'highlight' in hit:
                        for field, fragments in hit['highlight'].items():
                            if fragments:
                                print(f"   📝 Excerpt: ...{fragments[0][:120]}...")
                    
                    print()
            else:
                print("No results found")
            
            self.test_results.append(result)
            return result
            
        except Exception as e:
            print(f"❌ Search failed: {e}")
            return {'error': str(e)}
    
    def _explain_test(self, test_type: str, explanation: str) -> None:
        """Display explanation for what the test does."""
        print(f"\n💡 **{test_type}**: {explanation}")
        print()
    
    def test_semantic_searches(self) -> None:
        """Run a series of test searches demonstrating semantic search capabilities."""
        
        print("\n" + "=" * 70)
        print("🧪 TESTING SEMANTIC SEARCH CAPABILITIES")
        print("=" * 70)
        
        # Test 1: Pure Semantic Search
        query_text = "famous bridges in San Francisco"
        query_vector = self.get_query_embedding(query_text)
        
        if query_vector:
            semantic_query = {
                "size": 5,
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
                "_source": ["title", "city", "state", "categories"],
                "min_score": 1.0  # Filter out very low similarity scores
            }
            
            self.run_vector_search(semantic_query, f"Test 1: Semantic Search - '{query_text}'")
            self._explain_test(
                "Pure Semantic Search",
                "Uses cosine similarity between query embedding and content embeddings. "
                "Finds conceptually similar content even without exact keyword matches. "
                "Score = cosine_similarity + 1.0 (ranges from 0 to 2)."
            )
        
        # Test 2: KNN Search (k-nearest neighbors)
        query_text = "technology companies in California"
        query_vector = self.get_query_embedding(query_text)
        
        if query_vector:
            knn_query = {
                "size": 5,
                "knn": {
                    "field": "content_embedding",
                    "query_vector": query_vector,
                    "k": 10,
                    "num_candidates": 50
                },
                "_source": ["title", "city", "state", "categories"]
            }
            
            self.run_vector_search(knn_query, f"Test 2: KNN Search - '{query_text}'")
            self._explain_test(
                "K-Nearest Neighbors Search",
                "Efficient approximate nearest neighbor search using HNSW algorithm. "
                "Finds the k most similar documents based on vector distance. "
                "Faster than script_score for large datasets."
            )
        
        # Test 3: Hybrid Search (Vector + Keywords)
        query_text = "national parks"
        query_vector = self.get_query_embedding(query_text)
        
        if query_vector:
            hybrid_query = {
                "size": 5,
                "query": {
                    "bool": {
                        "should": [
                            {
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
                            {
                                "match": {
                                    "full_content": {
                                        "query": "national park",
                                        "boost": 2
                                    }
                                }
                            }
                        ]
                    }
                },
                "_source": ["title", "city", "state", "categories"],
                "highlight": {
                    "fields": {
                        "full_content": {
                            "fragment_size": 100,
                            "number_of_fragments": 1
                        }
                    }
                }
            }
            
            self.run_vector_search(hybrid_query, f"Test 3: Hybrid Search - '{query_text}' (vector + keywords)")
            self._explain_test(
                "Hybrid Search",
                "Combines semantic similarity with keyword matching for best of both worlds. "
                "Vector search captures semantic meaning while keyword search ensures precision. "
                "Particularly effective for domain-specific queries."
            )
        
        # Test 4: Multi-Field Vector Search
        query_text = "California history"
        query_vector = self.get_query_embedding(query_text)
        
        if query_vector:
            multifield_query = {
                "size": 5,
                "query": {
                    "bool": {
                        "should": [
                            {
                                "script_score": {
                                    "query": {"match_all": {}},
                                    "script": {
                                        "source": "cosineSimilarity(params.query_vector, 'title_embedding') + 1.0",
                                        "params": {
                                            "query_vector": query_vector
                                        }
                                    },
                                    "boost": 2
                                }
                            },
                            {
                                "script_score": {
                                    "query": {"match_all": {}},
                                    "script": {
                                        "source": "cosineSimilarity(params.query_vector, 'summary_embedding') + 1.0",
                                        "params": {
                                            "query_vector": query_vector
                                        }
                                    },
                                    "boost": 1.5
                                }
                            },
                            {
                                "script_score": {
                                    "query": {"match_all": {}},
                                    "script": {
                                        "source": "cosineSimilarity(params.query_vector, 'content_embedding') + 1.0",
                                        "params": {
                                            "query_vector": query_vector
                                        }
                                    }
                                }
                            }
                        ]
                    }
                },
                "_source": ["title", "city", "state", "categories"]
            }
            
            self.run_vector_search(multifield_query, f"Test 4: Multi-Field Vector Search - '{query_text}'")
            self._explain_test(
                "Multi-Field Vector Search",
                "Searches across multiple embedding fields (title, summary, content) with different weights. "
                "Title matches are boosted 2x, summary 1.5x. Captures relevance at different granularities."
            )
        
        # Test 5: Filtered Vector Search
        query_text = "landmarks and attractions"
        query_vector = self.get_query_embedding(query_text)
        
        if query_vector:
            filtered_query = {
                "size": 5,
                "query": {
                    "script_score": {
                        "query": {
                            "bool": {
                                "filter": [
                                    {"term": {"state": "California"}}
                                ]
                            }
                        },
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'content_embedding') + 1.0",
                            "params": {
                                "query_vector": query_vector
                            }
                        }
                    }
                },
                "_source": ["title", "city", "state", "categories"]
            }
            
            self.run_vector_search(filtered_query, f"Test 5: Filtered Vector Search - '{query_text}' in California")
            self._explain_test(
                "Filtered Vector Search",
                "Applies metadata filters before vector similarity calculation. "
                "Efficient for narrowing search scope by location, category, or other attributes. "
                "Reduces search space while maintaining semantic relevance."
            )
        
        # Test 6: Question-Answer Search
        query_text = "What is the tallest mountain in Utah?"
        query_vector = self.get_query_embedding(query_text)
        
        if query_vector:
            qa_query = {
                "size": 5,
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": """
                                double titleScore = cosineSimilarity(params.query_vector, 'title_embedding') + 1.0;
                                double contentScore = cosineSimilarity(params.query_vector, 'content_embedding') + 1.0;
                                return Math.max(titleScore * 1.5, contentScore);
                            """,
                            "params": {
                                "query_vector": query_vector
                            }
                        }
                    }
                },
                "_source": ["title", "city", "state", "short_summary"],
                "highlight": {
                    "fields": {
                        "full_content": {
                            "fragment_size": 150,
                            "number_of_fragments": 1,
                            "highlight_query": {
                                "match": {
                                    "full_content": "mountain Utah tallest"
                                }
                            }
                        }
                    }
                }
            }
            
            self.run_vector_search(qa_query, f"Test 6: Question-Answer Search - '{query_text}'")
            self._explain_test(
                "Question-Answer Search",
                "Optimized for finding answers to natural language questions. "
                "Uses combined scoring from title and content embeddings. "
                "Particularly effective for factual queries and information retrieval."
            )
        
        # Test 7: Similarity Threshold Search
        query_text = "San Francisco Bay Area"
        query_vector = self.get_query_embedding(query_text)
        
        if query_vector:
            threshold_query = {
                "size": 10,
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
                "_source": ["title", "city", "state"],
                "min_score": 1.7  # High similarity threshold (0.7 cosine similarity)
            }
            
            self.run_vector_search(threshold_query, f"Test 7: High Similarity Search - '{query_text}' (>0.7 similarity)")
            self._explain_test(
                "Similarity Threshold Search",
                "Returns only highly similar documents using min_score filter. "
                "Score of 1.7 = cosine similarity of 0.7 (very similar). "
                "Useful for finding near-duplicates or highly related content."
            )
    
    def find_similar_documents(self) -> None:
        """Find similar documents to a given document."""
        print("\n" + "=" * 70)
        print("🔍 DOCUMENT SIMILARITY SEARCH")
        print("=" * 70)
        
        # First, get a sample document
        sample_query = {
            "size": 1,
            "query": {
                "match": {
                    "title": "Golden Gate"
                }
            },
            "_source": ["title", "content_embedding", "city", "state"]
        }
        
        response = self.es.search(index='wikipedia_embeddings', body=sample_query)
        
        if response['hits']['hits']:
            source_doc = response['hits']['hits'][0]['_source']
            source_title = source_doc['title']
            
            if 'content_embedding' in source_doc:
                print(f"Finding documents similar to: '{source_title}'")
                print("-" * 60)
                
                # Use the document's embedding as the query vector
                similar_query = {
                    "size": 5,
                    "query": {
                        "script_score": {
                            "query": {
                                "bool": {
                                    "must_not": [
                                        {"term": {"title.keyword": source_title}}  # Exclude the source document
                                    ]
                                }
                            },
                            "script": {
                                "source": "cosineSimilarity(params.query_vector, 'content_embedding') + 1.0",
                                "params": {
                                    "query_vector": source_doc['content_embedding']
                                }
                            }
                        }
                    },
                    "_source": ["title", "city", "state", "categories"]
                }
                
                self.run_vector_search(similar_query, f"Documents similar to '{source_title}'")
                self._explain_test(
                    "Document Similarity",
                    "Uses an existing document's embedding to find similar documents. "
                    "Useful for 'more like this' features and content recommendations. "
                    "Excludes the source document from results."
                )
    
    def compare_search_methods(self) -> None:
        """Compare different search methods on the same query."""
        print("\n" + "=" * 70)
        print("⚖️ SEARCH METHOD COMPARISON")
        print("=" * 70)
        
        query_text = "historical landmarks in California"
        query_vector = self.get_query_embedding(query_text)
        
        if not query_vector:
            print("❌ Could not generate query embedding")
            return
        
        print(f"Query: '{query_text}'")
        print("=" * 60)
        
        # Method 1: Pure keyword search
        keyword_query = {
            "size": 6,
            "query": {
                "match": {
                    "full_content": query_text
                }
            },
            "_source": ["title", "city", "state", "categories"]
        }
        
        print("\n1️⃣ Keyword Search (BM25):")
        print("   Matching based on exact term frequency and document relevance")
        keyword_response = self.es.search(index='wikipedia_embeddings', body=keyword_query)
        for i, hit in enumerate(keyword_response['hits']['hits'], 1):
            title = hit['_source']['title']
            location = []
            if hit['_source'].get('city'):
                location.append(hit['_source']['city'])
            if hit['_source'].get('state'):
                location.append(hit['_source']['state'])
            location_str = f" ({', '.join(location)})" if location else ""
            print(f"   {i}. {title}{location_str}")
            print(f"      Score: {hit['_score']:.3f}")
        
        if not keyword_response['hits']['hits']:
            print("   No keyword matches found")
        
        # Method 2: Pure vector search
        vector_query = {
            "size": 6,
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
            "_source": ["title", "city", "state", "categories"]
        }
        
        print("\n2️⃣ Vector Search (Semantic):")
        print("   Finding conceptually similar documents using embeddings")
        vector_response = self.es.search(index='wikipedia_embeddings', body=vector_query)
        for i, hit in enumerate(vector_response['hits']['hits'], 1):
            title = hit['_source']['title']
            location = []
            if hit['_source'].get('city'):
                location.append(hit['_source']['city'])
            if hit['_source'].get('state'):
                location.append(hit['_source']['state'])
            location_str = f" ({', '.join(location)})" if location else ""
            print(f"   {i}. {title}{location_str}")
            print(f"      Score: {hit['_score']:.3f} (cosine similarity: {(hit['_score']-1):.3f})")
        
        # Method 3: Hybrid search
        hybrid_query = {
            "size": 6,
            "query": {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "full_content": {
                                    "query": query_text,
                                    "boost": 1
                                }
                            }
                        },
                        {
                            "script_score": {
                                "query": {"match_all": {}},
                                "script": {
                                    "source": "cosineSimilarity(params.query_vector, 'content_embedding') + 1.0",
                                    "params": {
                                        "query_vector": query_vector
                                    }
                                },
                                "boost": 2
                            }
                        }
                    ]
                }
            },
            "_source": ["title", "city", "state", "categories"]
        }
        
        print("\n3️⃣ Hybrid Search (Keyword + Vector):")
        print("   Combining BM25 keyword matching with semantic similarity")
        hybrid_response = self.es.search(index='wikipedia_embeddings', body=hybrid_query)
        for i, hit in enumerate(hybrid_response['hits']['hits'], 1):
            title = hit['_source']['title']
            location = []
            if hit['_source'].get('city'):
                location.append(hit['_source']['city'])
            if hit['_source'].get('state'):
                location.append(hit['_source']['state'])
            location_str = f" ({', '.join(location)})" if location else ""
            print(f"   {i}. {title}{location_str}")
            print(f"      Combined Score: {hit['_score']:.3f}")
        
        # Add comparison analysis
        print("\n📊 Results Analysis:")
        print("-" * 60)
        
        # Find overlapping results
        keyword_titles = {hit['_source']['title'] for hit in keyword_response['hits']['hits']}
        vector_titles = {hit['_source']['title'] for hit in vector_response['hits']['hits']}
        hybrid_titles = {hit['_source']['title'] for hit in hybrid_response['hits']['hits']}
        
        all_methods = keyword_titles & vector_titles & hybrid_titles
        keyword_vector = keyword_titles & vector_titles
        keyword_hybrid = keyword_titles & hybrid_titles
        vector_hybrid = vector_titles & hybrid_titles
        
        print(f"• Documents found by ALL methods: {len(all_methods)}")
        if all_methods:
            for title in list(all_methods)[:3]:
                print(f"  - {title}")
        
        print(f"• Documents in both Keyword & Vector: {len(keyword_vector)}")
        print(f"• Documents in both Keyword & Hybrid: {len(keyword_hybrid)}")
        print(f"• Documents in both Vector & Hybrid: {len(vector_hybrid)}")
        
        print(f"\n• Unique to Keyword search: {len(keyword_titles - vector_titles - hybrid_titles)}")
        print(f"• Unique to Vector search: {len(vector_titles - keyword_titles - hybrid_titles)}")
        print(f"• Unique to Hybrid search: {len(hybrid_titles - keyword_titles - vector_titles)}")
        
        # Score ranges
        print("\n📈 Score Distributions:")
        if keyword_response['hits']['hits']:
            keyword_scores = [hit['_score'] for hit in keyword_response['hits']['hits']]
            print(f"• Keyword (BM25): {min(keyword_scores):.2f} - {max(keyword_scores):.2f}")
        
        if vector_response['hits']['hits']:
            vector_scores = [hit['_score'] for hit in vector_response['hits']['hits']]
            print(f"• Vector (Cosine): {min(vector_scores):.2f} - {max(vector_scores):.2f}")
        
        if hybrid_response['hits']['hits']:
            hybrid_scores = [hit['_score'] for hit in hybrid_response['hits']['hits']]
            print(f"• Hybrid (Combined): {min(hybrid_scores):.2f} - {max(hybrid_scores):.2f}")
        
        self._explain_test(
            "Search Method Comparison",
            "Demonstrates how different search methods return different results. "
            "Keyword search finds exact matches, vector search finds semantic similarity, "
            "and hybrid search combines both for balanced results."
        )
    
    def interactive_search(self) -> None:
        """Allow user to run custom semantic searches."""
        print("\n" + "=" * 70)
        print("🎯 INTERACTIVE SEMANTIC SEARCH")
        print("=" * 70)
        print("\nEnter search queries (or 'quit' to exit):")
        print("Tip: Try natural language questions or concepts!")
        print()
        
        while True:
            query_text = input("Search > ").strip()
            
            if query_text.lower() in ['quit', 'exit', 'q']:
                break
            
            if not query_text:
                continue
            
            # Get embedding for query
            query_vector = self.get_query_embedding(query_text)
            
            if not query_vector:
                print("❌ Could not generate embedding for query")
                continue
            
            # Perform semantic search
            search_query = {
                "size": 5,
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
                "_source": ["title", "city", "state", "short_summary"],
                "min_score": 1.0
            }
            
            self.run_vector_search(search_query, f"Semantic search: '{query_text}'")
    
    def show_summary(self) -> None:
        """Display summary of all test results."""
        print("\n" + "=" * 70)
        print("📋 SEMANTIC SEARCH TEST SUMMARY")
        print("=" * 70)
        
        if not self.test_results:
            print("No test results to display")
            return
        
        # Create summary table
        table_data = []
        for result in self.test_results:
            if 'error' not in result:
                table_data.append([
                    result['description'][:40] + "...",
                    result['total_hits'],
                    f"{result['max_score']:.2f}" if result['max_score'] else "N/A",
                    len(result['results'])
                ])
        
        if table_data:
            print(tabulate(
                table_data,
                headers=['Test', 'Total Hits', 'Max Score', 'Shown'],
                tablefmt='grid'
            ))
        
        # Add score explanation for vector search
        print("\n📊 **Understanding Vector Search Scores:**")
        print("-" * 60)
        print("• **Score Calculation**: cosine_similarity + 1.0")
        print("• **Score Range**: 0.0 to 2.0 (theoretical)")
        print("• **Score Interpretation**:")
        print("  - **1.9-2.0**: Nearly identical (>90% similar)")
        print("  - **1.7-1.9**: Very similar (70-90% similar)")
        print("  - **1.5-1.7**: Similar (50-70% similar)")
        print("  - **1.3-1.5**: Somewhat similar (30-50% similar)")
        print("  - **1.0-1.3**: Weakly similar (0-30% similar)")
        print("\n• **Cosine Similarity**:")
        print("  - 1.0 = Identical vectors")
        print("  - 0.0 = Orthogonal (unrelated)")
        print("  - -1.0 = Opposite vectors")
        print("\n• **Factors Affecting Similarity**:")
        print("  - Semantic meaning overlap")
        print("  - Vocabulary and context")
        print("  - Document length and detail")
        print("  - Language model training data")
        
        # Show index statistics
        try:
            stats = self.es.count(index='wikipedia_embeddings')
            print(f"\n📊 Index Statistics:")
            print(f"   Total documents: {stats['count']:,}")
            
            # Get embedding stats
            processed = self.es.count(
                index='wikipedia_embeddings',
                body={"query": {"term": {"embeddings_processed": True}}}
            )
            print(f"   Documents with embeddings: {processed['count']:,}")
            print(f"   Total vectors: {processed['count'] * 3:,} (title, content, summary)")
            print(f"   Vector dimensions: {EMBEDDING_DIM}")
            
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
    print("🔬 Semantic Search Testing Suite")
    print("=" * 70)
    
    # Create Elasticsearch client
    es = create_elasticsearch_client()
    
    # Verify connection
    if not es.ping():
        print("❌ Cannot connect to Elasticsearch!")
        return 1
    
    print("✅ Connected to Elasticsearch")
    
    # Check if embeddings index exists
    if not es.indices.exists(index='wikipedia_embeddings'):
        print("❌ Wikipedia embeddings index not found!")
        print("Please run: python inference/process_wikipedia_embeddings.py")
        return 1
    
    # Check document count
    count = es.count(index='wikipedia_embeddings')['count']
    if count == 0:
        print("❌ Embeddings index is empty!")
        print("Please run: python inference/process_wikipedia_embeddings.py")
        return 1
    
    print(f"✅ Found {count:,} documents in wikipedia_embeddings index")
    
    # Check for documents with embeddings
    processed = es.count(
        index='wikipedia_embeddings',
        body={"query": {"term": {"embeddings_processed": True}}}
    )['count']
    
    if processed == 0:
        print("❌ No documents have embeddings yet!")
        print("Please run: python inference/process_wikipedia_embeddings.py")
        return 1
    
    print(f"✅ Found {processed:,} documents with embeddings")
    
    # Create tester and run tests
    tester = EmbeddingSearchTester(es)
    
    # Run automated tests
    tester.test_semantic_searches()
    
    # Find similar documents
    tester.find_similar_documents()
    
    # Compare search methods
    tester.compare_search_methods()
    
    # Show summary
    tester.show_summary()
    
    # Offer interactive search
    print("\n" + "=" * 70)
    response = input("\nWould you like to try interactive semantic search? (y/n): ")
    if response.lower() == 'y':
        tester.interactive_search()
    
    print("\n✨ Semantic search testing complete!")
    print("\n💡 Key Takeaways:")
    print("• Semantic search finds conceptually related content")
    print("• Hybrid search combines precision and recall")
    print("• Multi-field search improves relevance")
    print("• Vector similarity enables 'more like this' features")
    
    return 0

if __name__ == "__main__":
    exit(main())