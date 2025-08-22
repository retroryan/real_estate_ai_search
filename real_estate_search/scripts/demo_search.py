#!/usr/bin/env python3
"""
Demo script for Wikipedia-enhanced property search.
Shows various search capabilities using real data.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from real_estate_search.search.search_engine import SearchEngine, SearchMode
from real_estate_search.search.models import SearchRequest, SearchFilters
from real_estate_search.search.enums import QueryType
from real_estate_search.indexer.property_indexer import PropertyIndexer
from real_estate_search.wikipedia.extractor import WikipediaExtractor


class SearchDemo:
    """Demonstration of Wikipedia-enhanced search capabilities."""
    
    def __init__(self):
        """Initialize demo components."""
        self.search_engine = SearchEngine()
        self.indexer = PropertyIndexer()
        self.wikipedia_extractor = WikipediaExtractor()
    
    def setup_demo_index(self, force_recreate: bool = True):
        """Set up the demo index with sample data."""
        print("\n🔧 Setting up demo index...")
        
        # Create index
        if self.indexer.create_index(force_recreate=force_recreate):
            print("✅ Index created successfully")
        else:
            print("❌ Failed to create index")
            return False
        
        # Index properties
        print("\n📥 Indexing properties with Wikipedia enrichment...")
        
        # Get absolute paths to property files
        project_root = Path(__file__).parent.parent.parent
        sf_file = project_root / "real_estate_data" / "properties_sf.json"
        pc_file = project_root / "real_estate_data" / "properties_pc.json"
        
        # Index SF properties
        sf_stats = self.indexer.index_properties_from_file(
            str(sf_file),
            batch_size=20
        )
        print(f"  SF Properties: {sf_stats.success} indexed, {sf_stats.failed} failed")
        
        # Index Park City properties
        pc_stats = self.indexer.index_properties_from_file(
            str(pc_file),
            batch_size=20
        )
        print(f"  Park City Properties: {pc_stats.success} indexed, {pc_stats.failed} failed")
        
        # Show index stats
        stats = self.indexer.get_index_stats()
        print(f"\n📊 Index Statistics:")
        print(f"  Total documents: {stats.get('document_count', 0)}")
        print(f"  Wikipedia coverage:")
        print(f"    - Location context: {stats['wikipedia_coverage']['location_context']}")
        print(f"    - Neighborhood context: {stats['wikipedia_coverage']['neighborhood_context']}")
        print(f"    - Has POIs: {stats['wikipedia_coverage']['has_pois']}")
        avg_desirability = stats['wikipedia_coverage'].get('avg_desirability', 0)
        if avg_desirability is not None:
            print(f"    - Avg desirability: {avg_desirability:.2f}")
        else:
            print(f"    - Avg desirability: N/A")
        
        return True
    
    def demo_park_city_ski_search(self):
        """
        🎿 Ski Resort Properties Search
        
        Find luxury homes near world-class ski resorts in Park City, Utah.
        This search combines property features with location intelligence from
        Wikipedia to find homes that offer premium ski access and mountain lifestyle.
        
        What this search does:
        - Searches for luxury properties with ski resort proximity
        - Uses Wikipedia data about Deer Valley and Park City Mountain Resort
        - Filters for high-end properties ($1M+) in Park City
        - Ranks results by ski accessibility and luxury amenities
        """
        print("\n" + "="*60)
        print("🎿 DEMO 1: Park City Ski Resort Properties")
        print("="*60)
        
        query = "ski resort luxury home near Deer Valley"
        print(f"\nQuery: '{query}'")
        print("English: Find luxury ski resort properties near world-class slopes")
        
        request = SearchRequest(
            query_text=query,
            search_mode=SearchMode.STANDARD,
            filters=SearchFilters(
                cities=["Park City"],
                min_price=1000000
            ),
            size=3
        )
        results = self.search_engine.search(request)
        
        self._display_results(results, show_wikipedia=True)
    
    def demo_sf_cultural_search(self):
        """
        🎭 Cultural District Properties Search
        
        Discover properties near San Francisco's world-renowned cultural institutions.
        This search leverages Wikipedia data about museums, theaters, and art venues
        to find homes in vibrant cultural neighborhoods.
        
        What this search does:
        - Emphasizes proximity to museums, galleries, and theaters
        - Uses Wikipedia articles about SFMOMA, de Young Museum, Castro Theatre
        - Filters for properties suitable for cultural enthusiasts (2+ bedrooms)
        - Ranks by cultural venue density and neighborhood artistic character
        """
        print("\n" + "="*60)
        print("🎭 DEMO 2: San Francisco Cultural District Properties")
        print("="*60)
        
        query = "museum arts cultural"
        print(f"\nQuery: '{query}' (Cultural Mode)")
        print("English: Find homes near museums, galleries, and cultural venues")
        
        request = SearchRequest(
            query_text=query,
            search_mode=SearchMode.CULTURAL,
            filters=SearchFilters(
                cities=["San Francisco"],
                min_bedrooms=2
            ),
            size=3
        )
        results = self.search_engine.search(request)
        
        self._display_results(results, show_pois=True)
    
    def demo_lifestyle_search(self):
        """
        🏡 Family Lifestyle Properties Search
        
        Find family-friendly homes near parks and recreational facilities.
        This search prioritizes properties in neighborhoods with great outdoor
        amenities and family-oriented community features.
        
        What this search does:
        - Searches for homes near parks, playgrounds, and recreation centers
        - Uses Wikipedia data about Golden Gate Park, Crissy Field, and local parks
        - Filters for family-sized homes (3+ bedrooms) under $2M
        - Ranks by proximity to outdoor activities and family amenities
        """
        print("\n" + "="*60)
        print("🏡 DEMO 3: Lifestyle-Based Search")
        print("="*60)
        
        query = "park recreation family outdoor"
        print(f"\nQuery: '{query}' (Lifestyle Mode)")
        print("English: Find family homes near parks and outdoor recreation")
        
        request = SearchRequest(
            query_text=query,
            search_mode=SearchMode.LIFESTYLE,
            filters=SearchFilters(
                min_bedrooms=3,
                max_price=2000000
            ),
            size=3
        )
        results = self.search_engine.search(request)
        
        self._display_results(results, show_scores=True)
    
    def demo_poi_proximity_search(self):
        """
        📍 Point of Interest Proximity Search
        
        Find properties within walking distance of specific landmarks or amenities.
        This search uses geo-location data and Wikipedia POI information to find
        homes near your preferred destinations.
        
        What this search does:
        - Searches for properties within 1 mile of parks and landmarks
        - Uses GPS coordinates from Wikipedia articles
        - Calculates walking distances to POIs
        - Shows which specific POIs match your search
        """
        print("\n" + "="*60)
        print("📍 DEMO 4: POI Proximity Search")
        print("="*60)
        
        query = "Park"  # Will match various parks
        print(f"\nQuery: Properties near '{query}' (within 1 mile)")
        print("English: Find homes within walking distance of parks and green spaces")
        
        request = SearchRequest(
            query_text=query,
            search_mode=SearchMode.POI_PROXIMITY,
            filters=SearchFilters(),  # Will use default max_distance_miles in query builder
            size=3
        )
        results = self.search_engine.search(request)
        
        self._display_results(results, show_matching_pois=True)
    
    def demo_investment_search(self):
        """
        💰 Investment Property Search
        
        Identify properties with strong rental and investment potential.
        This search combines location data with tourism and economic indicators
        from Wikipedia to find profitable investment opportunities.
        
        What this search does:
        - Searches for properties in tourist-heavy areas
        - Uses Wikipedia data about visitor attractions and economic activity
        - Identifies areas with strong rental demand
        - Ranks by investment potential and tourism proximity
        """
        print("\n" + "="*60)
        print("💰 DEMO 5: Investment Property Search")
        print("="*60)
        
        query = "tourist rental investment"
        print(f"\nQuery: '{query}' (Investment Mode)")
        print("English: Find properties with strong rental and tourism potential")
        
        request = SearchRequest(
            query_text=query,
            search_mode=SearchMode.INVESTMENT,
            size=3
        )
        results = self.search_engine.search(request)
        
        self._display_results(results, show_investment_metrics=True)
    
    def demo_basic_property_search(self):
        """
        🏠 Basic Property Search
        
        Simple search for luxury homes with specific criteria.
        This demonstrates the core search functionality combining property
        attributes with location intelligence.
        
        What this search does:
        - Searches for luxury ski resort properties
        - Filters by location (Park City) and price ($1M+)
        - Uses combined property and Wikipedia data for ranking
        - Shows fundamental search capabilities
        """
        print("\n" + "="*60)
        print("🏠 DEMO 6: Basic Property Search")
        print("="*60)
        
        query = "luxury ski resort"
        print(f"\nQuery: '{query}'")
        print("English: Find luxury homes near ski resorts")
        
        request = SearchRequest(
            query_text=query,
            filters=SearchFilters(
                cities=["park city"],
                min_price=1000000
            ),
            size=10
        )
        results = self.search_engine.search(request)
        
        self._display_results(results, show_basic_info=True)
    
    
    def demo_faceted_search(self):
        """
        🔍 Faceted Search Options
        
        Demonstrate advanced filtering and aggregation capabilities.
        This shows how users can explore properties by various categories
        and use facets to refine their search criteria.
        
        What this search does:
        - Shows available filter options across all properties
        - Displays price ranges, cultural features, and POI categories
        - Provides location quality metrics
        - Enables drill-down search refinement
        """
        print("\n" + "="*60)
        print("🔍 DEMO 8: Faceted Search Options")
        print("="*60)
        
        facets = self.search_engine.get_facets(query="park")
        
        print("\n📊 Available Facets:")
        print("English: Show filter options and property categorization")
        
        # Price ranges
        print("\n💵 Price Ranges:")
        for bucket in facets.get("price_range", {}).get("buckets", []):
            print(f"  {bucket['key']}: {bucket['doc_count']} properties")
        
        # Cultural features
        print("\n🎭 Cultural Features:")
        for bucket in facets.get("cultural_features", {}).get("buckets", [])[:5]:
            print(f"  {bucket['key']}: {bucket['doc_count']} properties")
        
        # POI categories
        print("\n📍 Nearby POI Categories:")
        poi_cats = facets.get("poi_categories", {}).get("categories", {}).get("buckets", [])
        for bucket in poi_cats[:5]:
            print(f"  {bucket['key']}: {bucket['doc_count']} properties")
        
        # Location quality
        print("\n⭐ Location Quality:")
        for bucket in facets.get("location_quality", {}).get("buckets", []):
            print(f"  {bucket['key']}: {bucket['doc_count']} properties")
    
    def _display_results(
        self,
        results,
        show_wikipedia: bool = False,
        show_pois: bool = False,
        show_scores: bool = False,
        show_matching_pois: bool = False,
        show_investment_metrics: bool = False,
        show_basic_info: bool = False
    ):
        """Display search results with various details and Wikipedia content."""
        print(f"\n📊 Found {results.total} properties")
        
        for i, hit in enumerate(results.hits[:3], 1):
            prop = hit.property
            print(f"\n{i}. Property {prop.listing_id}")
            print(f"   📍 {prop.address.street}, {prop.address.city}")
            print(f"   💰 ${prop.price:,.0f}")
            print(f"   🏠 {prop.bedrooms} bed, {prop.bathrooms} bath, {prop.square_feet:,} sqft" if prop.square_feet else f"   🏠 {prop.bedrooms} bed, {prop.bathrooms} bath")
            
            # Try to access Wikipedia data from raw Elasticsearch hit
            es_hit = hit._raw_hit if hasattr(hit, '_raw_hit') else {}
            source = es_hit.get('_source', {})
            
            if show_wikipedia and source:
                location_context = source.get('location_context', {})
                if location_context:
                    print(f"   📚 Wikipedia: {location_context.get('wikipedia_title', 'Location data available')}")
                    if location_context.get('location_summary'):
                        summary = location_context['location_summary'][:100] + "..." if len(location_context['location_summary']) > 100 else location_context['location_summary']
                        print(f"      Summary: {summary}")
                else:
                    print(f"   📚 Wikipedia data enrichment: Available in search index")
            
            if show_pois and source:
                pois = source.get('nearby_poi', [])
                if pois:
                    print(f"   🗺️ Nearby POIs: {len(pois)} found")
                    for poi in pois[:2]:  # Show first 2 POIs
                        print(f"      • {poi.get('name', 'POI')} ({poi.get('category', 'location')})")
                else:
                    print(f"   🗺️ POI data: Available in search index")
            
            if show_scores and source:
                location_quality = source.get('location_quality_score', 0)
                desirability = source.get('neighborhood_desirability', 0)
                print(f"   ⭐ Location Quality: {location_quality:.1f}/10")
                print(f"   ✨ Desirability: {desirability:.1f}/10")
            
            if show_matching_pois and source:
                pois = source.get('nearby_poi', [])
                matching_pois = [poi for poi in pois if 'park' in poi.get('name', '').lower()]
                if matching_pois:
                    print(f"   🎯 Matching POIs: {len(matching_pois)} parks nearby")
                    for poi in matching_pois[:2]:
                        distance = poi.get('distance_miles', 0)
                        print(f"      • {poi.get('name', 'Park')} ({distance:.1f} miles)")
                else:
                    print(f"   🎯 Nearby POIs: Searchable in index")
            
            if show_investment_metrics and source:
                tourism_score = source.get('tourism_potential', 0)
                rental_demand = source.get('rental_demand_score', 0)
                print(f"   📈 Tourism Potential: {tourism_score:.1f}/10")
                print(f"   🏠 Rental Demand: {rental_demand:.1f}/10")
            
            if show_basic_info:
                print(f"   ⭐ Match Score: {hit.score:.2f}")
            
            # Show highlights if available
            if hit.highlights:
                print(f"   💡 Matched in: {', '.join(hit.highlights.keys())}")
    
    def demo_property_listing_with_wikipedia(self):
        """
        🏠 Property Listing with Wikipedia Integration
        
        Show a detailed property listing enriched with Wikipedia location data.
        This demonstrates how Wikipedia content enhances property information
        with rich neighborhood context, historical background, and local POIs.
        
        What this shows:
        - Full property details with market information
        - Wikipedia-derived neighborhood context and history
        - Nearby points of interest from Wikipedia articles
        - Location quality and desirability metrics
        - Investment potential based on tourism data
        """
        print("\n" + "="*60)
        print("🏠 DEMO 9: Property Listing with Wikipedia Integration")
        print("="*60)
        
        # Get a sample property with rich data
        request = SearchRequest(
            query_text="luxury mountain",
            filters=SearchFilters(cities=["park city"]),
            size=1
        )
        results = self.search_engine.search(request)
        
        if not results.hits:
            print("No properties found for detailed listing demo")
            return
            
        hit = results.hits[0]
        prop = hit.property
        
        print(f"\n🏡 FEATURED PROPERTY LISTING")
        print("="*40)
        
        # Basic property info
        print(f"Property ID: {prop.listing_id}")
        print(f"📍 Address: {prop.address.street}")
        print(f"           {prop.address.city}, {prop.address.state} {prop.address.zip_code}")
        print(f"💰 Price: ${prop.price:,.0f}")
        print(f"🏠 Details: {prop.bedrooms} bed, {prop.bathrooms} bath")
        if prop.square_feet:
            print(f"📐 Size: {prop.square_feet:,} sqft (${prop.price/prop.square_feet:.0f}/sqft)")
        if prop.year_built:
            print(f"🏗️ Built: {prop.year_built}")
        if prop.property_type:
            print(f"🏘️ Type: {prop.property_type.value}")
            
        # Try to get Wikipedia enrichment data
        try:
            # Get raw ES document
            es_response = self.search_engine.es_client.get(
                index=self.search_engine.index_name,
                id=hit.doc_id
            )
            source = es_response['_source']
            
            # Location context from Wikipedia
            location_context = source.get('location_context', {})
            if location_context:
                print(f"\n📚 LOCATION CONTEXT (Wikipedia)")
                print("="*40)
                print(f"📖 Wikipedia: {location_context.get('wikipedia_title', 'N/A')}")
                
                if location_context.get('location_summary'):
                    print(f"📝 Summary: {location_context['location_summary'][:200]}...")
                    
                if location_context.get('historical_significance'):
                    print(f"🏛️ History: {location_context['historical_significance'][:150]}...")
                    
                if location_context.get('key_topics'):
                    topics = location_context['key_topics']
                    if isinstance(topics, list):
                        print(f"🏷️ Topics: {', '.join(topics[:5])}")
            
            # Neighborhood context
            neighborhood_context = source.get('neighborhood_context', {})
            if neighborhood_context:
                print(f"\n🏘️ NEIGHBORHOOD INSIGHTS")
                print("="*40)
                print(f"📍 Area: {neighborhood_context.get('wikipedia_title', 'N/A')}")
                
                if neighborhood_context.get('character'):
                    print(f"✨ Character: {neighborhood_context['character'][:120]}...")
                    
                if neighborhood_context.get('notable_residents'):
                    residents = neighborhood_context['notable_residents']
                    if isinstance(residents, list) and residents:
                        print(f"👥 Notable Residents: {', '.join(residents[:3])}")
            
            # Points of Interest
            pois = source.get('nearby_poi', [])
            if pois:
                print(f"\n🗺️ NEARBY POINTS OF INTEREST")
                print("="*40)
                
                # Group POIs by category
                poi_by_category = {}
                for poi in pois:
                    category = poi.get('category', 'Other')
                    if category not in poi_by_category:
                        poi_by_category[category] = []
                    poi_by_category[category].append(poi)
                
                for category, category_pois in list(poi_by_category.items())[:4]:
                    print(f"🏷️ {category}:")
                    for poi in category_pois[:3]:
                        name = poi.get('name', 'Unknown')
                        distance = poi.get('distance_miles', 0)
                        print(f"   • {name} ({distance:.1f} miles)")
            
            # Quality metrics
            location_quality = source.get('location_quality_score', 0)
            desirability = source.get('neighborhood_desirability', 0)
            tourism_potential = source.get('tourism_potential', 0)
            
            if any([location_quality, desirability, tourism_potential]):
                print(f"\n📊 LOCATION METRICS")
                print("="*40)
                if location_quality:
                    print(f"⭐ Location Quality: {location_quality:.1f}/10")
                if desirability:
                    print(f"✨ Neighborhood Desirability: {desirability:.1f}/10")
                if tourism_potential:
                    print(f"🏖️ Tourism Potential: {tourism_potential:.1f}/10")
            
            print(f"\n💡 Search Match Score: {hit.score:.2f}")
            
        except Exception as e:
            print(f"\n📚 Wikipedia enrichment data: Available in search index")
            print(f"   (Demo note: Full data access requires direct ES query)")
    
    def show_wikipedia_coverage(self):
        """Show Wikipedia data coverage statistics."""
        print("\n" + "="*60)
        print("📚 Wikipedia Data Coverage")
        print("="*60)
        
        stats = self.wikipedia_extractor.get_location_statistics()
        print(f"\nTotal Wikipedia articles: {stats['total_articles']}")
        print(f"Unique locations: {stats['unique_locations']}")
        print(f"\nArticles by city:")
        print(f"  San Francisco: {stats['san_francisco_articles']}")
        print(f"  Park City: {stats['park_city_articles']}")
        print(f"  Oakland: {stats['oakland_articles']}")
        print(f"  San Jose: {stats['san_jose_articles']}")


def main():
    """Run the search demo."""
    demo = SearchDemo()
    
    print("\n" + "="*60)
    print("🚀 Wikipedia-Enhanced Property Search Demo")
    print("="*60)
    
    # Check if index already has data
    try:
        count = demo.search_engine.es_client.count(index=demo.search_engine.index_name)
        if count['count'] > 0:
            print(f"\n✅ Using existing index with {count['count']} documents")
        else:
            # Setup index only if empty
            if not demo.setup_demo_index(force_recreate=True):
                print("Failed to set up demo index")
                return
    except:
        # If index doesn't exist, create it
        if not demo.setup_demo_index(force_recreate=True):
            print("Failed to set up demo index")
            return
    
    # Show Wikipedia coverage
    demo.show_wikipedia_coverage()
    
    # Run demos
    demo.demo_park_city_ski_search()
    demo.demo_sf_cultural_search()
    demo.demo_lifestyle_search()
    demo.demo_poi_proximity_search()
    demo.demo_investment_search()
    demo.demo_basic_property_search()
    demo.demo_faceted_search()
    demo.demo_property_listing_with_wikipedia()
    
    print("\n" + "="*60)
    print("✅ Demo Complete!")
    print("="*60)


if __name__ == "__main__":
    main()