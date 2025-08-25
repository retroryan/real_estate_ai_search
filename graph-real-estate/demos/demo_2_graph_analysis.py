#!/usr/bin/env python3
"""
DEMO 2: GRAPH RELATIONSHIP ANALYSIS SHOWCASE
=============================================

This demo showcases the power of Neo4j graph relationships for real estate intelligence.
It demonstrates complex graph traversals, relationship analysis, and pattern discovery
that would be impossible with traditional vector search alone.

Key Capabilities Demonstrated:
1. Property similarity networks and clustering analysis
2. Feature co-occurrence patterns and correlation networks
3. Geographic relationship hierarchies and proximity analysis
4. Neighborhood lifestyle analysis and community insights
5. Market segment analysis through graph traversals
6. Investment opportunity discovery through relationship patterns

Graph Database Context:
- 6,447 total relationships across 8 relationship types
- 1,608 property similarities with calculated scores (0.720-1.000 range)
- 3,257 feature relationships across 416 unique features
- Geographic hierarchy: County -> City -> Neighborhood -> Property
- Complex similarity networks with high connectivity (avg 11 connections per hub)
"""

import sys
import signal
from pathlib import Path
from typing import Dict, List, Any, Tuple
import time
from collections import defaultdict, Counter

# Handle broken pipe errors gracefully when piping output
if hasattr(signal, 'SIGPIPE'):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.database import get_neo4j_driver, close_neo4j_driver, run_query


