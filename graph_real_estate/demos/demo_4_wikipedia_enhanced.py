#!/usr/bin/env python3
"""
DEMO 4: WIKIPEDIA-ENHANCED PROPERTY LISTINGS
==============================================

This demo showcases how neighborhoods with Wikipedia articles can enrich
property listings with contextual information about the area.

Key Capabilities Demonstrated:
1. Direct neighborhood -> Wikipedia connection via wikipedia_page_id
2. Enriching property descriptions with neighborhood context
3. Historical and cultural information for areas
4. Location intelligence from Wikipedia data

Database Context:
- Neighborhoods have wikipedia_page_id field linking to Wikipedia articles
- Wikipedia nodes contain detailed information about locations
- Properties inherit context through their neighborhood relationship
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.database import get_neo4j_driver, close_neo4j_driver, run_query


class WikipediaEnhancedDemo:
    """Demonstrate Wikipedia enhancement of property listings"""
    
    def __init__(self):
        """Initialize the demo with database connection"""
        print("\nWIKIPEDIA-ENHANCED PROPERTY LISTINGS DEMO")
        print("=" * 80)
        print("Demonstrating how Wikipedia integration enriches property listings")
        print("with cultural, historical, and geographic intelligence.")
        print("=" * 80)
        
        print("\n🚀 NEO4J FEATURES DEMONSTRATED:")
        print("   • Node Properties - Using wikipedia_page_id field for linking")
        print("   • Dynamic Property Access - Conditional matching on node properties")
        print("   • OPTIONAL MATCH - Graceful handling of missing Wikipedia data")
        print("   • Graph Enrichment - Connecting property data with knowledge graphs")
        print("   • Multi-Model Integration - Combining property and Wikipedia nodes")
        print("   • Contextual Analysis - Using external data to enhance property insights")
        print("   • Conditional Logic - CASE statements for categorization")
        
        self.driver = get_neo4j_driver()
        
        # Check if Wikipedia data exists
        query = "MATCH (w:Wikipedia) RETURN count(w) as count"
        result = run_query(self.driver, query)
        wiki_count = result[0]['count'] if result else 0
        
        if wiki_count == 0:
            print("\n⚠️  Warning: No Wikipedia data found in database!")
            print("Please ensure Wikipedia data has been loaded.")
        else:
            print(f"\n✅ Found {wiki_count} Wikipedia articles in database")
    
    def run_demo(self):
        """Run the complete Wikipedia enhancement demonstration"""
        try:
            self.demo_basic_enhancement()
            self.demo_neighborhood_context()
            self.demo_location_intelligence()
        except Exception as e:
            print(f"\n❌ Error running demo: {e}")
    
    def demo_basic_enhancement(self):
        """Show properties with Wikipedia-enhanced neighborhoods"""
        print("\n" + "=" * 80)
        print("SECTION 1: BASIC WIKIPEDIA ENHANCEMENT")
        print("=" * 80)
        print("Properties in neighborhoods with Wikipedia articles")
        
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WHERE n.wikipedia_page_id IS NOT NULL
        OPTIONAL MATCH (w:Wikipedia {wikipedia_id: n.wikipedia_page_id})
        WITH p, n, w
        WHERE w IS NOT NULL
        RETURN 
            p.listing_id as listing_id,
            p.street_address as address,
            p.listing_price as price,
            p.bedrooms as bedrooms,
            p.bathrooms as bathrooms,
            p.square_feet as sqft,
            n.name as neighborhood,
            n.city as city,
            w.title as wiki_title,
            w.extract as wiki_extract
        ORDER BY p.listing_price DESC
        LIMIT 5
        """
        
        results = run_query(self.driver, query)
        
        if not results:
            print("\n⚠️  No properties found with Wikipedia-enhanced neighborhoods")
            return
        
        print(f"\nFound {len(results)} properties with Wikipedia context:\n")
        
        for i, prop in enumerate(results, 1):
            print(f"{i}. Property: {prop.get('listing_id', 'N/A')}")
            print(f"   Address: {prop.get('address', 'N/A')}")
            price = prop.get('price', 0)
            print(f"   Price: ${price:,.0f}")
            print(f"   Details: {prop.get('bedrooms', 0)} bed, {prop.get('bathrooms', 0)} bath, {prop.get('sqft', 0):,} sqft")
            print(f"   Neighborhood: {prop.get('neighborhood', 'N/A')}, {prop.get('city', 'N/A')}")
            
            if prop.get('wiki_title'):
                print(f"\n   📚 Wikipedia: {prop['wiki_title']}")
                if prop.get('wiki_extract'):
                    extract = prop['wiki_extract'][:200] + "..." if len(prop.get('wiki_extract', '')) > 200 else prop.get('wiki_extract', '')
                    print(f"   {extract}")
            print("\n" + "-" * 60)
    
    def demo_neighborhood_context(self):
        """Show neighborhoods with their Wikipedia context"""
        print("\n" + "=" * 80)
        print("SECTION 2: NEIGHBORHOOD WIKIPEDIA CONTEXT")
        print("=" * 80)
        print("Neighborhoods enriched with Wikipedia articles")
        
        query = """
        MATCH (n:Neighborhood)
        WHERE n.wikipedia_page_id IS NOT NULL
        OPTIONAL MATCH (w:Wikipedia {wikipedia_id: n.wikipedia_page_id})
        OPTIONAL MATCH (p:Property)-[:LOCATED_IN]->(n)
        WITH n, w, count(p) as property_count, avg(p.listing_price) as avg_price
        WHERE w IS NOT NULL
        RETURN 
            n.name as neighborhood,
            n.city as city,
            n.state as state,
            property_count,
            avg_price,
            w.title as wiki_title,
            w.url as wiki_url,
            w.categories as wiki_categories
        ORDER BY property_count DESC
        LIMIT 5
        """
        
        results = run_query(self.driver, query)
        
        if not results:
            print("\n⚠️  No neighborhoods found with Wikipedia articles")
            return
        
        print(f"\nFound {len(results)} neighborhoods with Wikipedia articles:\n")
        
        for i, hood in enumerate(results, 1):
            print(f"{i}. {hood.get('neighborhood', 'N/A')}, {hood.get('city', 'N/A')}, {hood.get('state', 'N/A')}")
            print(f"   Properties: {hood.get('property_count', 0)}")
            avg_price = hood.get('avg_price', 0) or 0
            if avg_price > 0:
                print(f"   Average Price: ${avg_price:,.0f}")
            
            if hood.get('wiki_title'):
                print(f"\n   📚 Wikipedia Article: {hood['wiki_title']}")
                if hood.get('wiki_url'):
                    print(f"   🔗 URL: {hood['wiki_url']}")
                if hood.get('wiki_categories'):
                    categories = hood['wiki_categories'][:3] if isinstance(hood['wiki_categories'], list) else []
                    if categories:
                        print(f"   📂 Categories: {', '.join(categories)}")
            print("\n" + "-" * 60)
    
    def demo_location_intelligence(self):
        """Show location intelligence from Wikipedia data"""
        print("\n" + "=" * 80)
        print("SECTION 3: LOCATION INTELLIGENCE")
        print("=" * 80)
        print("Market insights enriched with Wikipedia context")
        
        query = """
        MATCH (n:Neighborhood)
        WHERE n.wikipedia_page_id IS NOT NULL
        OPTIONAL MATCH (w:Wikipedia {wikipedia_id: n.wikipedia_page_id})
        OPTIONAL MATCH (p:Property)-[:LOCATED_IN]->(n)
        WITH n, w, 
             count(p) as property_count,
             avg(p.listing_price) as avg_price,
             min(p.listing_price) as min_price,
             max(p.listing_price) as max_price
        WHERE w IS NOT NULL AND property_count > 0
        RETURN 
            n.name as neighborhood,
            n.city as city,
            property_count,
            avg_price,
            min_price,
            max_price,
            w.title as wiki_title,
            CASE 
                WHEN w.extract CONTAINS 'historic' THEN 'Historic'
                WHEN w.extract CONTAINS 'residential' THEN 'Residential'
                WHEN w.extract CONTAINS 'commercial' THEN 'Mixed-Use'
                ELSE 'Standard'
            END as area_type
        ORDER BY avg_price DESC
        LIMIT 5
        """
        
        results = run_query(self.driver, query)
        
        if not results:
            print("\n⚠️  No location intelligence data available")
            return
        
        print(f"\nLocation Intelligence for {len(results)} neighborhoods:\n")
        
        for i, loc in enumerate(results, 1):
            print(f"{i}. {loc.get('neighborhood', 'N/A')}, {loc.get('city', 'N/A')}")
            print(f"   Area Type: {loc.get('area_type', 'Unknown')}")
            print(f"   Market Stats:")
            print(f"      Properties: {loc.get('property_count', 0)}")
            
            avg_price = loc.get('avg_price', 0) or 0
            min_price = loc.get('min_price', 0) or 0
            max_price = loc.get('max_price', 0) or 0
            
            if avg_price > 0:
                print(f"      Average: ${avg_price:,.0f}")
                print(f"      Range: ${min_price:,.0f} - ${max_price:,.0f}")
            
            if loc.get('wiki_title'):
                print(f"   Wikipedia: {loc['wiki_title']}")
            print("\n" + "-" * 60)
        
        print("\n" + "=" * 80)
        print("WIKIPEDIA ENHANCEMENT COMPLETE")
        print("=" * 80)
        print("\nThis demonstration showed how Wikipedia data enriches property listings")
        print("by providing historical, cultural, and geographic context through the")
        print("direct neighborhood -> Wikipedia connection via wikipedia_page_id.")
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            close_neo4j_driver(self.driver)


def run_wikipedia_enhanced_demo():
    """Main execution function"""
    demo = None
    try:
        demo = WikipediaEnhancedDemo()
        demo.run_demo()
    except Exception as e:
        print(f"\n❌ Failed to run demo: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if demo:
            demo.cleanup()


def main():
    """Main entry point"""
    run_wikipedia_enhanced_demo()


if __name__ == "__main__":
    main()