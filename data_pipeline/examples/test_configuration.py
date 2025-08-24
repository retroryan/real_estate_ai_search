"""
Test script to verify multi-destination configuration is working.
"""

import json
from pathlib import Path
from data_pipeline.config.settings import ConfigurationManager


def main():
    """Test configuration loading and display."""
    
    print("=" * 60)
    print("Testing Multi-Destination Configuration")
    print("=" * 60)
    
    # Load configuration
    config_manager = ConfigurationManager()
    config = config_manager.load_config()
    
    # Display basic info
    print(f"\nPipeline: {config.metadata.name} v{config.metadata.version}")
    print(f"Environment: {config_manager.environment}")
    
    # Check output destinations
    if hasattr(config, 'output_destinations'):
        print("\n✅ Output destinations configuration found!")
        
        destinations = config.output_destinations
        print(f"\nEnabled destinations: {destinations.enabled_destinations}")
        
        # Display each destination config
        print("\n--- Parquet Configuration ---")
        print(f"  Enabled: {destinations.parquet.enabled}")
        print(f"  Path: {destinations.parquet.path}")
        print(f"  Compression: {destinations.parquet.compression}")
        print(f"  Partitioning: {destinations.parquet.partitioning_columns}")
        
        print("\n--- Neo4j Configuration ---")
        print(f"  Enabled: {destinations.neo4j.enabled}")
        print(f"  URI: {destinations.neo4j.uri}")
        print(f"  Username: {destinations.neo4j.username}")
        print(f"  Database: {destinations.neo4j.database}")
        print(f"  Clear before write: {destinations.neo4j.clear_before_write}")
        
        print("\n--- Elasticsearch Configuration ---")
        print(f"  Enabled: {destinations.elasticsearch.enabled}")
        print(f"  Hosts: {destinations.elasticsearch.hosts}")
        print(f"  Index prefix: {destinations.elasticsearch.index_prefix}")
        print(f"  Bulk size: {destinations.elasticsearch.bulk_size}")
        print(f"  Clear before write: {destinations.elasticsearch.clear_before_write}")
        
    else:
        print("\n❌ Output destinations configuration not found")
    
    # Display effective configuration summary
    print("\n" + "=" * 60)
    print("Effective Configuration Summary")
    print("=" * 60)
    summary = config_manager.get_effective_config_summary()
    print(json.dumps(summary, indent=2))
    
    print("\n✅ Configuration test completed successfully!")


if __name__ == "__main__":
    main()