#!/usr/bin/env python3
"""
DEMO 5: PURE VECTOR EMBEDDING SEARCH
=====================================

This demonstration showcases pure vector similarity search without graph boosting,
demonstrating the raw power of semantic embeddings for property discovery.

Key Capabilities:
1. Pure semantic similarity search using embeddings
2. Direct vector distance calculations
3. Semantic understanding of natural language queries
4. Cross-domain similarity (finding unexpected matches)
5. Embedding space exploration
6. Comparison with hybrid search results

This demo helps understand what the embeddings alone can do versus
the enhanced hybrid approach that combines vectors with graph intelligence.
"""

import sys
import signal
from pathlib import Path
from typing import Dict, List, Any, Optional
import time
import numpy as np

# Handle broken pipe errors gracefully when piping output
if hasattr(signal, 'SIGPIPE'):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import get_neo4j_driver
from src.database.neo4j_client import run_query
from src.vectors import PropertyEmbeddingPipeline
from src.vectors.config_loader import get_embedding_config, get_vector_index_config


class PureVectorSearchDemo:
    """Demonstrate pure vector embedding search capabilities"""
    
    def __init__(self, driver):
        self.driver = driver
        
        # Initialize embedding pipeline
        try:
            embedding_config = get_embedding_config()
            vector_config = get_vector_index_config()
            self.pipeline = PropertyEmbeddingPipeline(driver, embedding_config, vector_config)
            
            # Check if embeddings exist
            status = self.pipeline.vector_manager.check_embeddings_exist()
            self.embeddings_available = status['with_embeddings'] > 0
            
            if not self.embeddings_available:
                print("No embeddings found! Please run 'python create_embeddings.py' first.")
            else:
                print(f"Found {status['with_embeddings']} properties with embeddings")
                print(f"Using {embedding_config.provider} with {self.pipeline._get_model_name()}")
                print(f"Embedding dimensions: {vector_config.vector_dimensions}")
                
        except Exception as e:
            print(f"Could not initialize embedding pipeline: {e}")
            self.embeddings_available = False
    
    def print_section_header(self, title: str, description: str = ""):
        """Print formatted section header"""
        print(f"\n{'='*80}")
        print(f"{title.upper()}")
        print(f"{'='*80}")
        if description:
            print(f"{description}\n")
    
    def pure_vector_search(self, query: str, top_k: int = 5, min_score: float = 0.0) -> List[Dict[str, Any]]:
        """
        Perform pure vector similarity search without any graph boosting
        
        Args:
            query: Natural language search query
            top_k: Number of results to return
            min_score: Minimum similarity score threshold
            
        Returns:
            List of search results with similarity scores
        """
        if not self.embeddings_available:
            return []
        
        # Generate embedding for query
        query_embedding = self.pipeline.embed_model.get_text_embedding(query)
        
        # Perform pure vector search
        results = self.pipeline.vector_manager.vector_search(
            query_embedding=query_embedding,
            top_k=top_k,
            min_score=min_score
        )
        
        return results
    
    # ===== SECTION 1: BASIC SEMANTIC SEARCH =====
    
    def demo_basic_semantic_search(self):
        """Demonstrate basic semantic similarity search"""
        self.print_section_header(
            "Basic Semantic Search",
            "Pure vector similarity search using natural language queries"
        )
        
        queries = [
            "modern luxury penthouse with city views",
            "cozy family home with backyard",
            "investment property near tech companies",
            "ski-in ski-out mountain retreat",
            "historic victorian with original details"
        ]
        
        for query_text in queries:
            print(f"\nQuery: \"{query_text}\"")
            print("-" * 60)
            
            start_time = time.time()
            results = self.pure_vector_search(query_text, top_k=3)
            search_time = time.time() - start_time
            
            if results:
                print(f"Search time: {search_time*1000:.1f}ms")
                print(f"Top {len(results)} matches by pure vector similarity:\n")
                
                for i, result in enumerate(results, 1):
                    print(f"{i}. Property {result['listing_id']} - Score: {result['score']:.4f}")
                    print(f"   {result['neighborhood']}, {result['city']}")
                    print(f"   ${result['price']:,.0f}")
                    if result.get('bedrooms'):
                        print(f"   {result['bedrooms']} bed, {result['bathrooms']} bath, {result['square_feet']:,} sqft")
                    if result.get('description'):
                        desc = result['description'][:150].replace('\n', ' ')
                        print(f"   {desc}...")
            else:
                print("   No results found")
    
    # ===== SECTION 2: SEMANTIC UNDERSTANDING =====
    
    def demo_semantic_understanding(self):
        """Show how embeddings understand semantic meaning"""
        self.print_section_header(
            "Semantic Understanding",
            "Demonstrating how vector embeddings capture meaning, not just keywords"
        )
        
        # Pairs of semantically similar queries with different wording
        query_pairs = [
            {
                "queries": [
                    "house for a large family",
                    "spacious home with many bedrooms"
                ],
                "concept": "Family Size"
            },
            {
                "queries": [
                    "quiet peaceful neighborhood",
                    "serene residential area away from noise"
                ],
                "concept": "Tranquility"
            },
            {
                "queries": [
                    "good for entertaining guests",
                    "perfect for hosting parties"
                ],
                "concept": "Entertainment"
            }
        ]
        
        for pair in query_pairs:
            print(f"\nSemantic Concept: {pair['concept']}")
            print("-" * 60)
            
            all_results = []
            for query in pair['queries']:
                results = self.pure_vector_search(query, top_k=3)
                all_results.append({
                    'query': query,
                    'results': results
                })
            
            # Compare results
            print(f"Query 1: \"{pair['queries'][0]}\"")
            print(f"Query 2: \"{pair['queries'][1]}\"")
            print("\nOverlap in top results:")
            
            if all_results[0]['results'] and all_results[1]['results']:
                ids_1 = {r['listing_id'] for r in all_results[0]['results']}
                ids_2 = {r['listing_id'] for r in all_results[1]['results']}
                overlap = ids_1.intersection(ids_2)
                
                if overlap:
                    print(f"   {len(overlap)} common properties found: {', '.join(overlap)}")
                    print("   -> Embeddings understand these queries are semantically similar!")
                else:
                    print("   Warning: Different results, but may still be semantically aligned")
                
                # Show similarity scores for context
                scores_1 = [f"{r['score']:.3f}" for r in all_results[0]['results'][:3]]
                scores_2 = [f"{r['score']:.3f}" for r in all_results[1]['results'][:3]]
                print(f"\n   Scores for Query 1: {scores_1}")
                print(f"   Scores for Query 2: {scores_2}")
    
    # ===== SECTION 3: CROSS-DOMAIN SIMILARITY =====
    
    def demo_cross_domain_similarity(self):
        """Find properties through indirect/metaphorical descriptions"""
        self.print_section_header(
            "Cross-Domain Similarity",
            "Finding properties through abstract or metaphorical descriptions"
        )
        
        abstract_queries = [
            {
                "query": "james bond style bachelor pad",
                "expecting": "luxury, modern, sophisticated"
            },
            {
                "query": "zen meditation retreat",
                "expecting": "peaceful, minimalist, natural"
            },
            {
                "query": "silicon valley tech executive home",
                "expecting": "modern, high-tech, expensive"
            },
            {
                "query": "artist's creative sanctuary",
                "expecting": "unique, inspiring spaces"
            }
        ]
        
        for item in abstract_queries:
            print(f"\nAbstract Query: \"{item['query']}\"")
            print(f"   Expected: {item['expecting']}")
            print("-" * 60)
            
            results = self.pure_vector_search(item['query'], top_k=2)
            
            if results:
                print("Properties that match the concept:\n")
                for i, result in enumerate(results, 1):
                    print(f"{i}. Property {result['listing_id']} (Score: {result['score']:.3f})")
                    print(f"   ${result['price']:,.0f} in {result['neighborhood']}")
                    
                    # Try to identify why it matched
                    desc_lower = result.get('description', '').lower()
                    matching_concepts = []
                    
                    luxury_words = ['luxury', 'high-end', 'premium', 'exclusive']
                    tech_words = ['smart', 'automated', 'high-tech', 'modern']
                    peaceful_words = ['quiet', 'serene', 'peaceful', 'tranquil']
                    creative_words = ['unique', 'artistic', 'creative', 'inspiring']
                    
                    if any(word in desc_lower for word in luxury_words):
                        matching_concepts.append("luxury")
                    if any(word in desc_lower for word in tech_words):
                        matching_concepts.append("tech/modern")
                    if any(word in desc_lower for word in peaceful_words):
                        matching_concepts.append("peaceful")
                    if any(word in desc_lower for word in creative_words):
                        matching_concepts.append("creative")
                    
                    if matching_concepts:
                        print(f"   Matched concepts: {', '.join(matching_concepts)}")
            else:
                print("   No matches found")
    
    # ===== SECTION 4: SIMILARITY THRESHOLD ANALYSIS =====
    
    def demo_similarity_thresholds(self):
        """Analyze how similarity scores affect result quality"""
        self.print_section_header(
            "Similarity Threshold Analysis",
            "Understanding vector similarity scores and result quality"
        )
        
        query = "luxury waterfront property with modern amenities"
        thresholds = [0.0, 0.3, 0.5, 0.7, 0.8]
        
        print(f"Test Query: \"{query}\"\n")
        
        all_results = {}
        for threshold in thresholds:
            results = self.pure_vector_search(query, top_k=100, min_score=threshold)
            all_results[threshold] = results
            
        # Analyze results at different thresholds
        print("Results at Different Similarity Thresholds:\n")
        print(f"{'Threshold':<12} {'Count':<8} {'Avg Score':<12} {'Price Range':<30}")
        print("-" * 70)
        
        for threshold in thresholds:
            results = all_results[threshold]
            if results:
                scores = [r['score'] for r in results]
                prices = [r['price'] for r in results]
                avg_score = np.mean(scores)
                price_range = f"${min(prices):,.0f} - ${max(prices):,.0f}"
            else:
                avg_score = 0
                price_range = "N/A"
            
            print(f"{threshold:<12.1f} {len(results):<8} {avg_score:<12.3f} {price_range:<30}")
        
        # Show score distribution
        print("\nScore Distribution for Top 20 Results (no threshold):")
        if all_results[0.0]:
            top_20_scores = [r['score'] for r in all_results[0.0][:20]]
            
            # Create a simple histogram
            bins = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            histogram = {b: 0 for b in bins}
            
            for score in top_20_scores:
                for bin_val in bins:
                    if score <= bin_val:
                        histogram[bin_val] += 1
                        break
            
            for bin_val in bins:
                bar = "#" * histogram[bin_val]
                print(f"   <={bin_val:.1f}: {bar} ({histogram[bin_val]})")
        
        print("\nInsights:")
        print("   • Scores > 0.8: Extremely relevant matches")
        print("   • Scores 0.6-0.8: Good semantic matches")
        print("   • Scores 0.4-0.6: Moderate relevance")
        print("   • Scores < 0.4: Weak semantic connection")
    
    # ===== SECTION 5: VECTOR VS HYBRID COMPARISON =====
    
    def demo_vector_vs_hybrid_comparison(self):
        """Compare pure vector search with hybrid search results"""
        self.print_section_header(
            "Vector vs Hybrid Search Comparison",
            "Comparing pure embedding search with graph-enhanced hybrid search"
        )
        
        # Import hybrid search for comparison
        try:
            from src.vectors import HybridPropertySearch
            from src.vectors.config_loader import get_search_config
            
            search_config = get_search_config()
            hybrid_search = HybridPropertySearch(self.driver, self.pipeline, search_config)
            
            test_queries = [
                "luxury penthouse in tech neighborhood",
                "family home near parks",
                "investment property with rental potential"
            ]
            
            for query_text in test_queries:
                print(f"\nQuery: \"{query_text}\"")
                print("-" * 60)
                
                # Pure vector search
                vector_start = time.time()
                vector_results = self.pure_vector_search(query_text, top_k=5)
                vector_time = time.time() - vector_start
                
                # Hybrid search
                hybrid_start = time.time()
                hybrid_results = hybrid_search.search(query_text, top_k=5, use_graph_boost=True)
                hybrid_time = time.time() - hybrid_start
                
                print("\nPURE VECTOR SEARCH:")
                print(f"   Time: {vector_time*1000:.1f}ms")
                if vector_results:
                    for i, r in enumerate(vector_results[:3], 1):
                        print(f"   {i}. {r['listing_id']} (Score: {r['score']:.3f}) - ${r['price']:,.0f}")
                
                print("\nHYBRID SEARCH (Vector + Graph):")
                print(f"   Time: {hybrid_time*1000:.1f}ms")
                if hybrid_results:
                    for i, r in enumerate(hybrid_results[:3], 1):
                        print(f"   {i}. {r.listing_id} (Combined: {r.combined_score:.3f}) - ${r.price:,.0f}")
                        print(f"      Vector: {r.vector_score:.3f} | Graph: {r.graph_score:.3f}")
                
                # Analyze differences
                if vector_results and hybrid_results:
                    vector_ids = [r['listing_id'] for r in vector_results[:3]]
                    hybrid_ids = [r.listing_id for r in hybrid_results[:3]]
                    
                    overlap = set(vector_ids).intersection(set(hybrid_ids))
                    print(f"\nAnalysis:")
                    print(f"   Overlap: {len(overlap)}/3 properties in common")
                    
                    if len(overlap) < 3:
                        print("   Graph relationships influenced the ranking!")
                        unique_hybrid = set(hybrid_ids) - set(vector_ids)
                        if unique_hybrid:
                            print(f"   Graph boosted: {', '.join(unique_hybrid)}")
                
        except Exception as e:
            print(f"Could not compare with hybrid search: {e}")
            print("   Run this section after implementing hybrid search")
    
    # ===== SECTION 6: EMBEDDING SPACE EXPLORATION =====
    
    def demo_embedding_space_exploration(self):
        """Explore the embedding space and property clusters"""
        self.print_section_header(
            "Embedding Space Exploration",
            "Understanding how properties cluster in embedding space"
        )
        
        # Find properties that are very similar to each other
        print("Finding Natural Clusters in Embedding Space:\n")
        
        # Sample a few properties and find their nearest neighbors
        sample_query = """
        MATCH (p:Property)
        WHERE p.descriptionEmbedding IS NOT NULL
        RETURN p.listing_id as listing_id, 
               p.listing_price as price,
               p.description as description
        ORDER BY p.listing_price DESC
        LIMIT 5
        """
        
        sample_properties = run_query(self.driver, sample_query)
        
        for prop in sample_properties[:3]:
            print(f"\nAnchor Property: {prop['listing_id']} (${prop['price']:,.0f})")
            
            # Use property description as query to find similar properties
            if prop.get('description'):
                similar = self.pure_vector_search(prop['description'], top_k=4)
                
                # Filter out the property itself
                similar = [s for s in similar if s['listing_id'] != prop['listing_id']]
                
                if similar:
                    print("   Nearest neighbors in embedding space:")
                    for i, sim in enumerate(similar[:3], 1):
                        print(f"      {i}. {sim['listing_id']} (Similarity: {sim['score']:.3f})")
                        print(f"         ${sim['price']:,.0f} in {sim['neighborhood']}")
                    
                    # Analyze what makes them similar
                    price_variance = np.std([s['price'] for s in similar] + [prop['price']])
                    avg_similarity = np.mean([s['score'] for s in similar[:3]])
                    
                    print(f"\n   Cluster Analysis:")
                    print(f"      Average similarity: {avg_similarity:.3f}")
                    print(f"      Price variance: ${price_variance:,.0f}")
                    
                    if price_variance < 500000:
                        print("      -> Tight price clustering")
                    if avg_similarity > 0.8:
                        print("      -> Very similar properties")
        
        # Analyze global embedding statistics
        print("\n\nGlobal Embedding Space Statistics:")
        
        stats_query = """
        MATCH (p1:Property)-[s:SIMILAR_TO]->(p2:Property)
        WHERE s.similarity_score > 0.7
        RETURN count(s) as high_similarity_pairs,
               avg(s.similarity_score) as avg_high_similarity,
               max(s.similarity_score) as max_similarity
        """
        
        stats = run_query(self.driver, stats_query)
        if stats:
            stat = stats[0]
            print(f"   High similarity pairs (>0.7): {stat['high_similarity_pairs']}")
            # Handle None values by providing defaults
            avg_sim = stat['avg_high_similarity'] or 0.0
            max_sim = stat['max_similarity'] or 0.0
            print(f"   Average high similarity: {avg_sim:.3f}")
            print(f"   Maximum similarity: {max_sim:.3f}")


