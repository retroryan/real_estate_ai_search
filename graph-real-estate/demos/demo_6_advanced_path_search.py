#!/usr/bin/env python3
"""
DEMO 6: ADVANCED PATH-BASED AND CONSTRAINT SEARCH
==================================================

This demo showcases advanced search capabilities using graph paths, constraints,
and complex boolean logic that goes beyond simple similarity matching.

Key Capabilities Demonstrated:
1. Multi-hop relationship path searches
2. Constraint-based property matching (must-have vs nice-to-have)
3. Exclusion and negative searches (avoiding features/areas)
4. Complex boolean logic (AND/OR/NOT combinations)
5. Shortest path analysis between properties
6. Community detection and cluster analysis
7. Property recommendation chains through shared features

These searches demonstrate the unique power of graph databases for complex
queries that would be nearly impossible with traditional databases or pure
vector search.

Database Context:
- Complex graph with 80,000+ relationships
- Multi-hop paths through features, neighborhoods, and similarities
- Rich constraint possibilities across 8 feature categories
- Community structures based on similarity networks
"""

import sys
import signal
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
import time
from collections import defaultdict, Counter

# Handle broken pipe errors gracefully when piping output
if hasattr(signal, 'SIGPIPE'):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from database import get_neo4j_driver, close_neo4j_driver, run_query