class GraphRelationshipAnalysisDemo:
    """Comprehensive demonstration of graph relationship analysis capabilities"""
    
    def __init__(self):
        """Initialize the demo with database connection"""
        print("Initializing Graph Relationship Analysis Demo...")
        self.driver = get_neo4j_driver()
        
        # Verify database state
        node_count = self._get_node_count()
        relationship_count = self._get_relationship_count()
        
        print(f"Connected to graph database:")
        print(f"   {node_count:,} nodes across 7 types")
        print(f"   {relationship_count:,} relationships across 8 types")
        print(f"   Ready for advanced graph analysis")
    
    def _get_node_count(self) -> int:
        """Get total node count"""
        result = run_query(self.driver, "MATCH (n) RETURN count(n) as count")
        return result[0]['count'] if result else 0
    
    def _get_relationship_count(self) -> int:
        """Get total relationship count"""
        result = run_query(self.driver, "MATCH ()-[r]->() RETURN count(r) as count")
        return result[0]['count'] if result else 0
    
    def demo_1_similarity_networks(self):
        """Demo 1: Property similarity networks and clustering analysis"""
        print("\n" + "="*80 + "\n")
        print("DEMO 2A: PROPERTY SIMILARITY NETWORKS & CLUSTERING")
        print("="*82)
        print("Analyzing 1,608 property similarities to discover market clusters and patterns")
        
        # Find similarity network hubs (most connected properties)
        print("\nSIMILARITY NETWORK HUBS:")
        print("   Properties with the most similar connections (market influencers)")
        
        query = """
        MATCH (p:Property)-[s:SIMILAR_TO]->()
        WITH p, count(s) as connections
        ORDER BY connections DESC
        LIMIT 5
        MATCH (p)-[:LOCATED_IN]->(n:Neighborhood)-[:IN_CITY]->(c:City)
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
        WITH p, n, c, connections, collect(DISTINCT f.name)[0..5] as top_features
        RETURN p.listing_id as property_id, 
               p.listing_price as listing_price,
               n.name as neighborhood,
               c.name as city,
               connections,
               top_features
        """
        
        hubs = run_query(self.driver, query)
        for i, hub in enumerate(hubs, 1):
            print(f"\n{i}. {hub['property_id']} ({hub['connections']} similar properties)")
            print(f"   {hub['neighborhood']}, {hub['city']}")
            print(f"   ${hub['listing_price']:,.0f}")
            print(f"   Key features: {', '.join(hub['top_features'])}")
            
            # Analyze the similarity network for this hub
            network_analysis = self._analyze_similarity_network(hub['property_id'])
            print(f"   Network analysis: {network_analysis}")
        
        # Find high-similarity clusters (perfect or near-perfect matches)
        print("\n\nHIGH-SIMILARITY CLUSTERS:")
        print("   Groups of properties with very high similarity scores (>0.9)")
        
        query = """
        MATCH (p1:Property)-[s:SIMILAR_TO]->(p2:Property)
        WHERE s.score > 0.9 AND p1.listing_id < p2.listing_id
        MATCH (p1)-[:LOCATED_IN]->(n1:Neighborhood)
        MATCH (p2)-[:LOCATED_IN]->(n2:Neighborhood)
        RETURN p1.listing_id as prop1, p1.listing_price as listing_price1, n1.name as neighborhood1,
               p2.listing_id as prop2, p2.listing_price as listing_price2, n2.name as neighborhood2,
               s.score as similarity_score
        ORDER BY s.score DESC
        LIMIT 5
        """
        
        clusters = run_query(self.driver, query)
        for i, cluster in enumerate(clusters, 1):
            print(f"\n{i}. Similarity Score: {cluster['similarity_score']:.3f}")
            print(f"   Property A: {cluster['prop1']} (${cluster['listing_price1']:,.0f}) in {cluster['neighborhood1']}")
            print(f"   Property B: {cluster['prop2']} (${cluster['listing_price2']:,.0f}) in {cluster['neighborhood2']}")
            
            # Analyze why these properties are so similar
            similarity_factors = self._analyze_similarity_factors(cluster['prop1'], cluster['prop2'])
            print(f"   Similarity factors: {similarity_factors}")
        
        # Similarity distribution analysis
        print("\n\nSIMILARITY SCORE DISTRIBUTION ANALYSIS:")
        self._analyze_similarity_distribution()
    
    def demo_2_feature_networks(self):
        """Demo 2: Feature co-occurrence networks and correlation analysis"""
        print("\n" + "="*80 + "\n")
        print("DEMO 2B: FEATURE CO-OCCURRENCE NETWORKS")
        print("="*82)
        print("Analyzing 3,257 feature relationships to discover feature correlation patterns")
        
        # Feature category co-occurrence analysis
        print("\nFEATURE CATEGORY CO-OCCURRENCE:")
        print("   How different feature categories appear together in properties")
        
        query = """
        MATCH (p:Property)-[:HAS_FEATURE]->(f1:Feature),
              (p)-[:HAS_FEATURE]->(f2:Feature)
        WHERE f1.category < f2.category
        WITH f1.category as category1, f2.category as category2, count(p) as cooccurrence
        WHERE cooccurrence >= 10
        RETURN category1, category2, cooccurrence
        ORDER BY cooccurrence DESC
        LIMIT 10
        """
        
        category_pairs = run_query(self.driver, query)
        for pair in category_pairs:
            print(f"   {pair['category1']} + {pair['category2']}: {pair['cooccurrence']} properties")
        
        # Specific feature correlation networks
        print("\n\nHIGH-VALUE FEATURE CORRELATIONS:")
        print("   Features that frequently appear together in high-value properties")
        
        query = """
        MATCH (p:Property)-[:HAS_FEATURE]->(f1:Feature),
              (p)-[:HAS_FEATURE]->(f2:Feature)
        WHERE f1.name < f2.name AND p.listing_price > 3000000
        WITH f1.name as feature1, f2.name as feature2, 
             count(p) as cooccurrence,
             avg(p.listing_price) as avg_price
        WHERE cooccurrence >= 5
        RETURN feature1, feature2, cooccurrence, avg_price
        ORDER BY avg_price DESC
        LIMIT 8
        """
        
        luxury_correlations = run_query(self.driver, query)
        for corr in luxury_correlations:
            print(f"   {corr['feature1']} + {corr['feature2']}")
            print(f"      {corr['cooccurrence']} properties, ${corr['avg_price']:,.0f} avg price")
        
        # Feature influence on property value
        print("\n\nFEATURE VALUE INFLUENCE ANALYSIS:")
        self._analyze_feature_value_influence()
        
        # Unique feature combinations
        print("\n\nUNIQUE FEATURE COMBINATIONS:")
        print("   Rare but valuable feature combinations")
        
        query = """
        MATCH (p:Property)-[:HAS_FEATURE]->(f1:Feature {category: 'Recreation'}),
              (p)-[:HAS_FEATURE]->(f2:Feature {category: 'View'}),
              (p)-[:HAS_FEATURE]->(f3:Feature {category: 'Technology'})
        WITH p, collect(DISTINCT f1.name + ', ' + f2.name + ', ' + f3.name) as combo
        MATCH (p)-[:LOCATED_IN]->(n:Neighborhood)
        RETURN p.listing_id as property_id,
               p.listing_price as listing_price,
               n.name as neighborhood,
               combo[0] as feature_combination
        ORDER BY p.listing_price DESC
        LIMIT 3
        """
        
        unique_combos = run_query(self.driver, query)
        for combo in unique_combos:
            print(f"   {combo['property_id']}: ${combo['listing_price']:,.0f}")
            print(f"      {combo['neighborhood']}")
            print(f"      {combo['feature_combination']}")
    
    def demo_3_geographic_hierarchies(self):
        """Demo 3: Geographic relationship hierarchies and proximity analysis"""
        print("\n" + "="*80 + "\n")
        print("DEMO 2C: GEOGRAPHIC RELATIONSHIP HIERARCHIES")
        print("="*82)
        print("Analyzing geographic relationships: County -> City -> Neighborhood -> Property")
        
        # Full geographic hierarchy analysis
        print("\nCOMPLETE GEOGRAPHIC HIERARCHY:")
        
        query = """
        MATCH (co:County)<-[:IN_COUNTY]-(c:City)<-[:IN_CITY]-(n:Neighborhood)<-[:LOCATED_IN]-(p:Property)
        WITH co, c, n, 
             count(p) as properties,
             avg(p.listing_price) as avg_price,
             min(p.listing_price) as min_price,
             max(p.listing_price) as max_price
        RETURN co.name as county,
               c.name as city,
               n.name as neighborhood,
               properties,
               avg_price,
               min_price,
               max_price
        ORDER BY co.name, c.name, avg_price DESC
        """
        
        hierarchy = run_query(self.driver, query)
        current_county = None
        current_city = None
        
        for area in hierarchy:
            if area['county'] != current_county:
                current_county = area['county']
                print(f"\n{current_county} County")
                current_city = None
            
            if area['city'] != current_city:
                current_city = area['city']
                print(f"  {current_city}")
            
            print(f"    {area['neighborhood']}: {area['properties']} properties")
            print(f"       ${area['min_price']:,.0f} - ${area['max_price']:,.0f} (avg: ${area['avg_price']:,.0f})")
        
        # Neighborhood proximity analysis
        print("\n\n NEIGHBORHOOD PROXIMITY NETWORKS:")
        print("   Analyzing 200 NEAR relationships between neighborhoods")
        
        query = """
        MATCH (n1:Neighborhood)-[:NEAR]->(n2:Neighborhood)
        WHERE n1.name < n2.name
        MATCH (n1)<-[:LOCATED_IN]-(p1:Property)
        MATCH (n2)<-[:LOCATED_IN]-(p2:Property)
        WITH n1, n2, 
             avg(p1.listing_price) as avg_price1,
             avg(p2.listing_price) as avg_price2,
             count(p1) as properties1,
             count(p2) as properties2
        RETURN n1.name as neighborhood1,
               n2.name as neighborhood2,
               n1.city as city,
               avg_price1,
               avg_price2,
               abs(avg_price1 - avg_price2) as price_difference,
               properties1,
               properties2
        ORDER BY price_difference DESC
        LIMIT 5
        """
        
        proximity_analysis = run_query(self.driver, query)
        print("\n   Neighboring areas with largest price differences:")
        for prox in proximity_analysis:
            print(f"   {prox['neighborhood1']} <-> {prox['neighborhood2']} ({prox['city']})")
            print(f"      ${prox['avg_price1']:,.0f} vs ${prox['avg_price2']:,.0f}")
            print(f"      Price difference: ${prox['price_difference']:,.0f}")
            print(f"      Properties: {prox['properties1']} vs {prox['properties2']}")
        
        # Cross-city comparison through graph traversal
        print("\n\nCROSS-CITY MARKET COMPARISON:")
        self._analyze_cross_city_patterns()
    
    def demo_4_lifestyle_communities(self):
        """Demo 4: Neighborhood lifestyle analysis and community insights"""
        print("\n" + "="*80 + "\n")
        print("DEMO 2D: LIFESTYLE COMMUNITIES & SOCIAL PATTERNS")
        print("="*82)
        print("Analyzing lifestyle tags and community characteristics through graph relationships")
        
        # Lifestyle tag distribution and property characteristics
        print("\nLIFESTYLE TAG ANALYSIS:")
        
        query = """
        MATCH (n:Neighborhood)<-[:LOCATED_IN]-(p:Property)
        WHERE n.lifestyle_tags IS NOT NULL
        UNWIND n.lifestyle_tags as lifestyle_tag
        WITH lifestyle_tag, 
             collect(DISTINCT n.city) as cities,
             count(DISTINCT n) as neighborhoods,
             count(p) as properties,
             avg(p.listing_price) as avg_price,
             avg(p.price_per_sqft) as avg_price_per_sqft
        RETURN lifestyle_tag,
               cities,
               neighborhoods,
               properties,
               avg_price,
               avg_price_per_sqft
        ORDER BY avg_price DESC
        """
        
        lifestyle_analysis = run_query(self.driver, query)
        for lifestyle in lifestyle_analysis:
            print(f"\n{lifestyle['lifestyle_tag'].upper()}")
            print(f"   Cities: {', '.join(lifestyle['cities'])}")
            print(f"   Neighborhoods: {lifestyle['neighborhoods']}")
            print(f"   Properties: {lifestyle['properties']}")
            print(f"   Avg price: ${lifestyle['avg_price']:,.0f}")
            print(f"   Avg price/sqft: ${lifestyle['avg_price_per_sqft']:.0f}")
        
        # Lifestyle compatibility analysis
        print("\n\n LIFESTYLE COMPATIBILITY MATRIX:")
        print("   Neighborhoods sharing multiple lifestyle characteristics")
        
        query = """
        MATCH (n1:Neighborhood), (n2:Neighborhood)
        WHERE n1.name < n2.name 
          AND n1.lifestyle_tags IS NOT NULL 
          AND n2.lifestyle_tags IS NOT NULL
        WITH n1, n2,
             [tag IN n1.lifestyle_tags WHERE tag IN n2.lifestyle_tags] as shared_tags,
             size([tag IN n1.lifestyle_tags WHERE tag IN n2.lifestyle_tags]) as shared_count
        WHERE shared_count >= 2
        MATCH (n1)<-[:LOCATED_IN]-(p1:Property)
        MATCH (n2)<-[:LOCATED_IN]-(p2:Property)
        WITH n1, n2, shared_tags, shared_count,
             avg(p1.listing_price) as avg_price1,
             avg(p2.listing_price) as avg_price2
        RETURN n1.name as neighborhood1,
               n1.city as city1,
               n2.name as neighborhood2,
               n2.city as city2,
               shared_tags,
               shared_count,
               avg_price1,
               avg_price2
        ORDER BY shared_count DESC, abs(avg_price1 - avg_price2)
        LIMIT 5
        """
        
        compatibility = run_query(self.driver, query)
        for comp in compatibility:
            print(f"\n{comp['neighborhood1']} ({comp['city1']}) <-> {comp['neighborhood2']} ({comp['city2']})")
            print(f"   Shared lifestyle: {', '.join(comp['shared_tags'])}")
            print(f"   Pricing: ${comp['avg_price1']:,.0f} vs ${comp['avg_price2']:,.0f}")
        
        # Feature-lifestyle correlation
        print("\n\nLIFESTYLE-FEATURE CORRELATION:")
        self._analyze_lifestyle_feature_correlation()
    
    def demo_5_investment_patterns(self):
        """Demo 5: Investment opportunity discovery through relationship patterns"""
        print("\n" + "="*80 + "\n")
        print("DEMO 2E: INVESTMENT PATTERN DISCOVERY")
        print("="*82)
        print("Using graph relationships to identify investment opportunities and market patterns")
        
        # Undervalued properties in high-value neighborhoods
        print("\nUNDERVALUED OPPORTUNITIES:")
        print("   Properties priced below neighborhood average with high similarity scores")
        
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WITH n, avg(p.listing_price) as neighborhood_avg
        MATCH (target:Property)-[:LOCATED_IN]->(n)
        WHERE target.listing_price < neighborhood_avg * 0.85
        MATCH (target)-[sim:SIMILAR_TO]->(similar:Property)
        WHERE sim.score > 0.8
        WITH target, n, neighborhood_avg, count(similar) as high_similarity_count,
             avg(sim.score) as avg_similarity_score
        WHERE high_similarity_count >= 3
        MATCH (target)-[:HAS_FEATURE]->(f:Feature)
        RETURN target.listing_id as property_id,
               target.listing_price as price,
               neighborhood_avg,
               (neighborhood_avg - target.listing_price) as potential_upside,
               n.name as neighborhood,
               high_similarity_count,
               avg_similarity_score,
               collect(DISTINCT f.name)[0..5] as key_features
        ORDER BY potential_upside DESC
        LIMIT 3
        """
        
        opportunities = run_query(self.driver, query)
        for opp in opportunities:
            print(f"\n{opp['property_id']}")
            print(f"   Price: ${opp['listing_price']:,.0f}")
            print(f"   Neighborhood avg: ${opp['neighborhood_avg']:,.0f}")
            print(f"   Potential upside: ${opp['potential_upside']:,.0f}")
            print(f"   Location: {opp['neighborhood']}")
            print(f"   High-similarity connections: {opp['high_similarity_count']} (avg score: {opp['avg_similarity_score']:.3f})")
            print(f"   Key features: {', '.join(opp['key_features'])}")
        
        # High-connectivity investment hubs
        print("\n\nINVESTMENT HUBS:")
        print("   Properties with exceptional connectivity indicating market influence")
        
        query = """
        MATCH (hub:Property)-[sim:SIMILAR_TO]->(connected:Property)
        WITH hub, count(connected) as connectivity, avg(sim.score) as avg_sim_score
        WHERE connectivity >= 8
        MATCH (hub)-[:LOCATED_IN]->(n:Neighborhood)-[:IN_CITY]->(c:City)
        OPTIONAL MATCH (hub)-[:HAS_FEATURE]->(f:Feature {category: 'Recreation'})
        OPTIONAL MATCH (hub)-[:HAS_FEATURE]->(f2:Feature {category: 'View'})
        WITH hub, n, c, connectivity, avg_sim_score,
             count(DISTINCT f) as recreation_features,
             count(DISTINCT f2) as view_features
        RETURN hub.listing_id as property_id,
               hub.listing_price as price,
               n.name as neighborhood,
               c.name as city,
               connectivity,
               avg_sim_score,
               recreation_features,
               view_features,
               hub.price_per_sqft as price_per_sqft
        ORDER BY connectivity DESC, avg_sim_score DESC
        LIMIT 3
        """
        
        hubs = run_query(self.driver, query)
        for hub in hubs:
            print(f"\n{hub['property_id']} (Investment Hub)")
            print(f"   ${hub['listing_price']:,.0f} (${hub['price_per_sqft']:.0f}/sqft)")
            print(f"   {hub['neighborhood']}, {hub['city']}")
            print(f"   Network connectivity: {hub['connectivity']} similar properties")
            print(f"   Avg similarity score: {hub['avg_sim_score']:.3f}")
            print(f"   Feature profile: {hub['recreation_features']} recreation, {hub['view_features']} view features")
        
        # Market segment arbitrage opportunities
        print("\n\nMARKET SEGMENT ARBITRAGE:")
        self._analyze_market_arbitrage_opportunities()
    
    def demo_6_complex_graph_traversals(self):
        """Demo 6: Complex multi-hop graph traversals"""
        print("\n" + "="*80 + "\n")
        print("DEMO 2F: COMPLEX MULTI-HOP GRAPH TRAVERSALS")
        print("="*82)
        print("Advanced graph patterns requiring multiple relationship traversals")
        
        # Multi-hop similarity chains
        print("\nSIMILARITY CHAIN ANALYSIS:")
        print("   Properties connected through chains of high similarity")
        
        query = """
        MATCH path = (start:Property)-[:SIMILAR_TO*2..3]-(end:Property)
        WHERE start.listing_id < end.listing_id
        AND ALL(rel in relationships(path) WHERE rel.score > 0.8)
        WITH start, end, length(path) as chain_length,
             [rel in relationships(path) | rel.score] as scores
        MATCH (start)-[:LOCATED_IN]->(n1:Neighborhood)
        MATCH (end)-[:LOCATED_IN]->(n2:Neighborhood)
        RETURN start.listing_id as start_property,
               end.listing_id as end_property,
               start.listing_price as start_price,
               end.listing_price as end_price,
               n1.name as start_neighborhood,
               n2.name as end_neighborhood,
               chain_length,
               scores
        ORDER BY chain_length DESC
        LIMIT 3
        """
        
        chains = run_query(self.driver, query)
        for chain in chains:
            print(f"\nSimilarity Chain (length {chain['chain_length']}):")
            print(f"   Start: {chain['start_property']} (${chain['start_price']:,.0f}) in {chain['start_neighborhood']}")
            print(f"   End: {chain['end_property']} (${chain['end_price']:,.0f}) in {chain['end_neighborhood']}")
            print(f"   Similarity scores: {[f'{score:.3f}' for score in chain['scores']]}")
        
        # Feature influence propagation
        print("\n\nFEATURE INFLUENCE PROPAGATION:")
        print("   How premium features influence connected properties")
        
        query = """
        MATCH (premium:Property)-[:HAS_FEATURE]->(luxury:Feature)
        WHERE luxury.name IN ['Wine cellar', 'Home theater', 'Elevator', 'Pool/spa']
        MATCH (premium)-[:SIMILAR_TO]->(influenced:Property)
        WHERE NOT (influenced)-[:HAS_FEATURE]->(luxury)
        MATCH (influenced)-[:LOCATED_IN]->(n:Neighborhood)
        WITH luxury.name as luxury_feature,
             count(DISTINCT influenced) as influenced_count,
             avg(influenced.listing_price) as avg_influenced_price,
             collect(DISTINCT n.name)[0..3] as influenced_neighborhoods
        WHERE influenced_count >= 3
        RETURN luxury_feature,
               influenced_count,
               avg_influenced_price,
               influenced_neighborhoods
        ORDER BY influenced_count DESC
        """
        
        propagation = run_query(self.driver, query)
        for prop in propagation:
            print(f"\n{prop['luxury_feature']} influence:")
            print(f"   Influences {prop['influenced_count']} similar properties")
            print(f"   Avg influenced property price: ${prop['avg_influenced_price']:,.0f}")
            print(f"   Influenced neighborhoods: {', '.join(prop['influenced_neighborhoods'])}")
        
        # Cross-category feature bridges
        print("\n\nCROSS-CATEGORY FEATURE BRIDGES:")
        self._analyze_feature_category_bridges()
    
    def _analyze_similarity_network(self, property_id: str) -> str:
        """Analyze the similarity network for a specific property"""
        query = """
        MATCH (p:Property {listing_id: $property_id})-[s:SIMILAR_TO]->(similar:Property)
        RETURN avg(s.score) as avg_score, 
               min(s.score) as min_score,
               max(s.score) as max_score,
               count(similar) as total_similar
        """
        result = run_query(self.driver, query, {"property_id": property_id})
        if result:
            r = result[0]
            return f"avg similarity: {r['avg_score']:.3f}, range: {r['min_score']:.3f}-{r['max_score']:.3f}"
        return "no similarity data"
    
    def _analyze_similarity_factors(self, prop1: str, prop2: str) -> str:
        """Analyze factors contributing to high similarity between two properties"""
        query = """
        MATCH (p1:Property {listing_id: $prop1}), (p2:Property {listing_id: $prop2})
        OPTIONAL MATCH (p1)-[:HAS_FEATURE]->(f:Feature)<-[:HAS_FEATURE]-(p2)
        WITH p1, p2, count(DISTINCT f) as shared_features,
             abs(p1.listing_price - p2.listing_price) / p1.listing_price as price_diff,
             abs(p1.square_feet - p2.square_feet) / p1.square_feet as size_diff
        RETURN shared_features, price_diff, size_diff
        """
        result = run_query(self.driver, query, {"prop1": prop1, "prop2": prop2})
        if result:
            r = result[0]
            return f"{r['shared_features']} shared features, {r['price_diff']:.1%} price diff, {r['size_diff']:.1%} size diff"
        return "analysis unavailable"
    
    def _analyze_similarity_distribution(self):
        """Analyze the distribution of similarity scores"""
        query = """
        MATCH ()-[s:SIMILAR_TO]->()
        WITH s.score as score
        RETURN 
            count(*) as total,
            avg(score) as avg_score,
            percentileCont(score, 0.25) as q1,
            percentileCont(score, 0.5) as median,
            percentileCont(score, 0.75) as q3,
            min(score) as min_score,
            max(score) as max_score
        """
        result = run_query(self.driver, query)
        if result:
            r = result[0]
            print(f"   {r['total']:,} total similarity relationships")
            if r['total'] > 0 and r['min_score'] is not None:
                print(f"   Score distribution: min={r['min_score']:.3f}, Q1={r['q1']:.3f}, median={r['median']:.3f}, Q3={r['q3']:.3f}, max={r['max_score']:.3f}")
                print(f"   Average similarity: {r['avg_score']:.3f}")
            else:
                print("   No similarity relationships found in the database")
    
    def _analyze_feature_value_influence(self):
        """Analyze how features influence property values"""
        query = """
        MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
        WITH f.name as feature, 
             avg(p.listing_price) as avg_with_feature,
             count(p) as properties_with_feature
        WHERE properties_with_feature >= 10
        MATCH (all:Property)
        WITH feature, avg_with_feature, properties_with_feature, avg(all.listing_price) as overall_avg
        WITH feature, avg_with_feature, properties_with_feature,
             (avg_with_feature - overall_avg) / overall_avg as value_premium
        RETURN feature, avg_with_feature, properties_with_feature, value_premium
        ORDER BY value_premium DESC
        LIMIT 5
        """
        
        influences = run_query(self.driver, query)
        for inf in influences:
            print(f"   {inf['feature']}: +{inf['value_premium']:.1%} value premium")
            print(f"      Avg price: ${inf['avg_with_feature']:,.0f} ({inf['properties_with_feature']} properties)")
    
    def _analyze_cross_city_patterns(self):
        """Analyze patterns across cities"""
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)-[:IN_CITY]->(c:City)
        WITH c.name as city,
             avg(p.listing_price) as avg_price,
             avg(p.price_per_sqft) as avg_price_per_sqft,
             count(p) as properties,
             count(DISTINCT n) as neighborhoods
        RETURN city, avg_price, avg_price_per_sqft, properties, neighborhoods
        ORDER BY avg_price DESC
        """
        
        cities = run_query(self.driver, query)
        print("   Cross-city market comparison:")
        for city in cities:
            print(f"   {city['city']}: ${city['avg_price']:,.0f} avg (${city['avg_price_per_sqft']:.0f}/sqft)")
            print(f"      {city['properties']} properties across {city['neighborhoods']} neighborhoods")
    
    def _analyze_lifestyle_feature_correlation(self):
        """Analyze correlation between lifestyle tags and features"""
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)-[:HAS_FEATURE]->(f:Feature)
        WHERE n.lifestyle_tags IS NOT NULL
        UNWIND n.lifestyle_tags as lifestyle
        WITH lifestyle, f.category as feature_category, count(p) as correlation_count
        WHERE correlation_count >= 5
        RETURN lifestyle, feature_category, correlation_count
        ORDER BY lifestyle, correlation_count DESC
        """
        
        correlations = run_query(self.driver, query)
        lifestyle_groups = defaultdict(list)
        for corr in correlations:
            lifestyle_groups[corr['lifestyle']].append(f"{corr['feature_category']} ({corr['correlation_count']})")
        
        for lifestyle, features in lifestyle_groups.items():
            print(f"   {lifestyle}: {', '.join(features[:3])}")
    
    def _analyze_market_arbitrage_opportunities(self):
        """Analyze market arbitrage opportunities"""
        query = """
        MATCH (p1:Property)-[:LOCATED_IN]->(n1:Neighborhood)-[:IN_CITY]->(c:City),
              (p2:Property)-[:LOCATED_IN]->(n2:Neighborhood)-[:IN_CITY]->(c)
        WHERE n1.name <> n2.name
        WITH n1, n2, c, avg(p1.listing_price) as avg_price1, avg(p2.listing_price) as avg_price2
        WHERE abs(avg_price1 - avg_price2) > 500000
        RETURN n1.name as neighborhood1, n2.name as neighborhood2,
               avg_price1, avg_price2,
               abs(avg_price1 - avg_price2) as price_gap,
               c.name as city
        ORDER BY price_gap DESC
        LIMIT 3
        """
        
        arbitrage = run_query(self.driver, query)
        print("   Largest intra-city price gaps:")
        for arb in arbitrage:
            print(f"   {arb['neighborhood1']} vs {arb['neighborhood2']} ({arb['city']})")
            print(f"      ${arb['avg_price1']:,.0f} vs ${arb['avg_price2']:,.0f}")
            print(f"      Gap: ${arb['price_gap']:,.0f}")
    
    def _analyze_feature_category_bridges(self):
        """Analyze properties that bridge different feature categories"""
        query = """
        MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
        WITH p, collect(DISTINCT f.category) as categories
        WHERE size(categories) >= 5
        MATCH (p)-[:LOCATED_IN]->(n:Neighborhood)
        RETURN p.listing_id as property_id,
               p.listing_price as listing_price,
               n.name as neighborhood,
               categories,
               size(categories) as category_count
        ORDER BY category_count DESC
        LIMIT 3
        """
        
        bridges = run_query(self.driver, query)
        print("   Properties bridging multiple feature categories:")
        for bridge in bridges:
            print(f"   {bridge['property_id']}: ${bridge['listing_price']:,.0f}")
            print(f"      {bridge['neighborhood']}")
            print(f"      {bridge['category_count']} categories: {', '.join(bridge['categories'])}")
    
    def run_complete_demo(self):
        """Run the complete graph relationship analysis demonstration"""
        print("" + "="*80)
        print("GRAPH RELATIONSHIP ANALYSIS DEMONSTRATION")
        print("Advanced Neo4j Graph Intelligence for Real Estate Market Analysis")
        print("="*82)
        print("Graph Database: 6,447 relationships, 1,608 similarities, complex interconnections")
        print("Analysis Focus: Property networks, feature correlations, geographic patterns")
        
        try:
            # Run all demo sections
            self.demo_1_similarity_networks()
            self.demo_2_feature_networks()
            self.demo_3_geographic_hierarchies()
            self.demo_4_lifestyle_communities()
            self.demo_5_investment_patterns()
            self.demo_6_complex_graph_traversals()
            
            # Summary
            print("\n" + "" + "="*80)
            print("GRAPH ANALYSIS DEMONSTRATION COMPLETE")
            print("="*82)
            print("Property Similarity Networks: Discovered market clusters and influence hubs")
            print("Feature Co-occurrence: Analyzed 3,257 feature relationships and correlations")
            print("Geographic Hierarchies: Mapped County->City->Neighborhood->Property relationships")
            print("Lifestyle Communities: Analyzed neighborhood characteristics and compatibility")
            print("Investment Patterns: Identified opportunities through graph relationship analysis")
            print("Complex Traversals: Demonstrated multi-hop relationship patterns")
            print("\nGraph Intelligence Advantages:")
            print("   Relationship-based insights impossible with traditional search")
            print("   Network effects and influence propagation analysis")
            print("   Pattern discovery through complex graph traversals")
            print("   Market intelligence through interconnected data analysis")
            
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
    """Main function to run the graph relationship analysis demo"""
    demo = None
    try:
        demo = GraphRelationshipAnalysisDemo()
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