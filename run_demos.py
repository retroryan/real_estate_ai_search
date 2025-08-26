#!/usr/bin/env python3
"""
Working demo runner that bypasses import issues.
Run this from the project root to test all demo functionality.
"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from typing import List, Dict, Any

load_dotenv()

class DemoRunner:
    """Run graph database demos without import issues."""
    
    def __init__(self):
        """Initialize Neo4j connection."""
        self.driver = GraphDatabase.driver(
            'bolt://localhost:7687', 
            auth=('neo4j', os.getenv('NEO4J_PASSWORD'))
        )
    
    def run_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results."""
        with self.driver.session() as session:
            result = session.run(query)
            return list(result)
    
    def close(self):
        """Close database connection."""
        self.driver.close()
    
    def demo_1_property_search(self):
        """Demo 1: Basic Property Search"""
        print("\n" + "="*60)
        print("DEMO 1: Property Search & Filtering")
        print("="*60)
        
        print("\n🔍 Search: 3+ bedroom properties under $1M in San Francisco")
        query = """
        MATCH (p:Property)
        WHERE p.bedrooms >= 3 
          AND p.listing_price < 1000000
          AND p.city_normalized = 'San Francisco'
        OPTIONAL MATCH (p)-[:LOCATED_IN]->(n:Neighborhood)
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
        WITH p, n.name as neighborhood, collect(DISTINCT f.name)[0..5] as features
        RETURN p.listing_id as id, 
               p.listing_price as price,
               p.bedrooms as beds,
               p.bathrooms as baths,
               p.square_feet as sqft,
               neighborhood,
               features
        ORDER BY p.listing_price ASC
        LIMIT 5
        """
        
        results = self.run_query(query)
        
        if results:
            print(f"\n✅ Found {len(results)} matching properties:\n")
            for r in results:
                print(f"📍 {r['id']}")
                print(f"   💰 ${r['price']:,.0f}")
                print(f"   🏠 {r['beds']} bed / {r['baths']} bath / {r['sqft']:,.0f} sqft")
                if r['neighborhood']:
                    print(f"   📌 {r['neighborhood']}")
                if r['features']:
                    print(f"   ✨ Features: {', '.join(r['features'][:3])}")
                print()
        else:
            print("No properties found matching criteria")
    
    def demo_2_neighborhood_analysis(self):
        """Demo 2: Neighborhood Analysis"""
        print("\n" + "="*60)
        print("DEMO 2: Neighborhood Market Analysis")
        print("="*60)
        
        query = """
        MATCH (n:Neighborhood)<-[:LOCATED_IN]-(p:Property)
        WITH n.name as neighborhood,
             count(p) as property_count,
             avg(p.listing_price) as avg_price,
             avg(p.square_feet) as avg_sqft,
             avg(p.price_per_sqft) as avg_psf,
             collect(DISTINCT p.property_type_normalized)[0..3] as property_types
        WHERE property_count >= 5
        RETURN neighborhood, 
               property_count, 
               avg_price, 
               avg_sqft,
               avg_psf,
               property_types
        ORDER BY avg_price DESC
        LIMIT 5
        """
        
        results = self.run_query(query)
        
        if results:
            print("\n📊 Top Neighborhoods by Average Price:\n")
            for i, r in enumerate(results, 1):
                print(f"{i}. {r['neighborhood']}")
                print(f"   • Properties: {r['property_count']}")
                print(f"   • Avg Price: ${r['avg_price']:,.0f}")
                print(f"   • Avg Size: {r['avg_sqft']:,.0f} sqft")
                if r['avg_psf']:
                    print(f"   • Price/sqft: ${r['avg_psf']:,.2f}")
                if r['property_types']:
                    print(f"   • Types: {', '.join(r['property_types'])}")
                print()
        else:
            print("No neighborhood data available")
    
    def demo_3_feature_analysis(self):
        """Demo 3: Feature Impact on Pricing"""
        print("\n" + "="*60)
        print("DEMO 3: Feature Impact Analysis")
        print("="*60)
        
        query = """
        MATCH (f:Feature)<-[:HAS_FEATURE]-(p:Property)
        WITH f.name as feature,
             count(p) as property_count,
             avg(p.listing_price) as avg_price,
             min(p.listing_price) as min_price,
             max(p.listing_price) as max_price
        WHERE property_count >= 20
        RETURN feature, property_count, avg_price, min_price, max_price
        ORDER BY avg_price DESC
        LIMIT 10
        """
        
        results = self.run_query(query)
        
        if results:
            print("\n💎 Top Features by Average Property Price:\n")
            for i, r in enumerate(results, 1):
                print(f"{i}. {r['feature'].title()}")
                print(f"   • Found in: {r['property_count']} properties")
                print(f"   • Avg Price: ${r['avg_price']:,.0f}")
                print(f"   • Price Range: ${r['min_price']:,.0f} - ${r['max_price']:,.0f}")
                print()
        else:
            print("No feature data available")
    
    def demo_4_property_connections(self):
        """Demo 4: Property Connection Graph"""
        print("\n" + "="*60)
        print("DEMO 4: Property Relationship Graph")
        print("="*60)
        
        # Find a property with multiple relationships
        query = """
        MATCH (p:Property {listing_id: 'prop-oak-125'})
        OPTIONAL MATCH (p)-[:LOCATED_IN]->(n:Neighborhood)
        OPTIONAL MATCH (p)-[:IN_ZIP_CODE]->(z:ZipCode)
        OPTIONAL MATCH (p)-[:TYPE_OF]->(pt:PropertyType)
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
        RETURN p.listing_id as id,
               p.listing_price as price,
               n.name as neighborhood,
               z.id as zip_code,
               pt.name as property_type,
               collect(DISTINCT f.name)[0..10] as features
        """
        
        results = self.run_query(query)
        
        if results and results[0]:
            r = results[0]
            print(f"\n🏡 Property Graph for {r['id']}:\n")
            print(f"📊 Base Information:")
            print(f"   • Price: ${r['price']:,.0f}")
            print(f"\n🔗 Relationships:")
            print(f"   • Located in: {r['neighborhood'] or 'N/A'}")
            print(f"   • ZIP Code: {r['zip_code'] or 'N/A'}")
            print(f"   • Property Type: {r['property_type'] or 'N/A'}")
            if r['features']:
                print(f"   • Features ({len(r['features'])}): {', '.join(r['features'][:5])}")
                if len(r['features']) > 5:
                    print(f"     and {len(r['features'])-5} more...")
        else:
            print("Could not find property relationships")
    
    def demo_5_market_intelligence(self):
        """Demo 5: Market Intelligence Queries"""
        print("\n" + "="*60)
        print("DEMO 5: Market Intelligence")
        print("="*60)
        
        # Price distribution by property type
        print("\n📈 Price Distribution by Property Type:\n")
        query = """
        MATCH (p:Property)-[:TYPE_OF]->(pt:PropertyType)
        WITH pt.name as type,
             count(p) as count,
             percentileDisc(p.listing_price, 0.25) as q1,
             percentileDisc(p.listing_price, 0.50) as median,
             percentileDisc(p.listing_price, 0.75) as q3,
             avg(p.listing_price) as mean
        RETURN type, count, q1, median, q3, mean
        ORDER BY median DESC
        """
        
        results = self.run_query(query)
        
        if results:
            for r in results:
                print(f"🏠 {r['type'].title()}: {r['count']} properties")
                print(f"   • 25th percentile: ${r['q1']:,.0f}")
                print(f"   • Median: ${r['median']:,.0f}")
                print(f"   • 75th percentile: ${r['q3']:,.0f}")
                print(f"   • Mean: ${r['mean']:,.0f}")
                print()
        
        # Geographic price analysis
        print("🗺️ Geographic Price Analysis:\n")
        query = """
        MATCH (p:Property)-[:IN_ZIP_CODE]->(z:ZipCode)
        WITH z.id as zip_code,
             count(p) as property_count,
             avg(p.listing_price) as avg_price,
             avg(p.price_per_sqft) as avg_psf
        WHERE property_count >= 10
        RETURN zip_code, property_count, avg_price, avg_psf
        ORDER BY avg_price DESC
        LIMIT 5
        """
        
        results = self.run_query(query)
        
        if results:
            for i, r in enumerate(results, 1):
                print(f"{i}. ZIP {r['zip_code']}")
                print(f"   • Properties: {r['property_count']}")
                print(f"   • Avg Price: ${r['avg_price']:,.0f}")
                if r['avg_psf']:
                    print(f"   • Avg $/sqft: ${r['avg_psf']:,.2f}")
                print()
    
    def run_all_demos(self):
        """Run all demo queries."""
        print("\n" + "🚀 "*20)
        print("GRAPH DATABASE DEMO SUITE")
        print("🚀 "*20)
        
        self.demo_1_property_search()
        self.demo_2_neighborhood_analysis()
        self.demo_3_feature_analysis()
        self.demo_4_property_connections()
        self.demo_5_market_intelligence()
        
        print("\n" + "="*60)
        print("✅ All demos completed successfully!")
        print("="*60)

def main():
    """Main entry point."""
    runner = DemoRunner()
    
    try:
        runner.run_all_demos()
    finally:
        runner.close()

if __name__ == "__main__":
    main()