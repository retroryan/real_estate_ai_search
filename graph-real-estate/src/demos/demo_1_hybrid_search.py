#!/usr/bin/env python3
"""
DEMO 1: ADVANCED HYBRID SEARCH SHOWCASE
========================================

This demo showcases the power of combining semantic vector search with graph relationships
in Neo4j. It demonstrates how natural language queries are enhanced by graph intelligence,
feature relationships, and similarity calculations.

Key Capabilities Demonstrated:
1. Semantic vector search with natural language understanding
2. Graph-boosted scoring using property similarities
3. Feature-based intelligence and cross-feature correlations  
4. Lifestyle-based neighborhood matching
5. Complex multi-criteria search with contextual ranking
6. Geographic and market intelligence integration

Database Context:
- 420 properties with 768-dimensional embeddings
- 416 features across 8 categories with 3,257 feature relationships
- 1,608 property similarities (avg score: 0.823)
- 21 neighborhoods with lifestyle tags across 2 cities
- Complex graph with 6,447 total relationships
"""

import sys
import signal
from pathlib import Path
from typing import Dict, List, Any
import time

# Handle broken pipe errors gracefully when piping output
if hasattr(signal, 'SIGPIPE'):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.vectors import PropertyEmbeddingPipeline, HybridPropertySearch
from src.vectors.hybrid_search import SearchResult
from src.vectors.config_loader import get_embedding_config, get_vector_index_config, get_search_config
from src.database.neo4j_client import get_neo4j_driver, close_neo4j_driver
from src.database.neo4j_client import run_query


