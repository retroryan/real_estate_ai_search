#!/usr/bin/env python3
"""
Search properties using hybrid vector and graph search.
Requires embeddings to be created first with create_embeddings.py
"""
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.append(str(Path(__file__).parent))

from vectors import PropertyEmbeddingPipeline, HybridPropertySearch
from vectors.hybrid_search import SearchResult
from vectors.config_loader import get_embedding_config, get_vector_index_config, get_search_config
from database.neo4j_client import get_neo4j_driver, close_neo4j_driver


def print_result(result: SearchResult, index: int):
    """Pretty print a search result"""
    print(f"\n{index}. Property {result.listing_id}")
    print("   " + "-" * 50)
    if result.address:
        print(f"   Address: {result.address}")
    print(f"   Location: {result.neighborhood}, {result.city}")
    print(f"   Price: ${result.price:,.0f}")
    
    if result.bedrooms or result.bathrooms or result.square_feet:
        details = []
        if result.bedrooms:
            details.append(f"{result.bedrooms} bed")
        if result.bathrooms:
            details.append(f"{result.bathrooms} bath")
        if result.square_feet:
            details.append(f"{result.square_feet} sqft")
        print(f"   Details: {' | '.join(details)}")
    
    print(f"   Scores: Vector={result.vector_score:.3f}, Graph={result.graph_score:.3f}, Combined={result.combined_score:.3f}")
    
    if result.features and len(result.features) > 0:
        print(f"   Features: {', '.join(result.features[:5])}")
    
    if result.similar_properties:
        print(f"   Similar: {', '.join(result.similar_properties[:3])}")


def main():
    """Main function for property search"""
    parser = argparse.ArgumentParser(
        description="Search properties using vector embeddings and graph relationships"
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="",
        help="Natural language search query (not required with --demo)"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results to return (default: 5)"
    )
    parser.add_argument(
        "--no-graph-boost",
        action="store_true",
        help="Disable graph relationship boosting"
    )
    
    # Filter arguments
    parser.add_argument("--price-min", type=float, help="Minimum price")
    parser.add_argument("--price-max", type=float, help="Maximum price")
    parser.add_argument("--city", help="Filter by city")
    parser.add_argument("--neighborhood", help="Filter by neighborhood")
    parser.add_argument("--bedrooms-min", type=int, help="Minimum bedrooms")
    parser.add_argument("--bathrooms-min", type=float, help="Minimum bathrooms")
    parser.add_argument("--sqft-min", type=int, help="Minimum square feet")
    
    # Demo mode
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demo with predefined queries"
    )
    
    args = parser.parse_args()
    
    driver = None
    try:
        # Load configuration
        embedding_config = get_embedding_config()
        vector_config = get_vector_index_config()
        search_config = get_search_config()
        
        # Connect to Neo4j
        print("Connecting to Neo4j...")
        driver = get_neo4j_driver()
        
        # Create pipeline and search
        print("Initializing search pipeline...")
        # Clean initialization - embedding config handles model selection
        pipeline = PropertyEmbeddingPipeline(driver, embedding_config)
        search = HybridPropertySearch(driver, pipeline, search_config)
        
        # Check if embeddings exist
        status = pipeline.vector_manager.check_embeddings_exist()
        if status['with_embeddings'] == 0:
            print("\nWarning: No embeddings found! Run 'python create_embeddings.py' first.")
            return 1
        
        print(f"Ready to search {status['with_embeddings']} properties with embeddings\n")
        
        if args.demo:
            # Demo mode with multiple queries
            demo_queries = [
                "Modern condo with city views",
                "Family home with good schools nearby",
                "Luxury property with high-end features",
                "Affordable starter home",
                "Property near parks and recreation"
            ]
            
            print("=" * 60)
            print("DEMO MODE - Testing Multiple Queries")
            print("=" * 60)
            
            for query in demo_queries:
                print(f"\nQuery: '{query}'")
                print("=" * 60)
                
                results = search.search(
                    query=query,
                    top_k=3,
                    use_graph_boost=not args.no_graph_boost
                )
                
                if results:
                    for i, result in enumerate(results, 1):
                        print_result(result, i)
                else:
                    print("   No results found")
        else:
            # Single query mode
            # Build filters
            filters = {}
            if args.price_min:
                filters['price_min'] = args.price_min
            if args.price_max:
                filters['price_max'] = args.price_max
            if args.city:
                filters['city'] = args.city
            if args.neighborhood:
                filters['neighborhood'] = args.neighborhood
            if args.bedrooms_min:
                filters['bedrooms_min'] = args.bedrooms_min
            if args.bathrooms_min:
                filters['bathrooms_min'] = args.bathrooms_min
            if args.sqft_min:
                filters['square_feet_min'] = args.sqft_min
            
            # Perform search
            print(f"Searching for: '{args.query}'")
            if filters:
                print(f"   Filters: {json.dumps(filters, indent=2)}")
            print("=" * 60)
            
            results = search.search(
                query=args.query,
                filters=filters if filters else None,
                top_k=args.top_k,
                use_graph_boost=not args.no_graph_boost
            )
            
            if results:
                print(f"\nFound {len(results)} results:")
                for i, result in enumerate(results, 1):
                    print_result(result, i)
            else:
                print("\nNo results found matching your query")
                if filters:
                    print("Try removing some filters to get more results")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\nError: Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if driver:
            close_neo4j_driver()


if __name__ == "__main__":
    sys.exit(main())