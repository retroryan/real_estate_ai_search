#!/usr/bin/env python3
"""
Create vector embeddings for properties in the Neo4j graph database.
Run this after building the graph with main.py
"""
import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.vectors import PropertyEmbeddingPipeline
from src.vectors.config_loader import get_embedding_config, get_vector_index_config
from src.database.neo4j_client import get_neo4j_driver, close_neo4j_driver


def main():
    """Main function to create property embeddings"""
    parser = argparse.ArgumentParser(
        description="Generate vector embeddings for properties in Neo4j using settings from config.yaml"
    )
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Delete existing embeddings and recreate from scratch"
    )
    
    args = parser.parse_args()
    
    driver = None
    try:
        # Load configuration from config.yaml
        print("Loading configuration from config.yaml...")
        embedding_config = get_embedding_config()
        vector_config = get_vector_index_config()
        
        # Connect to Neo4j
        print("\nConnecting to Neo4j...")
        driver = get_neo4j_driver()
        
        # Create embedding pipeline
        print("Initializing embedding pipeline...")
        pipeline = PropertyEmbeddingPipeline(driver, embedding_config, vector_config)
        
        # Create vector index
        print("\nCreating vector index...")
        if pipeline.vector_manager.create_vector_index():
            print("Vector index ready")
        else:
            print("Failed to create vector index")
            return 1
        
        # Process properties
        print("\nGenerating embeddings...")
        stats = pipeline.process_properties(force_recreate=args.force_recreate)
        
        # Print final summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total properties: {stats['total']}")
        print(f"Successfully processed: {stats['processed']}")
        if stats['existing'] > 0:
            print(f"Already had embeddings: {stats['existing']}")
        if stats['errors'] > 0:
            print(f"Errors: {stats['errors']}")
        print(f"Time taken: {stats['time']:.2f} seconds")
        if stats['rate'] > 0:
            print(f"Processing rate: {stats['rate']:.1f} properties/second")
        
        return 0 if stats['errors'] == 0 else 1
        
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
            close_neo4j_driver(driver)
            print("\nClosed Neo4j connection")


if __name__ == "__main__":
    sys.exit(main())