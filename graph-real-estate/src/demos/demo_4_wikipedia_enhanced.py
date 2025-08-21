#!/usr/bin/env python3
"""
DEMO 4: WIKIPEDIA-ENHANCED PROPERTY LISTINGS
=============================================

This demo showcases how Wikipedia integration transforms static property 
listings into rich, contextual narratives by leveraging Wikipedia content 
about neighborhoods, landmarks, and local culture.

Key Capabilities Demonstrated:
1. Property descriptions enriched with Wikipedia context
2. Neighborhood cultural and historical insights
3. Landmark proximity and significance
4. Investment insights based on Wikipedia data
5. Lifestyle matching using Wikipedia categories
6. Market positioning with geographic intelligence

Database Context:
- 131 Wikipedia articles integrated
- 235 DESCRIBES relationships to neighborhoods
- 100+ properties with enriched descriptions
- Multiple relationship types: primary, cultural, park, landmark, transit
"""

import sys
import signal
from pathlib import Path
from typing import Dict, List, Any, Optional
import json

# Handle broken pipe errors gracefully when piping output
if hasattr(signal, 'SIGPIPE'):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.database import get_neo4j_driver
from src.database.neo4j_client import run_query


class WikipediaEnhancedListings:
    """Showcase Wikipedia-enhanced property listings and neighborhood intelligence"""
    
    def __init__(self, driver):
        self.driver = driver
    
    def print_section_header(self, title: str, description: str = ""):
        """Print formatted section header"""
        print(f"\n{'='*80}")
        print(f"{title.upper()}")
        print(f"{'='*80}")
        if description:
            print(f"{description}\n")
    
    def print_property_listing(self, property_data: Dict[str, Any], wiki_context: List[Dict[str, Any]]):
        """Print an enhanced property listing with Wikipedia context"""
        print(f"\nProperty {property_data['listing_id']}")
        print("-" * 60)
        
        # Basic property info
        print(f"Location: {property_data['neighborhood']}, {property_data['city']}")
        print(f"Price: ${property_data['listing_price']:,.0f}")
        
        if property_data.get('bedrooms'):
            details = []
            if property_data.get('bedrooms'):
                details.append(f"{property_data['bedrooms']} bed")
            if property_data.get('bathrooms'):
                details.append(f"{property_data['bathrooms']} bath")
            if property_data.get('square_feet'):
                details.append(f"{property_data['square_feet']:,} sqft")
            print(f"Details: {' | '.join(details)}")
        
        # Original description
        print(f"\nOriginal Description:")
        print(f"   {property_data['description'][:300]}...")
        
        # Wikipedia enhancement
        if wiki_context:
            print(f"\nWikipedia-Enhanced Context ({len(wiki_context)} articles):")
            
            # Group by type
            by_type = {}
            for w in wiki_context:
                typ = w.get('type', 'general')
                if typ not in by_type:
                    by_type[typ] = []
                by_type[typ].append(w)
            
            for typ, articles in by_type.items():
                print(f"\n   {typ.upper()}:")
                for article in articles[:3]:  # Limit to 3 per type
                    confidence = article.get('confidence', 0)
                    conf_icon = "" if confidence > 0.8 else "" if confidence > 0.5 else ""
                    print(f"   {conf_icon} {article['title']}")
                    if article.get('summary'):
                        summary = article['summary'][:250].replace('\n', ' ')
                        print(f"      {summary}...")
        
        # Enhanced description
        if property_data.get('enriched_description'):
            print(f"\nEnhanced Listing:")
            print(f"   {property_data['enriched_description']}")
    
    # ===== SECTION 1: BASIC WIKIPEDIA ENHANCEMENT =====
    
    def showcase_basic_enhancement(self):
        """Show basic property enhancement with Wikipedia context"""
        self.print_section_header(
            "Basic Wikipedia Enhancement",
            "Properties enriched with neighborhood Wikipedia articles"
        )
        
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WHERE p.enriched_description IS NOT NULL
        OPTIONAL MATCH (n)<-[:DESCRIBES]-(w:Wikipedia)
        WITH p, n, collect(DISTINCT {
            title: w.title,
            type: w.relationship_type,
            confidence: w.confidence,
            summary: substring(w.summary, 0, 200)
        }) as wiki_articles
        RETURN p.listing_id as listing_id,
               p.description as description,
               p.enriched_description as enriched_description,
               p.listing_price as listing_price,
               p.bedrooms as bedrooms,
               p.bathrooms as bathrooms,
               p.square_feet as square_feet,
               n.name as neighborhood,
               n.city as city,
               wiki_articles
        ORDER BY size(wiki_articles) DESC
        LIMIT 3
        """
        
        results = run_query(self.driver, query)
        
        for r in results:
            self.print_property_listing(r, r['wiki_articles'])
    
    # ===== SECTION 2: CULTURAL & HISTORICAL CONTEXT =====
    
    def showcase_cultural_context(self):
        """Properties near cultural and historical landmarks"""
        self.print_section_header(
            "Cultural & Historical Context",
            "Properties enriched with cultural and historical Wikipedia articles"
        )
        
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)<-[:DESCRIBES]-(w:Wikipedia)
        WHERE w.relationship_type IN ['cultural', 'landmark', 'historical']
        WITH p, n, collect(DISTINCT {
            title: w.title,
            type: w.relationship_type,
            confidence: w.confidence
        }) as cultural_articles
        WHERE size(cultural_articles) > 0
        RETURN p.listing_id as listing_id,
               p.listing_price as price,
               n.name as neighborhood,
               n.city as city,
               cultural_articles
        ORDER BY size(cultural_articles) DESC, p.listing_price DESC
        LIMIT 5
        """
        
        results = run_query(self.driver, query)
        
        print("Properties with Rich Cultural Context:\n")
        for r in results:
            print(f"Property {r['listing_id']} - ${r['price']:,.0f}")
            print(f"   Location: {r['neighborhood']}, {r['city']}")
            print(f"   Cultural Significance ({len(r['cultural_articles'])} landmarks):")
            
            for article in r['cultural_articles']:
                conf_icon = "" if article['type'] == 'landmark' else "" if article['type'] == 'cultural' else ""
                print(f"      {conf_icon} {article['title']} (confidence: {article['confidence']:.2f})")
    
    # ===== SECTION 3: NEIGHBORHOOD INTELLIGENCE =====
    
    def showcase_neighborhood_intelligence(self):
        """Deep neighborhood analysis using Wikipedia data"""
        self.print_section_header(
            "Neighborhood Intelligence",
            "Comprehensive neighborhood profiles powered by Wikipedia"
        )
        
        query = """
        MATCH (n:Neighborhood)<-[:DESCRIBES]-(w:Wikipedia)
        WITH n, collect(DISTINCT {
            title: w.title,
            type: w.relationship_type,
            confidence: w.confidence,
            summary: substring(w.summary, 0, 150)
        }) as wiki_articles
        WHERE size(wiki_articles) >= 3
        MATCH (p:Property)-[:LOCATED_IN]->(n)
        WITH n, wiki_articles,
             count(p) as property_count,
             avg(p.listing_price) as avg_price,
             min(p.listing_price) as min_price,
             max(p.listing_price) as max_price
        RETURN n.name as neighborhood,
               n.city as city,
               n.lifestyle_tags as lifestyle_tags,
               n.walkability_score as walkability,
               property_count,
               avg_price,
               min_price,
               max_price,
               wiki_articles
        ORDER BY size(wiki_articles) DESC
        LIMIT 3
        """
        
        results = run_query(self.driver, query)
        
        for r in results:
            print(f"\n{r['neighborhood']}, {r['city']}")
            print("-" * 60)
            
            # Market stats
            print(f"Market Overview:")
            print(f"   Properties: {r['property_count']}")
            print(f"   Price Range: ${r['min_price']:,.0f} - ${r['max_price']:,.0f}")
            print(f"   Average: ${r['avg_price']:,.0f}")
            
            # Lifestyle
            if r['lifestyle_tags']:
                print(f"\nLifestyle Tags: {', '.join(r['lifestyle_tags'])}")
            if r['walkability']:
                print(f"Walkability Score: {r['walkability']}/10")
            
            # Wikipedia intelligence
            print(f"\nWikipedia Intelligence ({len(r['wiki_articles'])} articles):")
            
            # Group by type
            by_type = {}
            for w in r['wiki_articles']:
                typ = w.get('type', 'general')
                if typ not in by_type:
                    by_type[typ] = []
                by_type[typ].append(w)
            
            for typ, articles in sorted(by_type.items()):
                print(f"\n   {typ.upper()} ({len(articles)}):")
                for article in articles[:2]:
                    print(f"   • {article['title']}")
                    if article.get('summary'):
                        print(f"     {article['summary']}...")
    
    # ===== SECTION 4: INVESTMENT INSIGHTS =====
    
    def showcase_investment_insights(self):
        """Investment opportunities based on Wikipedia significance"""
        self.print_section_header(
            "Investment Insights from Wikipedia",
            "Properties in areas with high Wikipedia significance"
        )
        
        # Properties in neighborhoods with many Wikipedia articles
        query = """
        MATCH (n:Neighborhood)<-[:DESCRIBES]-(w:Wikipedia)
        WHERE w.confidence > 0.7
        WITH n, count(DISTINCT w) as wiki_count,
             collect(DISTINCT w.relationship_type) as wiki_types
        MATCH (p:Property)-[:LOCATED_IN]->(n)
        WITH n, wiki_count, wiki_types,
             count(p) as property_count,
             avg(p.listing_price) as avg_price,
             avg(p.listing_price / NULLIF(p.square_feet, 0)) as price_per_sqft
        WHERE property_count >= 5
        RETURN n.name as neighborhood,
               n.city as city,
               wiki_count,
               wiki_types,
               property_count,
               avg_price,
               price_per_sqft,
               wiki_count * 1.0 / property_count as wiki_density
        ORDER BY wiki_density DESC
        LIMIT 8
        """
        
        results = run_query(self.driver, query)
        
        print("Neighborhoods with High Wikipedia Significance:\n")
        print("(Higher wiki density = more documented significance per property)\n")
        
        for r in results:
            density_icon = "" if r['wiki_density'] > 0.5 else "" if r['wiki_density'] > 0.3 else ""
            print(f"{density_icon} {r['neighborhood']}, {r['city']}")
            print(f"   Wikipedia Density: {r['wiki_density']:.2f} (articles/property)")
            print(f"   Total Wikipedia Articles: {r['wiki_count']}")
            print(f"   Article Types: {', '.join(r['wiki_types'])}")
            print(f"   Investment Metrics:")
            print(f"      Avg Price: ${r['avg_price']:,.0f}")
            if r['price_per_sqft']:
                print(f"      Price/sqft: ${r['price_per_sqft']:.0f}")
            print(f"      Properties Available: {r['property_count']}")
            print()
    
    # ===== SECTION 5: LIFESTYLE DISCOVERY =====
    
    def showcase_lifestyle_discovery(self):
        """Discover properties based on Wikipedia-inferred lifestyle"""
        self.print_section_header(
            "Lifestyle Discovery via Wikipedia",
            "Match properties to lifestyle preferences using Wikipedia categories"
        )
        
        # Define lifestyle patterns based on Wikipedia types
        lifestyle_queries = [
            {
                "name": "Urban Cultural Hub",
                "types": ['cultural', 'transit', 'commercial'],
                "description": "City living with rich cultural amenities"
            },
            {
                "name": "Nature & Recreation",
                "types": ['park', 'recreation', 'natural'],
                "description": "Properties near parks and outdoor activities"
            },
            {
                "name": "Historic Charm",
                "types": ['historical', 'landmark'],
                "description": "Areas with historical significance"
            }
        ]
        
        for lifestyle in lifestyle_queries:
            print(f"\n{lifestyle['name']}")
            print(f"   {lifestyle['description']}")
            print("-" * 60)
            
            # Build dynamic query for this lifestyle
            type_conditions = " OR ".join([f"w.relationship_type = '{t}'" for t in lifestyle['types']])
            
            query = f"""
            MATCH (n:Neighborhood)<-[:DESCRIBES]-(w:Wikipedia)
            WHERE {type_conditions}
            WITH n, count(DISTINCT w) as lifestyle_match_count,
                 collect(DISTINCT w.title) as matching_articles
            WHERE lifestyle_match_count >= 2
            MATCH (p:Property)-[:LOCATED_IN]->(n)
            WITH n, lifestyle_match_count, matching_articles,
                 min(p.listing_price) as min_price,
                 max(p.listing_price) as max_price,
                 count(p) as available_properties
            RETURN n.name as neighborhood,
                   n.city as city,
                   lifestyle_match_count,
                   matching_articles[0..3] as sample_articles,
                   min_price,
                   max_price,
                   available_properties
            ORDER BY lifestyle_match_count DESC
            LIMIT 3
            """
            
            results = run_query(self.driver, query)
            
            if results:
                for r in results:
                    print(f"\n   {r['neighborhood']}, {r['city']}")
                    print(f"      Match Score: {r['lifestyle_match_count']} Wikipedia articles")
                    print(f"      Price Range: ${r['min_price']:,.0f} - ${r['max_price']:,.0f}")
                    print(f"      Available: {r['available_properties']} properties")
                    print(f"      Relevant Articles: {', '.join(r['sample_articles'])}")
            else:
                print("   No matching neighborhoods found")
    
    # ===== SECTION 6: COMPARATIVE MARKET ANALYSIS =====
    
    def showcase_comparative_analysis(self):
        """Compare neighborhoods using Wikipedia data"""
        self.print_section_header(
            "Comparative Market Analysis",
            "Compare neighborhoods using Wikipedia-derived intelligence"
        )
        
        query = """
        // Compare top neighborhoods by Wikipedia coverage
        MATCH (n:Neighborhood)<-[:DESCRIBES]-(w:Wikipedia)
        WITH n, 
             count(DISTINCT w) as total_articles,
             count(DISTINCT CASE WHEN w.relationship_type = 'cultural' THEN w END) as cultural_count,
             count(DISTINCT CASE WHEN w.relationship_type = 'park' THEN w END) as park_count,
             count(DISTINCT CASE WHEN w.relationship_type = 'transit' THEN w END) as transit_count,
             count(DISTINCT CASE WHEN w.relationship_type = 'landmark' THEN w END) as landmark_count,
             avg(w.confidence) as avg_confidence
        WHERE total_articles >= 3
        MATCH (p:Property)-[:LOCATED_IN]->(n)
        WITH n, total_articles, cultural_count, park_count, transit_count, landmark_count,
             avg_confidence,
             avg(p.listing_price) as avg_price,
             count(p) as property_count
        RETURN n.name as neighborhood,
               n.city as city,
               total_articles,
               cultural_count,
               park_count,
               transit_count,
               landmark_count,
               avg_confidence,
               avg_price,
               property_count
        ORDER BY total_articles DESC
        LIMIT 6
        """
        
        results = run_query(self.driver, query)
        
        print("Neighborhood Comparison Matrix:\n")
        
        # Header
        print(f"{'Neighborhood':<25} {'Wiki':<6} {'Culture':<8} {'Parks':<7} {'Transit':<8} {'Landmarks':<10} {'Avg Price':<12}")
        print("-" * 100)
        
        for r in results:
            neighborhood = f"{r['neighborhood'][:20]}, {r['city'][:3]}"
            print(f"{neighborhood:<25} {r['total_articles']:<6} {r['cultural_count']:<8} "
                  f"{r['park_count']:<7} {r['transit_count']:<8} {r['landmark_count']:<10} "
                  f"${r['avg_price']/1000000:.1f}M")
        
        print("\nAnalysis Insights:")
        
        # Find the most culturally rich
        culturally_rich = max(results, key=lambda x: x['cultural_count'])
        print(f"   Most Culturally Rich: {culturally_rich['neighborhood']} "
              f"({culturally_rich['cultural_count']} cultural Wikipedia articles)")
        
        # Find the best for nature
        nature_friendly = max(results, key=lambda x: x['park_count'])
        if nature_friendly['park_count'] > 0:
            print(f"   Best for Nature Lovers: {nature_friendly['neighborhood']} "
                  f"({nature_friendly['park_count']} park-related articles)")
        
        # Find the best documented
        best_documented = max(results, key=lambda x: x['total_articles'])
        print(f"   Best Documented: {best_documented['neighborhood']} "
              f"({best_documented['total_articles']} total Wikipedia articles)")
        
        # Find the best value with good documentation
        if len(results) > 3:
            sorted_by_value = sorted(
                [r for r in results if r['total_articles'] >= 5],
                key=lambda x: x['avg_price']
            )
            if sorted_by_value:
                best_value = sorted_by_value[0]
                print(f"   Best Value (Well-Documented): {best_value['neighborhood']} "
                      f"(${best_value['avg_price']:,.0f} avg, {best_value['total_articles']} articles)")


