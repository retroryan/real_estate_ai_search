"""Example usage of the API Client Factory and clients."""

import logging
from common.api_client import APIClientFactory


def main():
    """Demonstrate API client usage patterns."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Method 1: Create factory for local development
    factory = APIClientFactory.for_local_development(port=8000)
    
    # Method 2: Create factory from configuration file
    # factory = APIClientFactory.from_yaml("config/api_config.yaml")
    
    # Method 3: Create factory from environment variables
    # factory = APIClientFactory.from_env(env_prefix="API")
    
    # Method 4: Create factory for production
    # factory = APIClientFactory.for_production(
    #     api_url="https://api.example.com",
    #     api_key="your-api-key",
    #     timeout=60
    # )
    
    # Check API health
    print("\n=== Checking API Health ===")
    if factory.check_health():
        print("✅ API is healthy and ready")
    else:
        print("❌ API is not available")
        return
    
    # Example 1: Get properties
    print("\n=== Fetching Properties ===")
    try:
        properties = factory.property_client.get_properties(
            city="San Francisco",
            page=1,
            page_size=5
        )
        print(f"Found {len(properties)} properties in San Francisco")
        
        if properties:
            prop = properties[0]
            print(f"Sample property: {prop.listing_id} - ${prop.price:,.0f}")
            print(f"  Address: {prop.address.street}, {prop.address.city}")
            print(f"  Type: {prop.property_type}")
    except Exception as e:
        print(f"Error fetching properties: {e}")
    
    # Example 2: Get neighborhoods
    print("\n=== Fetching Neighborhoods ===")
    try:
        neighborhoods = factory.property_client.get_neighborhoods(
            city="Park City",
            page=1,
            page_size=3
        )
        print(f"Found {len(neighborhoods)} neighborhoods in Park City")
        
        for neighborhood in neighborhoods:
            print(f"  - {neighborhood.name}: {neighborhood.poi_count} POIs")
    except Exception as e:
        print(f"Error fetching neighborhoods: {e}")
    
    # Example 3: Get Wikipedia articles
    print("\n=== Fetching Wikipedia Articles ===")
    try:
        articles = factory.wikipedia_client.get_articles(
            state="Utah",
            relevance_min=0.7,
            sort_by="relevance",
            page_size=3
        )
        print(f"Found {len(articles)} high-relevance articles about Utah")
        
        for article in articles:
            print(f"  - {article.title} (relevance: {article.relevance_score:.2f})")
    except Exception as e:
        print(f"Error fetching Wikipedia articles: {e}")
    
    # Example 4: Get statistics
    print("\n=== Fetching Statistics ===")
    try:
        summary_stats = factory.stats_client.get_summary_stats()
        print(f"Total properties: {summary_stats.total_properties}")
        print(f"Total neighborhoods: {summary_stats.total_neighborhoods}")
        print(f"Unique cities: {summary_stats.unique_cities}")
        print(f"Unique states: {summary_stats.unique_states}")
        
        if summary_stats.price_range:
            print(f"Price range: ${summary_stats.price_range['min']:,.0f} - ${summary_stats.price_range['max']:,.0f}")
    except Exception as e:
        print(f"Error fetching statistics: {e}")
    
    # Example 5: Pagination example
    print("\n=== Pagination Example ===")
    try:
        print("Fetching all properties in batches...")
        total_properties = 0
        
        for batch in factory.property_client.get_all_properties(page_size=10):
            total_properties += len(batch)
            print(f"  Fetched batch with {len(batch)} properties (total so far: {total_properties})")
            
            # Process first 3 batches only for demo
            if total_properties >= 30:
                break
    except Exception as e:
        print(f"Error during pagination: {e}")
    
    # Example 6: Get detailed statistics
    print("\n=== Detailed Statistics ===")
    try:
        # Property statistics
        property_stats = factory.stats_client.get_property_stats()
        print(f"Properties by type:")
        for prop_type, count in list(property_stats.by_type.items())[:3]:
            print(f"  - {prop_type}: {count}")
        
        # Coverage statistics
        coverage_stats = factory.stats_client.get_coverage_stats()
        print(f"\nTop cities by data coverage:")
        for city_info in coverage_stats.top_cities_by_data[:3]:
            print(f"  - {city_info['city']}: {city_info['total_data_points']} data points")
    except Exception as e:
        print(f"Error fetching detailed statistics: {e}")
    
    # Example 7: Error handling
    print("\n=== Error Handling Example ===")
    try:
        # Try to get a non-existent property
        property = factory.property_client.get_property_by_id("invalid-id-12345")
    except Exception as e:
        print(f"Expected error handled: {type(e).__name__}: {e}")
    
    print("\n✅ API client examples completed successfully!")


if __name__ == "__main__":
    main()