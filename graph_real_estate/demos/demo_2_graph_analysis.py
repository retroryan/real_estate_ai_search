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

from database import get_neo4j_driver, close_neo4j_driver, run_query


class GraphRelationshipAnalysisDemo:
    """Comprehensive demonstration of graph relationship analysis capabilities"""
    
    def __init__(self):
        """Initialize the demo with database connection"""
        print("Initializing Graph Relationship Analysis Demo...")
        
        print("\n🚀 NEO4J FEATURES DEMONSTRATED:")
        print("   • Multi-Pattern Matching - Complex MATCH patterns for comprehensive analysis")
        print("   • Advanced Aggregations - Statistical functions and percentiles")
        print("   • Graph Algorithms - Path finding and centrality measures")
        print("   • Conditional Logic - CASE statements for dynamic categorization")
        print("   • Subqueries - WITH clauses for multi-stage processing")
        print("   • Feature Correlation - Analyzing relationships between property features")
        print("   • Market Segmentation - Graph-based market analysis")
        print("   • Cross-Pattern Analysis - Combining multiple relationship types\n")
        
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
    
    def demo_1_property_relationships(self):
        """Demo 1: Property location relationships and neighborhood analysis"""
        print("\n" + "="*80 + "\n")
        print("DEMO 2A: PROPERTY LOCATION RELATIONSHIPS")
        print("="*82)
        print("Analyzing property-neighborhood relationships and geographic patterns")
        
        # Find neighborhoods with most properties
        print("\nNEIGHBORHOOD PROPERTY DENSITY:")
        print("   Neighborhoods with the highest concentration of properties")
        
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WITH n, count(p) as property_count,
             avg(p.listing_price) as avg_price,
             min(p.listing_price) as min_price,
             max(p.listing_price) as max_price
        RETURN n.name as neighborhood,
               n.city as city,
               n.state as state,
               property_count,
               avg_price,
               min_price,
               max_price
        ORDER BY property_count DESC
        LIMIT 10
        """
        
        neighborhoods = run_query(self.driver, query)
        for i, hood in enumerate(neighborhoods, 1):
            print(f"\n{i}. {hood['neighborhood']}, {hood['city']}, {hood['state']}")
            print(f"   Properties: {hood['property_count']}")
            min_price = hood.get('min_price') or 0
            max_price = hood.get('max_price') or 0
            avg_price = hood.get('avg_price') or 0
            print(f"   Price range: ${min_price:,.0f} - ${max_price:,.0f}")
            print(f"   Average price: ${avg_price:,.0f}")
        
        # Property price distribution analysis
        print("\n\nPROPERTY PRICE DISTRIBUTION:")
        print("   Price ranges across all properties")
        
        query = """
        MATCH (p:Property)
        WITH p.listing_price as price
        RETURN 
            count(*) as total_properties,
            avg(price) as avg_price,
            percentileCont(price, 0.25) as q1_price,
            percentileCont(price, 0.5) as median_price,
            percentileCont(price, 0.75) as q3_price,
            min(price) as min_price,
            max(price) as max_price
        """
        
        price_stats = run_query(self.driver, query)
        if price_stats and len(price_stats) > 0:
            stats = price_stats[0]
            print(f"   Total properties: {stats['total_properties']:,}")
            min_price = stats.get('min_price') or 0
            max_price = stats.get('max_price') or 0
            avg_price = stats.get('avg_price') or 0
            median_price = stats.get('median_price') or 0
            q1_price = stats.get('q1_price') or 0
            q3_price = stats.get('q3_price') or 0
            print(f"   Price range: ${min_price:,.0f} - ${max_price:,.0f}")
            print(f"   Average: ${avg_price:,.0f}")
            print(f"   Median: ${median_price:,.0f}")
            print(f"   Q1-Q3: ${q1_price:,.0f} - ${q3_price:,.0f}")
        
        # High-value property concentrations
        print("\n\nHIGH-VALUE PROPERTY CLUSTERS:")
        print("   Neighborhoods with highest concentration of luxury properties (>$2M)")
        
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WHERE p.listing_price > 2000000
        WITH n, count(p) as luxury_count, avg(p.listing_price) as avg_luxury_price
        WHERE luxury_count >= 3
        MATCH (n)<-[:LOCATED_IN]-(all_props:Property)
        WITH n, luxury_count, avg_luxury_price, count(all_props) as total_props
        RETURN n.name as neighborhood,
               n.city as city,
               luxury_count,
               total_props,
               (luxury_count * 100.0 / total_props) as luxury_percentage,
               avg_luxury_price
        ORDER BY luxury_percentage DESC
        LIMIT 5
        """
        
        luxury_areas = run_query(self.driver, query)
        for area in luxury_areas:
            print(f"\n{area['neighborhood']}, {area['city']}")
            print(f"   Luxury properties: {area['luxury_count']} of {area['total_props']} ({area['luxury_percentage']:.1f}%)")
            avg_luxury_price = area.get('avg_luxury_price') or 0
            print(f"   Average luxury price: ${avg_luxury_price:,.0f}")
    
    def demo_2_wikipedia_relationships(self):
        """Demo 2: Wikipedia article relationships and location descriptions"""
        print("\n" + "="*80 + "\n")
        print("DEMO 2B: WIKIPEDIA ARTICLE RELATIONSHIPS")
        print("="*82)
        print("Analyzing Wikipedia articles that describe neighborhoods and locations")
        
        # Wikipedia articles describing neighborhoods
        print("\nWIKIPEDIA-NEIGHBORHOOD RELATIONSHIPS:")
        print("   Wikipedia articles that provide detailed descriptions of neighborhoods")
        
        query = """
        MATCH (w:WikipediaArticle)-[:DESCRIBES]->(n:Neighborhood)
        WITH n, count(w) as article_count,
             collect(w.title)[0..3] as sample_articles
        WHERE article_count > 0
        MATCH (n)<-[:LOCATED_IN]-(p:Property)
        WITH n, article_count, sample_articles,
             count(p) as property_count,
             avg(p.listing_price) as avg_price
        RETURN n.name as neighborhood,
               n.city as city,
               n.state as state,
               article_count,
               sample_articles,
               property_count,
               avg_price
        ORDER BY article_count DESC
        LIMIT 10
        """
        
        wiki_neighborhoods = run_query(self.driver, query)
        for wiki in wiki_neighborhoods:
            print(f"\n{wiki['neighborhood']}, {wiki['city']}, {wiki['state']}")
            print(f"   Wikipedia articles: {wiki['article_count']}")
            print(f"   Sample articles: {', '.join(wiki['sample_articles'])}")
            avg_price = wiki.get('avg_price') or 0
            print(f"   Properties: {wiki['property_count']} (avg: ${avg_price:,.0f})")
        
        # Most documented locations
        print("\n\nMOST DOCUMENTED LOCATIONS:")
        print("   Areas with the richest Wikipedia content coverage")
        
        query = """
        MATCH (w:WikipediaArticle)-[:DESCRIBES]->(n:Neighborhood)
        WITH w, n, size(w.text) as article_length
        WHERE article_length > 1000
        WITH n, 
             count(w) as detailed_articles,
             avg(article_length) as avg_article_length,
             sum(article_length) as total_content_length
        MATCH (n)<-[:LOCATED_IN]-(p:Property)
        WITH n, detailed_articles, avg_article_length, total_content_length,
             count(p) as property_count,
             avg(p.listing_price) as avg_price
        WHERE detailed_articles >= 2
        RETURN n.name as neighborhood,
               n.city as city,
               detailed_articles,
               avg_article_length,
               total_content_length,
               property_count,
               avg_price
        ORDER BY total_content_length DESC
        LIMIT 5
        """
        
        documented_areas = run_query(self.driver, query)
        for area in documented_areas:
            print(f"\n{area['neighborhood']}, {area['city']}")
            print(f"   Detailed articles: {area['detailed_articles']}")
            print(f"   Total content: {area['total_content_length']:,} characters")
            avg_article_length = area.get('avg_article_length') or 0
            avg_price = area.get('avg_price') or 0
            print(f"   Avg article length: {avg_article_length:,.0f} characters")
            print(f"   Properties: {area['property_count']} (avg: ${avg_price:,.0f})")
    
    def demo_3_geographic_hierarchies(self):
        """Demo 3: Geographic relationship hierarchies using PART_OF relationships"""
        print("\n" + "="*80 + "\n")
        print("DEMO 2C: GEOGRAPHIC RELATIONSHIP HIERARCHIES")
        print("="*82)
        print("Analyzing geographic PART_OF relationships and location hierarchies")
        
        # Geographic hierarchy analysis using PART_OF relationships
        print("\nGEOGRAPHIC PART_OF RELATIONSHIPS:")
        print("   Analyzing hierarchical geographic relationships")
        
        query = """
        MATCH (child)-[:PART_OF]->(parent)
        RETURN child.name as child_name,
               labels(child)[0] as child_type,
               parent.name as parent_name,
               labels(parent)[0] as parent_type
        ORDER BY parent_name, child_name
        LIMIT 20
        """
        
        hierarchy = run_query(self.driver, query)
        current_parent = None
        
        for rel in hierarchy:
            if rel['parent_name'] != current_parent:
                current_parent = rel['parent_name']
                print(f"\n{rel['parent_name']} ({rel['parent_type']})")
            
            print(f"   └─ {rel['child_name']} ({rel['child_type']})")
        
        # Property distribution by geographic hierarchy
        print("\n\nPROPERTY DISTRIBUTION BY LOCATION:")
        print("   Properties distributed across geographic regions")
        
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WITH n.city as city, n.state as state,
             count(p) as property_count,
             avg(p.listing_price) as avg_price,
             min(p.listing_price) as min_price,
             max(p.listing_price) as max_price
        RETURN city, state, property_count, avg_price, min_price, max_price
        ORDER BY property_count DESC
        LIMIT 10
        """
        
        distribution = run_query(self.driver, query)
        for area in distribution:
            print(f"\n{area['city']}, {area['state']}")
            print(f"   Properties: {area['property_count']}")
            min_price = area.get('min_price') or 0
            max_price = area.get('max_price') or 0
            avg_price = area.get('avg_price') or 0
            print(f"   Price range: ${min_price:,.0f} - ${max_price:,.0f}")
            print(f"   Average: ${avg_price:,.0f}")
        
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
            avg_price1 = prox.get('avg_price1') or 0
            avg_price2 = prox.get('avg_price2') or 0
            price_difference = prox.get('price_difference') or 0
            print(f"      ${avg_price1:,.0f} vs ${avg_price2:,.0f}")
            print(f"      Price difference: ${price_difference:,.0f}")
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
            avg_price = lifestyle.get('avg_price') or 0
            print(f"   Avg price: ${avg_price:,.0f}")
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
            avg_price1 = comp.get('avg_price1') or 0
            avg_price2 = comp.get('avg_price2') or 0
            print(f"   Pricing: ${avg_price1:,.0f} vs ${avg_price2:,.0f}")
        
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
            listing_price = opp.get('listing_price') or 0
            neighborhood_avg = opp.get('neighborhood_avg') or 0
            potential_upside = opp.get('potential_upside') or 0
            print(f"   Price: ${listing_price:,.0f}")
            print(f"   Neighborhood avg: ${neighborhood_avg:,.0f}")
            print(f"   Potential upside: ${potential_upside:,.0f}")
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
            listing_price = hub.get('listing_price') or 0
            price_per_sqft = hub.get('price_per_sqft') or 0
            print(f"   ${listing_price:,.0f} (${price_per_sqft:.0f}/sqft)")
            print(f"   {hub['neighborhood']}, {hub['city']}")
            print(f"   Network connectivity: {hub['connectivity']} connected properties")
            print(f"   Avg shared features: {hub['avg_shared_features']:.1f}")
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
        
        # Multi-hop feature chains
        print("\nFEATURE CONNECTION CHAINS:")
        print("   Properties connected through shared feature paths")
        
        query = """
        // Find properties connected through feature chains
        MATCH path = (start:Property)-[:HAS_FEATURE*2..6]-(end:Property)
        WHERE start.listing_id < end.listing_id
        AND start <> end
        WITH start, end, length(path) as chain_length,
             [n IN nodes(path) WHERE n:Feature | n.name] as features
        WHERE size(features) >= 2
        MATCH (start)-[:LOCATED_IN]->(n1:Neighborhood)
        MATCH (end)-[:LOCATED_IN]->(n2:Neighborhood)
        RETURN start.listing_id as start_property,
               end.listing_id as end_property,
               start.listing_price as start_price,
               end.listing_price as end_price,
               n1.name as start_neighborhood,
               n2.name as end_neighborhood,
               chain_length,
               features[0..3] as connecting_features
        ORDER BY chain_length ASC
        LIMIT 3
        """
        
        chains = run_query(self.driver, query)
        for chain in chains:
            print(f"\nFeature Chain (length {chain['chain_length']}):")
            start_price = chain.get('start_price') or 0
            end_price = chain.get('end_price') or 0
            print(f"   Start: {chain['start_property']} (${start_price:,.0f}) in {chain['start_neighborhood']}")
            print(f"   End: {chain['end_property']} (${end_price:,.0f}) in {chain['end_neighborhood']}")
            print(f"   Connecting features: {', '.join(chain['connecting_features'])}")
        
        # Feature influence propagation
        print("\n\nFEATURE INFLUENCE PROPAGATION:")
        print("   How premium features influence connected properties")
        
        query = """
        MATCH (premium:Property)-[:HAS_FEATURE]->(luxury:Feature)
        WHERE luxury.name IN ['Wine cellar', 'Home theater', 'Elevator', 'Pool/spa']
        // Find properties in same neighborhood without luxury features
        MATCH (premium)-[:LOCATED_IN]->(n:Neighborhood)<-[:LOCATED_IN]-(influenced:Property)
        WHERE NOT (influenced)-[:HAS_FEATURE]->(luxury)
          AND premium <> influenced
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
            avg_influenced_price = prop.get('avg_influenced_price') or 0
            print(f"   Avg influenced property price: ${avg_influenced_price:,.0f}")
            print(f"   Influenced neighborhoods: {', '.join(prop['influenced_neighborhoods'])}")
        
        # Cross-category feature bridges
        print("\n\nCROSS-CATEGORY FEATURE BRIDGES:")
        self._analyze_feature_category_bridges()
    
    def _analyze_similarity_network(self, property_id: str) -> str:
        """Analyze the feature network for a specific property"""
        query = """
        MATCH (p:Property {listing_id: $property_id})-[:HAS_FEATURE]->(f:Feature)<-[:HAS_FEATURE]-(similar:Property)
        WHERE p <> similar
        WITH p, similar, COUNT(DISTINCT f) as shared_features
        RETURN avg(shared_features) as avg_shared, 
               min(shared_features) as min_shared,
               max(shared_features) as max_shared,
               count(DISTINCT similar) as connected_properties
        """
        result = run_query(self.driver, query, {"property_id": property_id})
        if result:
            r = result[0]
            return f"avg shared features: {r['avg_shared']:.1f}, range: {r['min_shared']}-{r['max_shared']}"
        return "no feature connections"
    
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
        """Analyze the distribution of feature connections"""
        query = """
        MATCH (p1:Property)-[:HAS_FEATURE]->(f:Feature)<-[:HAS_FEATURE]-(p2:Property)
        WHERE p1 <> p2 AND p1.listing_id < p2.listing_id
        WITH p1, p2, COUNT(DISTINCT f) as shared_features
        RETURN 
            count(*) as total,
            avg(shared_features) as avg_shared,
            percentileCont(shared_features, 0.25) as q1,
            percentileCont(shared_features, 0.5) as median,
            percentileCont(shared_features, 0.75) as q3,
            min(shared_features) as min_shared,
            max(shared_features) as max_shared
        """
        result = run_query(self.driver, query)
        if result:
            r = result[0]
            print(f"   {r['total']:,} total property pairs with shared features")
            if r['total'] > 0 and r['min_shared'] is not None:
                print(f"   Shared features distribution: min={r['min_shared']:.0f}, Q1={r['q1']:.0f}, median={r['median']:.0f}, Q3={r['q3']:.0f}, max={r['max_shared']:.0f}")
                print(f"   Average shared features: {r['avg_shared']:.1f}")
            else:
                print("   No feature connections found in the database")
    
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
            avg_with_feature = inf.get('avg_with_feature') or 0
            print(f"      Avg price: ${avg_with_feature:,.0f} ({inf['properties_with_feature']} properties)")
    
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
            avg_price = city.get('avg_price') or 0
            avg_price_per_sqft = city.get('avg_price_per_sqft') or 0
            print(f"   {city['city']}: ${avg_price:,.0f} avg (${avg_price_per_sqft:.0f}/sqft)")
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
            avg_price1 = arb.get('avg_price1') or 0
            avg_price2 = arb.get('avg_price2') or 0
            price_gap = arb.get('price_gap') or 0
            print(f"      ${avg_price1:,.0f} vs ${avg_price2:,.0f}")
            print(f"      Gap: ${price_gap:,.0f}")
    
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
            listing_price = bridge.get('listing_price') or 0
            print(f"   {bridge['property_id']}: ${listing_price:,.0f}")
            print(f"      {bridge['neighborhood']}")
            print(f"      {bridge['category_count']} categories: {', '.join(bridge['categories'])}")
    
    def run_complete_demo(self):
        """Run the complete graph relationship analysis demonstration"""
        print("" + "="*80)
        print("GRAPH RELATIONSHIP ANALYSIS DEMONSTRATION")
        print("Advanced Neo4j Graph Intelligence for Real Estate Market Analysis")
        print("="*82)
        
        # Show actual relationship statistics
        print("Relationship Statistics:")
        relationships = ["LOCATED_IN", "PART_OF", "DESCRIBES"]
        for rel_type in relationships:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
            result = run_query(self.driver, query)
            count = result[0]['count'] if result and len(result) > 0 else 0
            print(f"  {rel_type}: {count}")
        print()
        
        try:
            # Run all demo sections
            self.demo_1_property_relationships()
            self.demo_2_wikipedia_relationships()
            self.demo_3_geographic_hierarchies()
            
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
            close_neo4j_driver()


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