def run_pure_vector_search_demo():
    """Run the complete pure vector search demonstration"""
    print("PURE VECTOR EMBEDDING SEARCH DEMO")
    print("="*80)
    print("Demonstrating the power of semantic embeddings for property search")
    print("without graph boosting, showing what pure vector similarity can achieve.")
    print("="*80)
    
    driver = None
    try:
        driver = get_neo4j_driver()
        demo = PureVectorSearchDemo(driver)
        
        if not demo.embeddings_available:
            print("\nError: Cannot run demo without embeddings.")
            print("Please run: python create_embeddings.py")
            return
        
        # Run all demo sections
        demo.demo_basic_semantic_search()
        demo.demo_semantic_understanding()
        demo.demo_cross_domain_similarity()
        demo.demo_similarity_thresholds()
        demo.demo_vector_vs_hybrid_comparison()
        demo.demo_embedding_space_exploration()
        
        print(f"\n{'='*80}")
        print("PURE VECTOR SEARCH DEMO COMPLETE")
        print("="*80)
        print("\nKey Insights:")
        print("• Vector embeddings provide powerful semantic understanding")
        print("• Can find properties through natural language and abstract concepts")
        print("• Similarity scores indicate semantic relevance (>0.8 is excellent)")
        print("• Properties cluster naturally in embedding space")
        print("• Hybrid search adds graph intelligence for even better results")
        print("\nPure vector search excels at semantic matching, while hybrid search")
        print("combines this with graph relationships for superior property discovery.")
        
    except Exception as e:
        print(f"Demo error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.close()


if __name__ == "__main__":
    run_pure_vector_search_demo()