def run_wikipedia_enhanced_demo():
    """Run the complete Wikipedia enhancement demonstration"""
    print("WIKIPEDIA-ENHANCED PROPERTY LISTINGS DEMO")
    print("="*80)
    print("Demonstrating how Wikipedia integration transforms static property")
    print("listings into rich, contextual narratives with cultural, historical,")
    print("and geographic intelligence.")
    print("="*80)
    
    driver = None
    try:
        driver = get_neo4j_driver()
        
        # Quick check that Wikipedia data exists
        wiki_check = run_query(driver, "MATCH (w:Wikipedia) RETURN count(w) as count")
        if wiki_check[0]['count'] == 0:
            print("\nWarning: No Wikipedia data found in database!")
            print("Please run 'python main.py all' to import Wikipedia articles.")
            return
        
        print(f"\nFound {wiki_check[0]['count']} Wikipedia articles in database")
        
        showcase = WikipediaEnhancedListings(driver)
        
        # Run all showcase sections
        showcase.showcase_basic_enhancement()
        showcase.showcase_cultural_context()
        showcase.showcase_neighborhood_intelligence()
        showcase.showcase_investment_insights()
        showcase.showcase_lifestyle_discovery()
        showcase.showcase_comparative_analysis()
        
        print(f"\n{'='*80}")
        print("WIKIPEDIA ENHANCEMENT DEMO COMPLETE")
        print("="*80)
        print("\nThis demonstration showcased:")
        print("• Basic property enhancement with Wikipedia context")
        print("• Cultural and historical significance of locations")
        print("• Deep neighborhood intelligence from Wikipedia")
        print("• Investment insights based on Wikipedia coverage")
        print("• Lifestyle discovery through Wikipedia categories")
        print("• Comparative market analysis using Wikipedia data")
        print("\nWikipedia integration provides rich context that transforms")
        print("property listings from mere data points into compelling narratives")
        print("that help buyers understand not just the property, but the")
        print("complete lifestyle and cultural context of their potential new home.")
        
    except Exception as e:
        print(f"Demo error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.close()


if __name__ == "__main__":
    run_wikipedia_enhanced_demo()