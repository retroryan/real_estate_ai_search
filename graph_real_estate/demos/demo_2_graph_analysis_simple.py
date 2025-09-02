#!/usr/bin/env python3
"""
DEMO 2: GRAPH ANALYSIS WITH EMBEDDING-BASED SIMILARITY
========================================================

This demo showcases graph analysis capabilities using embeddings for
similarity search instead of pre-computed SIMILAR_TO relationships.

Key Capabilities Demonstrated:
1. Property location relationships and geographic patterns
2. Embedding-based similarity search on demand
3. Feature co-occurrence analysis
4. Neighborhood proximity networks
5. Market segmentation through graph traversals

Database Context:
- Properties with embeddings for similarity calculation
- Rich feature relationships (HAS_FEATURE)
- Geographic hierarchy (LOCATED_IN, IN_CITY, IN_COUNTY)
- Neighborhood proximity (NEAR) relationships
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import get_neo4j_driver, close_neo4j_driver, run_query


class GraphAnalysisDemo:
    """Demonstrate graph analysis with embedding-based similarity"""
    
    def __init__(self):
        """Initialize the demo with database connection"""
        print("\nGRAPH ANALYSIS WITH EMBEDDING-BASED SIMILARITY")
        print("=" * 80)
        print("Analyzing graph relationships and using embeddings for similarity")
        print("=" * 80)
        
        print("\n🚀 NEO4J FEATURES DEMONSTRATED:")
        print("   • Vector Embeddings - 1024-dimensional property embeddings stored as node properties")
        print("   • Cosine Similarity - On-demand vector similarity calculations")
        print("   • Graph Pattern Matching - Complex MATCH patterns for relationship analysis")
        print("   • Property Storage - Embeddings stored directly on Property nodes")
        print("   • Aggregation Pipeline - Multi-stage WITH clauses for data transformation")
        print("   • Graph Statistics - COUNT, AVG on nodes and relationships")
        print("   • NumPy Integration - Vector operations on retrieved embeddings")
        
        self.driver = get_neo4j_driver()
        
        # Check database statistics
        self._show_database_stats()
    
    def _show_database_stats(self):
        """Show database statistics"""
        print("\nDatabase Statistics:")
        
        # Count nodes
        node_types = ['Property', 'Neighborhood', 'Feature', 'City', 'County']
        for node_type in node_types:
            query = f"MATCH (n:{node_type}) RETURN count(n) as count"
            result = run_query(self.driver, query)
            if result:
                print(f"  {node_type}: {result[0]['count']}")
        
        # Count relationships
        print("\nRelationships:")
        rel_types = ['LOCATED_IN', 'HAS_FEATURE', 'IN_CITY', 'IN_COUNTY', 'NEAR']
        for rel_type in rel_types:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
            result = run_query(self.driver, query)
            if result:
                count = result[0]['count']
                if count > 0:
                    print(f"  {rel_type}: {count}")
        
        # Check embeddings
        query = """
        MATCH (p:Property)
        RETURN count(p) as total,
               count(CASE WHEN p.embedding IS NOT NULL THEN 1 END) as with_embeddings
        """
        result = run_query(self.driver, query)
        if result:
            total = result[0]['total']
            with_emb = result[0]['with_embeddings']
            print(f"\nEmbeddings: {with_emb}/{total} properties ({(with_emb/total*100):.1f}%)")
    
    def demo_location_analysis(self):
        """Analyze property location relationships"""
        print("\n" + "=" * 80)
        print("SECTION 1: LOCATION RELATIONSHIP ANALYSIS")
        print("=" * 80)
        
        # Neighborhood property density
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WITH n, count(p) as property_count, 
             avg(p.listing_price) as avg_price,
             min(p.listing_price) as min_price,
             max(p.listing_price) as max_price
        WHERE property_count >= 2
        RETURN n.name as neighborhood,
               n.city as city,
               property_count,
               avg_price,
               min_price,
               max_price
        ORDER BY avg_price DESC
        LIMIT 5
        """
        
        results = run_query(self.driver, query)
        
        if results:
            print("\nTop Neighborhoods by Average Price:")
            for i, hood in enumerate(results, 1):
                print(f"\n{i}. {hood.get('neighborhood', 'N/A')}, {hood.get('city', 'N/A')}")
                print(f"   Properties: {hood.get('property_count', 0)}")
                avg_price = hood.get('avg_price', 0) or 0
                min_price = hood.get('min_price', 0) or 0
                max_price = hood.get('max_price', 0) or 0
                print(f"   Average: ${avg_price:,.0f}")
                print(f"   Range: ${min_price:,.0f} - ${max_price:,.0f}")
    
    def demo_embedding_similarity(self):
        """Demonstrate embedding-based similarity search"""
        print("\n" + "=" * 80)
        print("SECTION 2: EMBEDDING-BASED SIMILARITY SEARCH")
        print("=" * 80)
        
        # Get a random property with embedding
        query = """
        MATCH (p:Property)
        WHERE p.embedding IS NOT NULL
        WITH p, rand() as r
        ORDER BY r
        LIMIT 1
        RETURN p.listing_id as id,
               p.street_address as address,
               p.listing_price as price,
               p.bedrooms as bedrooms,
               p.bathrooms as bathrooms,
               p.embedding as embedding
        """
        
        result = run_query(self.driver, query)
        
        if not result or not result[0].get('embedding'):
            print("\n⚠️  No properties with embeddings found")
            return
        
        source = result[0]
        print(f"\nSource Property: {source['id']}")
        print(f"  Address: {source.get('address', 'N/A')}")
        print(f"  Price: ${source.get('price', 0):,.0f}")
        print(f"  Details: {source.get('bedrooms', 0)} bed, {source.get('bathrooms', 0)} bath")
        
        # Find similar properties using embeddings
        source_embedding = np.array(source['embedding'])
        
        query = """
        MATCH (p:Property)
        WHERE p.embedding IS NOT NULL AND p.listing_id <> $source_id
        RETURN p.listing_id as id,
               p.street_address as address,
               p.listing_price as price,
               p.bedrooms as bedrooms,
               p.bathrooms as bathrooms,
               p.embedding as embedding
        """
        
        candidates = run_query(self.driver, query, {'source_id': source['id']})
        
        if candidates:
            # Calculate cosine similarities
            similarities = []
            for candidate in candidates:
                if candidate.get('embedding'):
                    cand_embedding = np.array(candidate['embedding'])
                    # Cosine similarity
                    similarity = np.dot(source_embedding, cand_embedding) / (
                        np.linalg.norm(source_embedding) * np.linalg.norm(cand_embedding)
                    )
                    similarities.append({
                        'property': candidate,
                        'similarity': similarity
                    })
            
            # Sort by similarity
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            print(f"\nTop 5 Similar Properties (using embeddings):")
            for i, item in enumerate(similarities[:5], 1):
                prop = item['property']
                sim = item['similarity']
                print(f"\n{i}. {prop['id']} (Similarity: {sim:.3f})")
                print(f"   Address: {prop.get('address', 'N/A')}")
                print(f"   Price: ${prop.get('price', 0):,.0f}")
                print(f"   Details: {prop.get('bedrooms', 0)} bed, {prop.get('bathrooms', 0)} bath")
    
    def demo_feature_analysis(self):
        """Analyze feature relationships"""
        print("\n" + "=" * 80)
        print("SECTION 3: FEATURE ANALYSIS")
        print("=" * 80)
        
        # Popular features
        query = """
        MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
        RETURN f.name as feature,
               f.category as category,
               count(p) as property_count
        ORDER BY property_count DESC
        LIMIT 10
        """
        
        results = run_query(self.driver, query)
        
        if results:
            print("\nTop 10 Most Common Features:")
            for i, feat in enumerate(results, 1):
                print(f"{i:2}. {feat.get('feature', 'Unknown')}: {feat.get('property_count', 0)} properties")
                if feat.get('category'):
                    print(f"     Category: {feat['category']}")
        
        # Feature co-occurrence
        query = """
        MATCH (f1:Feature)<-[:HAS_FEATURE]-(p:Property)-[:HAS_FEATURE]->(f2:Feature)
        WHERE f1.name < f2.name
        WITH f1.name as feature1, f2.name as feature2, count(p) as cooccurrence
        WHERE cooccurrence >= 5
        RETURN feature1, feature2, cooccurrence
        ORDER BY cooccurrence DESC
        LIMIT 10
        """
        
        results = run_query(self.driver, query)
        
        if results:
            print("\n\nFeature Co-occurrence (appears together):")
            for i, pair in enumerate(results, 1):
                print(f"{i:2}. {pair.get('feature1', 'N/A')} + {pair.get('feature2', 'N/A')}: {pair.get('cooccurrence', 0)} properties")
    
    def demo_neighborhood_proximity(self):
        """Analyze neighborhood proximity networks"""
        print("\n" + "=" * 80)
        print("SECTION 4: NEIGHBORHOOD PROXIMITY NETWORKS")
        print("=" * 80)
        
        query = """
        MATCH (n1:Neighborhood)-[:NEAR]-(n2:Neighborhood)
        MATCH (p1:Property)-[:LOCATED_IN]->(n1)
        MATCH (p2:Property)-[:LOCATED_IN]->(n2)
        WITH n1, n2, 
             avg(p1.listing_price) as avg_price1,
             avg(p2.listing_price) as avg_price2,
             count(DISTINCT p1) as count1,
             count(DISTINCT p2) as count2
        WHERE count1 >= 2 AND count2 >= 2
        WITH n1.name as neighborhood1, n2.name as neighborhood2,
             avg_price1, avg_price2,
             abs(avg_price1 - avg_price2) as price_difference
        ORDER BY price_difference DESC
        LIMIT 5
        RETURN neighborhood1, neighborhood2, 
               avg_price1, avg_price2, price_difference
        """
        
        results = run_query(self.driver, query)
        
        if results:
            print("\nNeighboring Areas with Largest Price Differences:")
            for i, pair in enumerate(results, 1):
                print(f"\n{i}. {pair.get('neighborhood1', 'N/A')} <-> {pair.get('neighborhood2', 'N/A')}")
                avg1 = pair.get('avg_price1', 0) or 0
                avg2 = pair.get('avg_price2', 0) or 0
                diff = pair.get('price_difference', 0) or 0
                print(f"   Average prices: ${avg1:,.0f} vs ${avg2:,.0f}")
                print(f"   Difference: ${diff:,.0f}")
    
    def run_demo(self):
        """Run the complete graph analysis demonstration"""
        try:
            self.demo_location_analysis()
            self.demo_embedding_similarity()
            self.demo_feature_analysis()
            self.demo_neighborhood_proximity()
            
            print("\n" + "=" * 80)
            print("GRAPH ANALYSIS DEMONSTRATION COMPLETE")
            print("=" * 80)
            print("\nKey Insights Demonstrated:")
            print("✅ Location-based graph analysis")
            print("✅ On-demand embedding similarity search")
            print("✅ Feature relationship patterns")
            print("✅ Neighborhood proximity networks")
            print("\nEmbedding-based similarity provides flexible, real-time")
            print("similarity search without pre-computed relationships!")
            
        except Exception as e:
            print(f"\n❌ Error running demo: {e}")
            import traceback
            traceback.print_exc()
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            close_neo4j_driver(self.driver)


def main():
    """Main execution function"""
    demo = None
    try:
        demo = GraphAnalysisDemo()
        demo.run_demo()
    except Exception as e:
        print(f"\n❌ Failed to initialize demo: {e}")
        return 1
    finally:
        if demo:
            demo.cleanup()
    
    return 0


if __name__ == "__main__":
    exit(main())