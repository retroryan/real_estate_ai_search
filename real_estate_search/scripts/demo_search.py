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
        """Demo: Find ski-accessible properties in Park City."""
        print("\n" + "="*60)
        print("🎿 DEMO 1: Park City Ski Resort Properties")
        print("="*60)
        
        query = "ski resort luxury home near Deer Valley"
        print(f"\nQuery: '{query}'")
        
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
        """Demo: Find properties near cultural venues in San Francisco."""
        print("\n" + "="*60)
        print("🎭 DEMO 2: San Francisco Cultural District Properties")
        print("="*60)
        
        query = "museum arts cultural"
        print(f"\nQuery: '{query}' (Cultural Mode)")
        
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
        """Demo: Lifestyle-based property search."""
        print("\n" + "="*60)
        print("🏡 DEMO 3: Lifestyle-Based Search")
        print("="*60)
        
        query = "park recreation family outdoor"
        print(f"\nQuery: '{query}' (Lifestyle Mode)")
        
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
        """Demo: Find properties near specific POIs."""
        print("\n" + "="*60)
        print("📍 DEMO 4: POI Proximity Search")
        print("="*60)
        
        query = "Park"  # Will match various parks
        print(f"\nQuery: Properties near '{query}' (within 1 mile)")
        
        request = SearchRequest(
            query_text=query,
            search_mode=SearchMode.POI_PROXIMITY,
            filters=SearchFilters(),  # Will use default max_distance_miles in query builder
            size=3
        )
        results = self.search_engine.search(request)
        
        self._display_results(results, show_matching_pois=True)
    
    def demo_investment_search(self):
        """Demo: Investment property search."""
        print("\n" + "="*60)
        print("💰 DEMO 5: Investment Property Search")
        print("="*60)
        
        query = "tourist rental investment"
        print(f"\nQuery: '{query}' (Investment Mode)")
        
        request = SearchRequest(
            query_text=query,
            search_mode=SearchMode.INVESTMENT,
            size=3
        )
        results = self.search_engine.search(request)
        
        self._display_results(results, show_investment_metrics=True)
    
    def demo_faceted_search(self):
        """Demo: Show faceted search capabilities."""
        print("\n" + "="*60)
        print("🔍 DEMO 6: Faceted Search Options")
        print("="*60)
        
        facets = self.search_engine.get_facets(query="park")
        
        print("\n📊 Available Facets:")
        
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
        show_investment_metrics: bool = False
    ):
        """Display search results with various details."""
        print(f"\n📊 Found {results.total} properties")
        
        for i, hit in enumerate(results.hits[:3], 1):
            prop = hit.property
            print(f"\n{i}. Property {prop.listing_id}")
            print(f"   📍 {prop.address.street}, {prop.address.city}")
            print(f"   💰 ${prop.price:,.0f}")
            print(f"   🏠 {prop.bedrooms} bed, {prop.bathrooms} bath, {prop.square_feet:,} sqft" if prop.square_feet else f"   🏠 {prop.bedrooms} bed, {prop.bathrooms} bath")
            
            # Note: Wikipedia data would be in the ES document, not the Property model
            # For demo purposes, we'll skip showing Wikipedia details since they're not directly accessible
            # The data IS indexed and searchable, just not returned in the Property model
            
            if show_wikipedia:
                print(f"   📚 Location data: Available in search index")
            
            if show_pois:
                print(f"   🗺️ POI data: Available in search index")
            
            if show_scores:
                print(f"   ⭐ Location context: Enriched in search index")
            
            if show_matching_pois:
                print(f"   🎯 Nearby POIs: Searchable in index")
            
            if show_investment_metrics:
                print(f"   📈 Investment metrics: Available for ranking")
            
            # Show highlights if available
            if hit.highlights:
                print(f"   💡 Matched in: {', '.join(hit.highlights.keys())}")
    
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
    demo.demo_faceted_search()
    
    print("\n" + "="*60)
    print("✅ Demo Complete!")
    print("="*60)


if __name__ == "__main__":
    main()