class AdvancedPathSearchDemo:
    """Demonstration of advanced path-based and constraint search capabilities"""
    
    def __init__(self):
        """Initialize the demo with database connection"""
        print("Initializing Advanced Path-Based Search Demo...")
        self.driver = get_neo4j_driver()
        
    def print_section_header(self, title: str, description: str = ""):
        """Print formatted section header"""
        print(f"\n{'='*80}")
        print(f"  {title}")
        if description:
            print(f"  {description}")
        print('='*80)
    
    def format_price(self, price: float) -> str:
        """Format price with currency symbol"""
        if price >= 1_000_000:
            return f"${price/1_000_000:.2f}M"
        elif price >= 1_000:
            return f"${price/1_000:.0f}K"
        else:
            return f"${price:.0f}"
    
    def run_all_demos(self):
        """Run all demonstration queries"""
        demos = [
            ("CONSTRAINT-BASED SEARCH", "Properties matching complex requirements", 
             self.demo_constraint_based_search),
            ("EXCLUSION SEARCH", "Finding properties while avoiding certain features", 
             self.demo_exclusion_search),
            ("MULTI-HOP PATH SEARCH", "Properties connected through feature chains", 
             self.demo_multi_hop_paths),
            ("BOOLEAN LOGIC SEARCH", "Complex AND/OR/NOT combinations", 
             self.demo_boolean_logic_search),
            ("SHORTEST PATH ANALYSIS", "Finding connections between properties", 
             self.demo_shortest_paths),
            ("COMMUNITY DETECTION", "Identifying property clusters and groups", 
             self.demo_community_detection),
            ("RECOMMENDATION CHAINS", "Property suggestions through shared attributes", 
             self.demo_recommendation_chains),
        ]
        
        for title, desc, demo_func in demos:
            self.print_section_header(title, desc)
            demo_func()
            time.sleep(0.5)  # Brief pause between sections
    
    def demo_constraint_based_search(self):
        """Demonstrate constraint-based property search with must-have and nice-to-have features"""
        
        print("\n1. STRICT CONSTRAINT SEARCH")
        print("   Finding properties with ALL must-have features...")
        
        # Must have: View, Parking, AND Modern Kitchen
        query = """
        MATCH (p:Property)
        WHERE EXISTS {
            MATCH (p)-[:HAS_FEATURE]->(:Feature {name: 'Ocean View'})
        }
        AND EXISTS {
            MATCH (p)-[:HAS_FEATURE]->(:Feature {category: 'Parking'})
        }
        AND EXISTS {
            MATCH (p)-[:HAS_FEATURE]->(:Feature {name: 'Modern Kitchen'})
        }
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
        WITH p, COLLECT(DISTINCT f.name) as all_features
        OPTIONAL MATCH (p)-[:LOCATED_IN]->(n:Neighborhood)
        RETURN 
            p.listing_id as id,
            p.price as price,
            n.name as neighborhood,
            p.bedrooms as beds,
            p.bathrooms as baths,
            all_features[0..5] as top_features,
            SIZE(all_features) as total_features
        ORDER BY p.price DESC
        LIMIT 5
        """
        
        results = run_query(self.driver, query)
        if results:
            print(f"\n   Found {len(results)} properties with ALL must-have features:")
            for r in results:
                print(f"   • {r['id']}: {self.format_price(r['price'])} in {r['neighborhood']}")
                print(f"     {r['beds']}BR/{r['baths']}BA | {r['total_features']} features")
                print(f"     Features: {', '.join(r['top_features'][:3])}...")
        
        print("\n2. WEIGHTED CONSTRAINT SEARCH")
        print("   Scoring properties by must-have vs nice-to-have features...")
        
        # Score based on feature importance
        query = """
        MATCH (p:Property)
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(must:Feature)
        WHERE must.name IN ['Ocean View', 'Modern Kitchen', 'Parking Garage']
        WITH p, COUNT(DISTINCT must) as must_have_count
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(nice:Feature)
        WHERE nice.name IN ['Wine Cellar', 'Home Theater', 'Pool']
        WITH p, must_have_count, COUNT(DISTINCT nice) as nice_to_have_count
        WHERE must_have_count > 0
        WITH p, 
             must_have_count * 10 + nice_to_have_count * 3 as score,
             must_have_count,
             nice_to_have_count
        OPTIONAL MATCH (p)-[:LOCATED_IN]->(n:Neighborhood)
        RETURN 
            p.listing_id as id,
            p.price as price,
            n.name as neighborhood,
            must_have_count,
            nice_to_have_count,
            score
        ORDER BY score DESC, p.price ASC
        LIMIT 5
        """
        
        results = run_query(self.driver, query)
        if results:
            print(f"\n   Top properties by weighted constraints:")
            for r in results:
                print(f"   • {r['id']}: Score {r['score']} | {self.format_price(r['price'])}")
                print(f"     Must-haves: {r['must_have_count']}/3 | Nice-to-haves: {r['nice_to_have_count']}/3")
                print(f"     Location: {r['neighborhood']}")
    
    def demo_exclusion_search(self):
        """Demonstrate exclusion-based searches"""
        
        print("\n1. AVOIDING UNWANTED FEATURES")
        print("   Finding family-friendly properties (no party features)...")
        
        query = """
        MATCH (p:Property)
        WHERE p.bedrooms >= 3
        AND NOT EXISTS {
            MATCH (p)-[:HAS_FEATURE]->(f:Feature)
            WHERE f.name IN ['Wine Cellar', 'Home Theater', 'Bar']
        }
        AND EXISTS {
            MATCH (p)-[:HAS_FEATURE]->(f:Feature)
            WHERE f.category = 'Outdoor' 
            AND f.name IN ['Garden', 'Backyard', 'Patio']
        }
        OPTIONAL MATCH (p)-[:LOCATED_IN]->(n:Neighborhood)
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(feat:Feature)
        WITH p, n, COLLECT(DISTINCT feat.name) as features
        RETURN 
            p.listing_id as id,
            p.price as price,
            n.name as neighborhood,
            p.bedrooms as beds,
            features[0..5] as sample_features
        ORDER BY p.bedrooms DESC, p.price ASC
        LIMIT 5
        """
        
        results = run_query(self.driver, query)
        if results:
            print(f"\n   Found family-friendly properties without party features:")
            for r in results:
                print(f"   • {r['id']}: {r['beds']}BR | {self.format_price(r['price'])}")
                print(f"     Location: {r['neighborhood']}")
                print(f"     Features: {', '.join(r['sample_features'][:3])}...")
        
        print("\n2. AVOIDING SPECIFIC NEIGHBORHOODS")
        print("   Finding properties outside of expensive areas...")
        
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WHERE NOT n.name IN ['Sf-PacificHeights', 'Sf-Presidio', 'Sf-NobHill']
        WITH n, AVG(p.price) as avg_price, COUNT(p) as count
        WHERE count >= 5
        RETURN 
            n.name as neighborhood,
            n.city as city,
            count as properties,
            avg_price
        ORDER BY avg_price ASC
        LIMIT 5
        """
        
        results = run_query(self.driver, query)
        if results:
            print(f"\n   More affordable neighborhoods:")
            for r in results:
                print(f"   • {r['neighborhood']}: {r['properties']} properties")
                print(f"     Average: {self.format_price(r['avg_price'])}")
    
    def demo_multi_hop_paths(self):
        """Demonstrate multi-hop relationship path searches"""
        
        print("\n1. PROPERTIES CONNECTED THROUGH SHARED FEATURES")
        print("   Finding properties with 3+ features in common...")
        
        query = """
        MATCH (p1:Property)-[:HAS_FEATURE]->(f:Feature)<-[:HAS_FEATURE]-(p2:Property)
        WHERE p1.listing_id < p2.listing_id
        WITH p1, p2, COLLECT(DISTINCT f.name) as shared_features
        WHERE SIZE(shared_features) >= 3
        OPTIONAL MATCH (p1)-[:LOCATED_IN]->(n1:Neighborhood)
        OPTIONAL MATCH (p2)-[:LOCATED_IN]->(n2:Neighborhood)
        RETURN 
            p1.listing_id as prop1,
            p2.listing_id as prop2,
            n1.name as hood1,
            n2.name as hood2,
            SIZE(shared_features) as common_features,
            shared_features[0..3] as sample_features,
            ABS(p1.price - p2.price) as price_diff
        ORDER BY common_features DESC, price_diff ASC
        LIMIT 5
        """
        
        results = run_query(self.driver, query)
        if results:
            print(f"\n   Property pairs with strong feature overlap:")
            for r in results:
                print(f"   • {r['prop1']} ↔ {r['prop2']}: {r['common_features']} shared features")
                print(f"     Locations: {r['hood1']} ↔ {r['hood2']}")
                print(f"     Price difference: {self.format_price(r['price_diff'])}")
                print(f"     Shared: {', '.join(r['sample_features'])}...")
        
        print("\n2. NEIGHBORHOOD CONNECTIVITY PATHS")
        print("   Finding properties in well-connected neighborhoods...")
        
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        OPTIONAL MATCH (n)-[:NEAR]-(connected:Neighborhood)
        WITH p, n, COUNT(DISTINCT connected) as connections
        WHERE connections >= 2
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
        WITH p, n, connections, COUNT(DISTINCT f) as feature_count
        RETURN 
            p.listing_id as id,
            n.name as neighborhood,
            connections as nearby_neighborhoods,
            feature_count,
            p.price as price
        ORDER BY connections DESC, feature_count DESC
        LIMIT 5
        """
        
        results = run_query(self.driver, query)
        if results:
            print(f"\n   Properties in well-connected areas:")
            for r in results:
                print(f"   • {r['id']}: {r['neighborhood']}")
                print(f"     Connected to {r['nearby_neighborhoods']} neighborhoods")
                print(f"     {r['feature_count']} features | {self.format_price(r['price'])}")
    
    def demo_boolean_logic_search(self):
        """Demonstrate complex boolean logic searches"""
        
        print("\n1. COMPLEX AND/OR COMBINATIONS")
        print("   (Ocean View OR Bay View) AND (Modern Kitchen OR Updated) AND NOT Condo...")
        
        query = """
        MATCH (p:Property)
        WHERE p.property_type <> 'Condo'
        AND EXISTS {
            MATCH (p)-[:HAS_FEATURE]->(f:Feature)
            WHERE f.name IN ['Ocean View', 'Bay View', 'Water View']
        }
        AND EXISTS {
            MATCH (p)-[:HAS_FEATURE]->(f:Feature)
            WHERE f.name IN ['Modern Kitchen', 'Updated Kitchen', 'Chef Kitchen']
        }
        OPTIONAL MATCH (p)-[:LOCATED_IN]->(n:Neighborhood)
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(feat:Feature)
        WHERE feat.category = 'View'
        WITH p, n, COLLECT(DISTINCT feat.name) as views
        RETURN 
            p.listing_id as id,
            p.property_type as type,
            p.price as price,
            n.name as neighborhood,
            views
        ORDER BY p.price DESC
        LIMIT 5
        """
        
        results = run_query(self.driver, query)
        if results:
            print(f"\n   Properties matching complex criteria:")
            for r in results:
                print(f"   • {r['id']}: {r['type']} | {self.format_price(r['price'])}")
                print(f"     Location: {r['neighborhood']}")
                print(f"     Views: {', '.join(r['views']) if r['views'] else 'N/A'}")
        
        print("\n2. NESTED BOOLEAN LOGIC")
        print("   ((Luxury AND Downtown) OR (Affordable AND Family)) properties...")
        
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WHERE (
            // Luxury Downtown option
            (p.price > 2000000 AND n.city = 'San Francisco' 
             AND EXISTS {
                MATCH (p)-[:HAS_FEATURE]->(f:Feature)
                WHERE f.category = 'Luxury'
             })
        ) OR (
            // Affordable Family option
            (p.price < 1000000 AND p.bedrooms >= 3
             AND EXISTS {
                MATCH (p)-[:HAS_FEATURE]->(f:Feature)
                WHERE f.name IN ['Garden', 'Backyard', 'Family Room']
             })
        )
        WITH p, n,
             CASE 
                WHEN p.price > 2000000 THEN 'Luxury Downtown'
                ELSE 'Affordable Family'
             END as category
        RETURN 
            p.listing_id as id,
            category,
            p.price as price,
            n.name as neighborhood,
            p.bedrooms as beds
        ORDER BY category, p.price DESC
        LIMIT 6
        """
        
        results = run_query(self.driver, query)
        if results:
            print(f"\n   Properties in two distinct categories:")
            current_category = None
            for r in results:
                if current_category != r['category']:
                    current_category = r['category']
                    print(f"\n   {current_category}:")
                print(f"   • {r['id']}: {r['beds']}BR | {self.format_price(r['price'])}")
                print(f"     Location: {r['neighborhood']}")
    
    def demo_shortest_paths(self):
        """Demonstrate shortest path analysis between properties"""
        
        print("\n1. SHORTEST PATH THROUGH SIMILARITIES")
        print("   Finding connection paths between dissimilar properties...")
        
        # First, get two very different properties
        query = """
        MATCH (luxury:Property)
        WHERE luxury.price > 3000000
        WITH luxury
        ORDER BY luxury.price DESC
        LIMIT 1
        MATCH (affordable:Property)
        WHERE affordable.price < 800000
        WITH luxury, affordable
        ORDER BY affordable.price ASC
        LIMIT 1
        MATCH path = shortestPath((luxury)-[:SIMILAR_TO*..5]-(affordable))
        WITH luxury, affordable, path, 
             [n IN nodes(path) | n.listing_id] as property_chain,
             [n IN nodes(path) | n.price] as price_chain
        RETURN 
            luxury.listing_id as luxury_id,
            luxury.price as luxury_price,
            affordable.listing_id as affordable_id,
            affordable.price as affordable_price,
            LENGTH(path) as hops,
            property_chain,
            price_chain
        LIMIT 1
        """
        
        results = run_query(self.driver, query)
        if results and len(results) > 0:
            r = results[0]
            print(f"\n   Path from luxury to affordable property:")
            print(f"   Start: {r['luxury_id']} ({self.format_price(r['luxury_price'])})")
            print(f"   End: {r['affordable_id']} ({self.format_price(r['affordable_price'])})")
            print(f"   Hops: {r['hops']}")
            if r['property_chain']:
                print(f"   Path: {' → '.join(r['property_chain'][:5])}")
        else:
            print("   No path found between luxury and affordable properties")
        
        print("\n2. FEATURE-BASED SHORTEST PATHS")
        print("   Properties connected through feature chains...")
        
        query = """
        MATCH (p1:Property {listing_id: 'SF-100'})
        MATCH (p2:Property {listing_id: 'SF-200'})
        OPTIONAL MATCH path = shortestPath((p1)-[:HAS_FEATURE|SIMILAR_TO*..6]-(p2))
        WITH p1, p2, path,
             [n IN nodes(path) WHERE n:Property | n.listing_id] as properties,
             [n IN nodes(path) WHERE n:Feature | n.name] as features
        WHERE path IS NOT NULL
        RETURN 
            p1.listing_id as start,
            p2.listing_id as end,
            LENGTH(path) as path_length,
            SIZE(properties) as properties_in_path,
            SIZE(features) as features_in_path,
            features[0..3] as sample_features
        LIMIT 1
        """
        
        results = run_query(self.driver, query)
        if results and len(results) > 0:
            r = results[0]
            print(f"\n   Feature connection path:")
            print(f"   {r['start']} → {r['end']}")
            print(f"   Path length: {r['path_length']} hops")
            print(f"   Properties: {r['properties_in_path']}, Features: {r['features_in_path']}")
            if r['sample_features']:
                print(f"   Via features: {', '.join(r['sample_features'])}...")
    
    def demo_community_detection(self):
        """Demonstrate community detection and clustering"""
        
        print("\n1. SIMILARITY-BASED COMMUNITIES")
        print("   Identifying tightly connected property clusters...")
        
        query = """
        MATCH (p:Property)-[s:SIMILAR_TO]-(other:Property)
        WHERE s.overall_score > 0.85
        WITH p, COUNT(DISTINCT other) as connections, 
             COLLECT(DISTINCT other.listing_id)[0..3] as connected_to,
             AVG(s.overall_score) as avg_similarity
        WHERE connections >= 3
        OPTIONAL MATCH (p)-[:LOCATED_IN]->(n:Neighborhood)
        RETURN 
            p.listing_id as id,
            n.name as neighborhood,
            connections,
            ROUND(avg_similarity * 100) / 100 as avg_sim,
            connected_to
        ORDER BY connections DESC, avg_similarity DESC
        LIMIT 5
        """
        
        results = run_query(self.driver, query)
        if results:
            print(f"\n   Properties at the center of similarity clusters:")
            for r in results:
                print(f"   • {r['id']}: Hub with {r['connections']} connections")
                print(f"     Location: {r['neighborhood']}")
                print(f"     Avg similarity: {r['avg_sim']:.2f}")
                print(f"     Connected to: {', '.join(r['connected_to'])}...")
        
        print("\n2. FEATURE-BASED COMMUNITIES")
        print("   Properties forming communities through shared features...")
        
        query = """
        MATCH (p1:Property)-[:HAS_FEATURE]->(f:Feature)<-[:HAS_FEATURE]-(p2:Property)
        WHERE f.category IN ['Luxury', 'View']
        WITH f, COLLECT(DISTINCT p1) as properties
        WHERE SIZE(properties) >= 5
        WITH f.name as feature, 
             SIZE(properties) as property_count,
             [p IN properties | p.listing_id][0..5] as sample_properties,
             AVG([p IN properties | p.price]) as avg_price
        RETURN 
            feature,
            property_count,
            ROUND(avg_price) as avg_price,
            sample_properties
        ORDER BY property_count DESC
        LIMIT 5
        """
        
        results = run_query(self.driver, query)
        if results:
            print(f"\n   Feature communities (properties sharing luxury/view features):")
            for r in results:
                print(f"   • '{r['feature']}': {r['property_count']} properties")
                print(f"     Avg price: {self.format_price(r['avg_price'])}")
                print(f"     Members: {', '.join(r['sample_properties'][:3])}...")
    
    def demo_recommendation_chains(self):
        """Demonstrate recommendation chains through properties"""
        
        print("\n1. UPGRADE PATH RECOMMENDATIONS")
        print("   Finding property upgrade paths based on features...")
        
        query = """
        MATCH (start:Property)
        WHERE start.price < 1000000
        MATCH (start)-[:HAS_FEATURE]->(f1:Feature)
        MATCH (mid:Property)-[:HAS_FEATURE]->(f1)
        WHERE mid.price > start.price * 1.2 
          AND mid.price < start.price * 2
        MATCH (mid)-[:HAS_FEATURE]->(f2:Feature)
        WHERE NOT (start)-[:HAS_FEATURE]->(f2)
        MATCH (end:Property)-[:HAS_FEATURE]->(f2)
        WHERE end.price > mid.price * 1.2
          AND end.price < mid.price * 2
        WITH start, mid, end,
             COLLECT(DISTINCT f1.name)[0..2] as shared_with_mid,
             COLLECT(DISTINCT f2.name)[0..2] as new_in_end
        RETURN 
            start.listing_id as starter_home,
            start.price as starter_price,
            mid.listing_id as upgrade_1,
            mid.price as mid_price,
            end.listing_id as upgrade_2,
            end.price as end_price,
            shared_with_mid,
            new_in_end
        ORDER BY start.price ASC
        LIMIT 3
        """
        
        results = run_query(self.driver, query)
        if results:
            print(f"\n   Property upgrade paths:")
            for i, r in enumerate(results, 1):
                print(f"\n   Path {i}:")
                print(f"   • Start: {r['starter_home']} ({self.format_price(r['starter_price'])})")
                print(f"   • Step 1: {r['upgrade_1']} ({self.format_price(r['mid_price'])})")
                print(f"     Shares: {', '.join(r['shared_with_mid'][:2]) if r['shared_with_mid'] else 'N/A'}")
                print(f"   • Step 2: {r['upgrade_2']} ({self.format_price(r['end_price'])})")
                print(f"     Adds: {', '.join(r['new_in_end'][:2]) if r['new_in_end'] else 'N/A'}")
        
        print("\n2. LATERAL MOVE RECOMMENDATIONS")
        print("   Finding similar properties in different neighborhoods...")
        
        query = """
        MATCH (source:Property)-[:LOCATED_IN]->(n1:Neighborhood)
        WHERE source.listing_id IN ['SF-100', 'SF-101', 'SF-102']
        MATCH (source)-[sim:SIMILAR_TO]-(target:Property)-[:LOCATED_IN]->(n2:Neighborhood)
        WHERE n1 <> n2
          AND sim.overall_score > 0.8
        WITH source, target, n1, n2, sim.overall_score as similarity
        ORDER BY source.listing_id, similarity DESC
        WITH source.listing_id as source_id,
             n1.name as source_hood,
             COLLECT({
                id: target.listing_id,
                hood: n2.name,
                sim: ROUND(similarity * 100) / 100
             })[0..2] as recommendations
        RETURN source_id, source_hood, recommendations
        LIMIT 3
        """
        
        results = run_query(self.driver, query)
        if results:
            print(f"\n   Lateral move recommendations (similar properties, different areas):")
            for r in results:
                print(f"\n   From {r['source_id']} in {r['source_hood']}:")
                for rec in r['recommendations']:
                    print(f"   • {rec['id']} in {rec['hood']} (similarity: {rec['sim']})")
    
    def close(self):
        """Clean up database connection"""
        close_neo4j_driver(self.driver)


def main():
    """Main execution function"""
    demo = AdvancedPathSearchDemo()
    
    try:
        print("\n" + "="*80)
        print(" ADVANCED PATH-BASED AND CONSTRAINT SEARCH DEMONSTRATION")
        print(" Showcasing complex graph queries beyond simple similarity")
        print("="*80)
        
        demo.run_all_demos()
        
        print("\n" + "="*80)
        print(" DEMONSTRATION COMPLETE")
        print(" These advanced searches show the unique power of graph databases")
        print(" for complex, multi-dimensional property discovery")
        print("="*80 + "\n")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()
    finally:
        demo.close()


if __name__ == "__main__":
    main()