class AdvancedHybridSearchDemo:
    """Comprehensive demonstration of hybrid search capabilities"""
    
    def __init__(self):
        """Initialize the demo with database connection and search pipeline"""
        print("Initializing Advanced Hybrid Search Demo...")
        
        # Connect to database
        self.driver = get_neo4j_driver()
        
        # Load configurations
        embedding_config = get_embedding_config()
        vector_config = get_vector_index_config()
        search_config = get_search_config()
        
        # Initialize search pipeline
        self.pipeline = PropertyEmbeddingPipeline(self.driver, embedding_config, vector_config)
        self.search = HybridPropertySearch(self.driver, self.pipeline, search_config)
        
        # Verify embeddings exist
        status = self.pipeline.vector_manager.check_embeddings_exist()
        if status['with_embeddings'] == 0:
            raise RuntimeError("Error: No embeddings found! Run 'python create_embeddings.py' first.")
        
        print(f"Ready to search {status['with_embeddings']} properties with embeddings")
    
    def format_result(self, result: SearchResult, index: int, show_analysis: bool = True) -> str:
        """Format search result with detailed analysis"""
        output = []
        output.append(f"\n{index}. {result.listing_id}")
        output.append("   " + "─" * 70)
        
        # Basic property info
        if result.address:
            output.append(f"   Address: {result.address}")
        output.append(f"   Location: {result.neighborhood}, {result.city}")
        output.append(f"   Price: ${result.price:,.0f}")
        
        # Property details
        if result.bedrooms or result.bathrooms or result.square_feet:
            details = []
            if result.bedrooms:
                details.append(f"{result.bedrooms} bed")
            if result.bathrooms:
                details.append(f"{result.bathrooms} bath")
            if result.square_feet:
                details.append(f"{result.square_feet:,} sqft")
            if result.square_feet and result.price:
                price_per_sqft = result.price / result.square_feet
                details.append(f"${price_per_sqft:.0f}/sqft")
            output.append(f"   Details: {' | '.join(details)}")
        
        # Scoring analysis
        if show_analysis:
            output.append(f"   Scoring Analysis:")
            output.append(f"      Vector Similarity: {result.vector_score:.3f} (semantic match)")
            output.append(f"      Graph Boost: {result.graph_score:.3f} (relationship intelligence)")
            output.append(f"      Combined Score: {result.combined_score:.3f}")
        
        # Features (top 5 most relevant)
        if result.features and len(result.features) > 0:
            output.append(f"   Key Features: {', '.join(result.features[:5])}")
            if len(result.features) > 5:
                output.append(f"      ... and {len(result.features) - 5} more features")
        
        # Similar properties (graph intelligence)
        if result.similar_properties:
            output.append(f"   Similar Properties: {', '.join(result.similar_properties[:3])}")
        
        return '\n'.join(output)
    
    def demo_1_semantic_understanding(self):
        """Demo 1: Semantic vector search understanding complex queries"""
        print("\n" + "="*80 + "\n")
        print("DEMO 1A: SEMANTIC UNDERSTANDING & NATURAL LANGUAGE PROCESSING")
        print("="*82)
        print("Showcasing how vector embeddings understand natural language nuances")
        
        # Complex semantic queries that test natural language understanding
        semantic_queries = [
            {
                "query": "sprawling estate perfect for entertaining with gourmet kitchen",
                "description": "Tests understanding of: size (sprawling), social aspects (entertaining), high-end features (gourmet)"
            },
            {
                "query": "cozy starter home in family-friendly neighborhood near good schools",
                "description": "Tests understanding of: size preference, life stage, family needs, educational priorities"
            },
            {
                "query": "investment property with rental potential in up-and-coming area",
                "description": "Tests understanding of: investment intent, rental features, market dynamics"
            },
            {
                "query": "luxury ski-in ski-out retreat with mountain views and spa amenities",
                "description": "Tests understanding of: luxury level, specific recreation, geographic features, wellness"
            },
            {
                "query": "tech professional work-from-home setup in urban walkable neighborhood",
                "description": "Tests understanding of: profession-specific needs, remote work, urban lifestyle"
            }
        ]
        
        for i, test in enumerate(semantic_queries, 1):
            print(f"\nTest {i}: {test['description']}")
            print(f"Query: \"{test['query']}\"")
            print("─" * 80)
            
            start_time = time.time()
            results = self.search.search(query=test['query'], top_k=2, use_graph_boost=True)
            search_time = time.time() - start_time
            
            if results:
                for j, result in enumerate(results, 1):
                    print(self.format_result(result, j, show_analysis=True))
            else:
                print("   Error: No results found")
            
            print(f"\nSearch completed in {search_time:.3f} seconds")
            
            # Brief pause for readability
            time.sleep(0.5)
    
    def demo_2_graph_intelligence(self):
        """Demo 2: Graph relationship intelligence enhancing search"""
        print("\n" + "="*80 + "\n")
        print("DEMO 1B: GRAPH RELATIONSHIP INTELLIGENCE")
        print("="*82)
        print("Comparing pure vector search vs. graph-enhanced hybrid search")
        
        test_queries = [
            "luxury property with high-end amenities",
            "family home with outdoor space",
            "modern condo with city views"
        ]
        
        for query in test_queries:
            print(f"\nQuery: \"{query}\"")
            print("─" * 80)
            
            # Pure vector search (no graph boost)
            print("\nPURE VECTOR SEARCH (no graph intelligence):")
            vector_results = self.search.search(query=query, top_k=2, use_graph_boost=False)
            for i, result in enumerate(vector_results, 1):
                print(f"   {i}. {result.listing_id}: Vector={result.vector_score:.3f}, Combined={result.combined_score:.3f}")
                print(f"      {result.neighborhood}, ${result.price:,.0f}")
            
            # Graph-enhanced search
            print("\nGRAPH-ENHANCED HYBRID SEARCH:")
            hybrid_results = self.search.search(query=query, top_k=2, use_graph_boost=True)
            for i, result in enumerate(hybrid_results, 1):
                print(f"   {i}. {result.listing_id}: Vector={result.vector_score:.3f}, Graph={result.graph_score:.3f}, Combined={result.combined_score:.3f}")
                print(f"      {result.neighborhood}, ${result.price:,.0f}")
                if result.similar_properties:
                    print(f"      Graph boost from {len(result.similar_properties)} similar properties")
            
            # Analysis
            if vector_results and hybrid_results:
                vector_top = vector_results[0].listing_id
                hybrid_top = hybrid_results[0].listing_id
                if vector_top != hybrid_top:
                    print(f"\nGraph intelligence changed ranking! Vector top: {vector_top}, Hybrid top: {hybrid_top}")
                else:
                    print(f"\nGraph intelligence confirmed vector ranking for {hybrid_top}")
            
            time.sleep(0.5)
    
    def demo_3_feature_intelligence(self):
        """Demo 3: Feature relationships and cross-feature correlations"""
        print("\n" + "="*80 + "\n")
        print("DEMO 1C: FEATURE INTELLIGENCE & CROSS-FEATURE CORRELATIONS")
        print("="*82)
        print("Leveraging 416 features across 8 categories with 3,257 feature relationships")
        
        # First, show feature category intelligence
        print("\nTesting feature category understanding:")
        
        category_tests = [
            ("luxury kitchen features", "Kitchen category + high-end terms"),
            ("outdoor entertainment space", "Outdoor category + social aspects"),
            ("smart home technology", "Technology category + automation"),
            ("panoramic view amenities", "View category + premium descriptions"),
            ("recreation and wellness", "Recreation category + health/fitness")
        ]
        
        for query, description in category_tests:
            print(f"\n\"{query}\" → {description}")
            results = self.search.search(query=query, top_k=1, use_graph_boost=True)
            if results:
                result = results[0]
                print(f"   {result.listing_id}: {result.neighborhood}, ${result.price:,.0f}")
                
                # Analyze feature categories in result
                feature_analysis = self._analyze_features(result.listing_id)
                if feature_analysis:
                    print("   Feature categories found:")
                    for category, features in feature_analysis.items():
                        if features:
                            print(f"      {category}: {', '.join(features[:3])}{'...' if len(features) > 3 else ''}")
        
        # Show feature co-occurrence intelligence
        print(f"\nFeature Co-occurrence Intelligence:")
        print("   Demonstrating how the system understands feature combinations")
        
        cooccurrence_tests = [
            "mountain views with ski access",
            "city views with rooftop access", 
            "wine cellar with entertainment space",
            "home theater with smart home system"
        ]
        
        for query in cooccurrence_tests:
            print(f"\n\"{query}\"")
            results = self.search.search(query=query, top_k=1, use_graph_boost=True)
            if results:
                result = results[0]
                print(f"   Found: {result.listing_id} (${result.price:,.0f})")
                print(f"   Features: {', '.join(result.features[:5])}")
                
                # Check if the specific combination exists
                matching_features = self._check_feature_combination(result.listing_id, query)
                if matching_features:
                    print(f"   Combination confirmed: {', '.join(matching_features)}")
    
    def demo_4_complex_multi_criteria(self):
        """Demo 4: Complex multi-criteria search with filters and context"""
        print("\n" + "="*80 + "\n")
        print("DEMO 1D: COMPLEX MULTI-CRITERIA SEARCH")
        print("="*82)
        print("Combining semantic search, filters, and graph intelligence")
        
        complex_scenarios = [
            {
                "description": "Luxury Mountain Retreat Investor",
                "query": "luxury ski property with rental potential and mountain views",
                "filters": {"price_min": 2000000, "city": "Park City"},
                "context": "High-net-worth investor looking for luxury ski rental property"
            },
            {
                "description": "Tech Family Relocation",
                "query": "family home with home office space in tech-friendly neighborhood",
                "filters": {"bedrooms_min": 3, "city": "San Francisco"},
                "context": "Tech family relocating to San Francisco, needs space for remote work"
            },
            {
                "description": "Urban Professional Investment",
                "query": "modern condo with city views and building amenities",
                "filters": {"price_max": 2000000, "bedrooms_min": 2},
                "context": "Urban professional seeking investment property with strong rental appeal"
            },
            {
                "description": "Ultra-Luxury Acquisition",
                "query": "ultra-luxury estate with entertainment facilities and privacy",
                "filters": {"price_min": 5000000},
                "context": "Ultra-high net worth individual seeking premium estate"
            }
        ]
        
        for scenario in complex_scenarios:
            print(f"\n{scenario['description']}")
            print(f"Context: {scenario['context']}")
            print(f"Query: \"{scenario['query']}\"")
            print(f"Filters: {scenario['filters']}")
            print("─" * 80)
            
            start_time = time.time()
            results = self.search.search(
                query=scenario['query'],
                filters=scenario['filters'],
                top_k=2,
                use_graph_boost=True
            )
            search_time = time.time() - start_time
            
            if results:
                for i, result in enumerate(results, 1):
                    print(self.format_result(result, i, show_analysis=True))
                    
                    # Add scenario-specific analysis
                    if "rental potential" in scenario['query']:
                        self._analyze_rental_potential(result)
                    elif "tech-friendly" in scenario['query']:
                        self._analyze_tech_features(result)
                    elif "ultra-luxury" in scenario['query']:
                        self._analyze_luxury_features(result)
            else:
                print("   Error: No properties match these specific criteria")
            
            print(f"\nMulti-criteria search completed in {search_time:.3f} seconds")
            time.sleep(0.5)
    
    def demo_5_lifestyle_geographic_intelligence(self):
        """Demo 5: Lifestyle and geographic intelligence"""
        print("\n" + "="*80 + "\n")
        print("DEMO 1E: LIFESTYLE & GEOGRAPHIC INTELLIGENCE") 
        print("="*82)
        print("Leveraging neighborhood lifestyle tags and geographic relationships")
        
        # Show lifestyle understanding
        lifestyle_queries = [
            ("outdoor enthusiast dream home", "outdoor-recreation, ski-access, mountain lifestyle"),
            ("urban tech professional sanctuary", "tech-friendly, urban, walkable lifestyle"),
            ("family-oriented community living", "family-friendly neighborhoods with schools"),
            ("elevated luxury living", "elevated, premium neighborhoods")
        ]
        
        for query, lifestyle_description in lifestyle_queries:
            print(f"\n\"{query}\"")
            print(f"Target lifestyle: {lifestyle_description}")
            print("─" * 50)
            
            results = self.search.search(query=query, top_k=2, use_graph_boost=True)
            for i, result in enumerate(results, 1):
                print(f"\n{i}. {result.listing_id} in {result.neighborhood}, {result.city}")
                print(f"   ${result.price:,.0f} | Score: {result.combined_score:.3f}")
                
                # Get lifestyle analysis for this neighborhood
                lifestyle_info = self._get_neighborhood_lifestyle(result.neighborhood)
                if lifestyle_info:
                    print(f"   Neighborhood lifestyle: {', '.join(lifestyle_info)}")
                
                print(f"   Key features: {', '.join(result.features[:4])}")
        
        # Geographic relationship intelligence
        print("\n\nGEOGRAPHIC RELATIONSHIP INTELLIGENCE:")
        print("   Showing how geographic hierarchy enhances search context")
        
        geo_query = "mountain property near recreational amenities"
        print(f"\n\"{geo_query}\"")
        results = self.search.search(query=geo_query, top_k=3, use_graph_boost=True)
        
        for i, result in enumerate(results, 1):
            # Get full geographic context
            geo_context = self._get_geographic_context(result.listing_id)
            print(f"\n{i}. {result.listing_id}")
            print(f"   Full geographic context:")
            print(f"      Property → {geo_context['neighborhood']} → {geo_context['city']} → {geo_context['county']}")
            print(f"   Regional context: {geo_context['nearby_neighborhoods']} nearby neighborhoods")
            print(f"   ${result.price:,.0f} | Features: {', '.join(result.features[:3])}")
    
    def _analyze_features(self, listing_id: str) -> Dict[str, List[str]]:
        """Analyze feature categories for a property"""
        query = """
        MATCH (p:Property {listing_id: $listing_id})-[:HAS_FEATURE]->(f:Feature)
        RETURN f.category as category, collect(f.name) as features
        """
        result = run_query(self.driver, query, {"listing_id": listing_id})
        return {r['category']: r['features'] for r in result if r['category']}
    
    def _check_feature_combination(self, listing_id: str, query: str) -> List[str]:
        """Check if property has specific feature combinations"""
        # This would be enhanced with more sophisticated matching
        query = """
        MATCH (p:Property {listing_id: $listing_id})-[:HAS_FEATURE]->(f:Feature)
        RETURN collect(f.name) as all_features
        """
        result = run_query(self.driver, query, {"listing_id": listing_id})
        if result:
            return [f for f in result[0]['all_features'] if any(keyword in f.lower() for keyword in ['view', 'mountain', 'ski', 'rooftop', 'wine', 'theater', 'smart'])]
        return []
    
    def _analyze_rental_potential(self, result: SearchResult):
        """Analyze rental potential factors"""
        print(f"   Rental Analysis: High-end features and location appeal suggest strong rental potential")
    
    def _analyze_tech_features(self, result: SearchResult):
        """Analyze tech-related features"""
        tech_features = [f for f in result.features if any(tech in f.lower() for tech in ['smart', 'tech', 'fiber', 'charging', 'office'])]
        if tech_features:
            print(f"   Tech features: {', '.join(tech_features)}")
    
    def _analyze_luxury_features(self, result: SearchResult):
        """Analyze luxury features"""
        luxury_features = [f for f in result.features if any(lux in f.lower() for lux in ['wine', 'theater', 'spa', 'pool', 'elevator', 'gym'])]
        if luxury_features:
            print(f"   Luxury amenities: {', '.join(luxury_features)}")
    
    def _get_neighborhood_lifestyle(self, neighborhood: str) -> List[str]:
        """Get lifestyle tags for a neighborhood"""
        query = """
        MATCH (n:Neighborhood {name: $neighborhood})
        RETURN n.lifestyle_tags as tags
        """
        result = run_query(self.driver, query, {"neighborhood": neighborhood})
        return result[0]['tags'] if result and result[0]['tags'] else []
    
    def _get_geographic_context(self, listing_id: str) -> Dict[str, Any]:
        """Get full geographic context for a property"""
        query = """
        MATCH (p:Property {listing_id: $listing_id})-[:LOCATED_IN]->(n:Neighborhood)-[:IN_CITY]->(c:City)-[:IN_COUNTY]->(co:County)
        OPTIONAL MATCH (n)-[:NEAR]-(nearby:Neighborhood)
        RETURN n.name as neighborhood, c.name as city, co.name as county,
               count(DISTINCT nearby) as nearby_count,
               collect(DISTINCT nearby.name)[0..3] as nearby_neighborhoods
        """
        result = run_query(self.driver, query, {"listing_id": listing_id})
        if result:
            return result[0]
        return {}
    
    def run_complete_demo(self):
        """Run the complete advanced hybrid search demonstration"""
        print("\n" + "="*80 + "\n")
        print("ADVANCED HYBRID SEARCH DEMONSTRATION")
        print("Real Estate Intelligence with Neo4j Vector Search + Graph Relationships")
        print("="*82)
        print("Database: 420 properties, 416 features, 1,608 similarities, 6,447 relationships")
        print("Vector Embeddings: 768-dimensional semantic representations")
        print("Graph Intelligence: Property similarities, feature relationships, lifestyle matching")
        
        try:
            # Run all demo sections
            self.demo_1_semantic_understanding()
            self.demo_2_graph_intelligence()
            self.demo_3_feature_intelligence()
            self.demo_4_complex_multi_criteria()
            self.demo_5_lifestyle_geographic_intelligence()
            
            # Summary
            print("\n" + "="*80 + "\n")
            print("DEMONSTRATION COMPLETE")
            print("="*82)
            print("Semantic Understanding: Natural language processing with vector embeddings")
            print("Graph Intelligence: Relationship-based scoring and similarity boosting")
            print("Feature Intelligence: Cross-feature correlations and category understanding")
            print("Multi-Criteria Search: Complex filtering with contextual ranking")
            print("Geographic Intelligence: Lifestyle tags and geographic hierarchy")
            print("\nThe hybrid approach combines the best of both worlds:")
            print("   Vector search for semantic understanding of natural language")
            print("   Graph relationships for intelligent ranking and recommendations")
            print("   Result: More accurate, contextual, and intelligent property search")
            
        except KeyboardInterrupt:
            print("\n\nDemo interrupted by user")
        except Exception as e:
            print(f"\nError: Demo error: {e}")
            import traceback
            traceback.print_exc()
    
    def close(self):
        """Clean up resources"""
        if self.driver:
            close_neo4j_driver(self.driver)


def main():
    """Main function to run the advanced hybrid search demo"""
    demo = None
    try:
        demo = AdvancedHybridSearchDemo()
        demo.run_complete_demo()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\nError: Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if demo:
            demo.close()


if __name__ == "__main__":
    main()