"""
Elasticsearch index management CLI for real estate search system.
Main entry point for index creation, validation, and management operations.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, Any
import json

from .config import AppConfig
from .infrastructure.elasticsearch_client import ElasticsearchClientFactory, ElasticsearchClient
from .indexer.index_manager import ElasticsearchIndexManager, IndexStatus
from .indexer.enums import IndexName
from .demo_queries import (
    demo_basic_property_search,
    demo_property_filter,
    demo_geo_search,
    demo_neighborhood_stats,
    demo_price_distribution,
    demo_semantic_search,
    demo_multi_entity_search,
    demo_wikipedia_search,
    demo_relationship_search,
    demo_wikipedia_fulltext
)


def setup_logging(log_level: str = "INFO"):
    """Configure logging for the management operations."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


class IndexManagementCLI:
    """
    Command-line interface for Elasticsearch index management.
    Provides commands for index setup, validation, and monitoring.
    """
    
    def __init__(self, config: AppConfig):
        """
        Initialize CLI with configuration.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize Elasticsearch components
        self._init_elasticsearch()
    
    def _init_elasticsearch(self):
        """Initialize Elasticsearch client and index manager."""
        try:
            # Create client factory and client
            client_factory = ElasticsearchClientFactory(self.config.elasticsearch)
            raw_client = client_factory.create_client()
            
            # Create enhanced client and index manager
            self.es_client = ElasticsearchClient(raw_client)
            self.index_manager = ElasticsearchIndexManager(raw_client)
            
            self.logger.info("Elasticsearch components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Elasticsearch: {str(e)}")
            sys.exit(1)
    
    def setup_indices(self, clear: bool = False) -> bool:
        """
        Create all indices with proper mappings.
        
        Args:
            clear: If True, delete existing indices first (for demo reset)
        
        Returns:
            True if all indices were set up successfully
        """
        if clear:
            self.logger.info("Clear flag set - deleting existing indices first...")
            print("\n🗑️  Clearing existing indices for demo reset...")
            
            # Delete all managed indices
            indices_to_delete = [
                IndexName.PROPERTIES, IndexName.TEST_PROPERTIES,
                IndexName.NEIGHBORHOODS, IndexName.TEST_NEIGHBORHOODS,
                IndexName.WIKIPEDIA, IndexName.TEST_WIKIPEDIA
            ]
            for index_name in indices_to_delete:
                try:
                    if self.es_client.client.indices.exists(index=index_name):
                        self.es_client.delete_index(index_name)
                        print(f"   ✓ Deleted {index_name}")
                        self.logger.info(f"Deleted index: {index_name}")
                    else:
                        print(f"   - {index_name} doesn't exist, skipping")
                except Exception as e:
                    print(f"   ✗ Failed to delete {index_name}: {str(e)}")
                    self.logger.error(f"Failed to delete {index_name}: {str(e)}")
            
            print("")  # Add blank line for readability
        
        self.logger.info("Setting up Elasticsearch indices...")
        
        try:
            results = self.index_manager.setup_all_indices()
            
            # Print results
            print("\nIndex Setup Results:")
            print("=" * 50)
            
            all_successful = True
            for name, success in results.items():
                status = "✓ SUCCESS" if success else "✗ FAILED"
                print(f"{name:30} {status}")
                if not success:
                    all_successful = False
            
            print("=" * 50)
            
            if all_successful:
                print("✓ All indices set up successfully!")
                self.logger.info("All indices set up successfully")
            else:
                print("✗ Some indices failed to set up")
                self.logger.error("Some indices failed to set up")
            
            return all_successful
            
        except Exception as e:
            self.logger.error(f"Failed to setup indices: {str(e)}")
            print(f"✗ Error setting up indices: {str(e)}")
            return False
    
    def validate_indices(self) -> bool:
        """
        Validate that all indices exist with correct mappings.
        
        Returns:
            True if all validations pass
        """
        self.logger.info("Validating Elasticsearch indices...")
        
        try:
            statuses = self.index_manager.list_all_indices()
            
            # Print validation results
            print("\nIndex Validation Results:")
            print("=" * 70)
            print(f"{'Index Name':20} {'Exists':8} {'Health':8} {'Docs':8} {'Mappings':10}")
            print("=" * 70)
            
            all_valid = True
            for status in statuses:
                exists_str = "✓" if status.exists else "✗"
                health_str = status.health if status.exists else "N/A"
                docs_str = str(status.docs_count) if status.exists else "N/A"
                mappings_str = "✓" if status.mapping_valid else "✗"
                
                print(f"{status.name:20} {exists_str:8} {health_str:8} {docs_str:8} {mappings_str:10}")
                
                if not status.exists or not status.mapping_valid:
                    all_valid = False
                    if status.error_message:
                        print(f"  Error: {status.error_message}")
            
            print("=" * 70)
            
            if all_valid:
                print("✓ All indices are valid!")
                self.logger.info("All indices validation passed")
            else:
                print("✗ Some indices have validation issues")
                self.logger.warning("Some indices failed validation")
            
            return all_valid
            
        except Exception as e:
            self.logger.error(f"Failed to validate indices: {str(e)}")
            print(f"✗ Error validating indices: {str(e)}")
            return False
    
    def list_indices(self) -> bool:
        """
        Show current status of all indices.
        
        Returns:
            True if listing was successful
        """
        self.logger.info("Listing Elasticsearch indices...")
        
        try:
            statuses = self.index_manager.list_all_indices()
            
            # Print detailed status
            print("\nElasticsearch Index Status:")
            print("=" * 80)
            
            for status in statuses:
                print(f"\nIndex: {status.name}")
                print(f"  Exists: {'✓ Yes' if status.exists else '✗ No'}")
                
                if status.exists:
                    print(f"  Health: {status.health}")
                    print(f"  Documents: {status.docs_count:,}")
                    print(f"  Store Size: {self._format_bytes(status.store_size_bytes)}")
                    print(f"  Mappings Valid: {'✓ Yes' if status.mapping_valid else '✗ No'}")
                else:
                    if status.error_message:
                        print(f"  Error: {status.error_message}")
            
            print("=" * 80)
            
            # Get cluster health
            cluster_health = self.es_client.get_cluster_health()
            print(f"\nCluster Status: {cluster_health['status']}")
            print(f"Number of Nodes: {cluster_health['number_of_nodes']}")
            print(f"Active Primary Shards: {cluster_health['active_primary_shards']}")
            print(f"Active Shards: {cluster_health['active_shards']}")
            
            self.logger.info("Successfully listed all indices")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to list indices: {str(e)}")
            print(f"✗ Error listing indices: {str(e)}")
            return False
    
    def validate_embeddings(self) -> bool:
        """
        Validate that embeddings have been properly generated for all entity types.
        
        Checks:
        - Document counts for each entity type
        - Percentage of documents with embeddings
        - Embedding dimensions consistency
        - Embedding model consistency
        
        Returns:
            True if embedding validation passes
        """
        self.logger.info("Validating vector embeddings across all entity types...")
        
        try:
            # Entity types and their expected indices
            entity_indices = {
                "properties": IndexName.PROPERTIES,
                "neighborhoods": IndexName.NEIGHBORHOODS, 
                "wikipedia": IndexName.WIKIPEDIA
            }
            
            print("\nVector Embedding Validation Results:")
            print("=" * 80)
            print(f"{'Entity Type':15} {'Total Docs':12} {'With Embeddings':15} {'Percentage':12} {'Dimension':10} {'Model':15}")
            print("-" * 80)
            
            overall_valid = True
            total_docs = 0
            total_with_embeddings = 0
            
            for entity_type, index_name in entity_indices.items():
                try:
                    # Check if index exists
                    if not self.es_client.client.indices.exists(index=index_name):
                        print(f"{entity_type:15} {'N/A':12} {'INDEX MISSING':15} {'N/A':12} {'N/A':10} {'N/A':15}")
                        overall_valid = False
                        continue
                    
                    # Get total document count
                    total_count_result = self.es_client.client.count(index=index_name)
                    total_count = total_count_result['count']
                    
                    # Count documents with embeddings
                    embedding_query = {
                        "query": {
                            "bool": {
                                "must": [
                                    {"exists": {"field": "embedding"}},
                                    {"exists": {"field": "embedding_model"}},
                                    {"exists": {"field": "embedding_dimension"}}
                                ]
                            }
                        }
                    }
                    
                    embedding_count_result = self.es_client.client.count(
                        index=index_name, 
                        body=embedding_query
                    )
                    embedding_count = embedding_count_result['count']
                    
                    # Calculate percentage
                    percentage = (embedding_count / total_count * 100) if total_count > 0 else 0
                    
                    # Get sample embedding metadata
                    dimension = "N/A"
                    model = "N/A"
                    
                    if embedding_count > 0:
                        sample_query = {
                            "query": {
                                "bool": {
                                    "must": [{"exists": {"field": "embedding"}}]
                                }
                            },
                            "size": 1,
                            "_source": ["embedding_dimension", "embedding_model"]
                        }
                        
                        sample_result = self.es_client.client.search(
                            index=index_name,
                            body=sample_query
                        )
                        
                        if sample_result['hits']['hits']:
                            hit = sample_result['hits']['hits'][0]['_source']
                            dimension = hit.get('embedding_dimension', 'N/A')
                            model = hit.get('embedding_model', 'N/A')
                    
                    # Determine status
                    status_color = ""
                    if percentage >= 95:
                        status_color = "✓"
                    elif percentage >= 80:
                        status_color = "⚠"
                    else:
                        status_color = "✗"
                        overall_valid = False
                    
                    print(f"{entity_type:15} {total_count:12,} {embedding_count:15,} {percentage:10.1f}% {str(dimension):10} {str(model):15}")
                    
                    total_docs += total_count
                    total_with_embeddings += embedding_count
                    
                except Exception as e:
                    print(f"{entity_type:15} {'ERROR':12} {str(e)[:15]:15} {'N/A':12} {'N/A':10} {'N/A':15}")
                    self.logger.error(f"Error validating embeddings for {entity_type}: {e}")
                    overall_valid = False
            
            print("-" * 80)
            
            # Overall statistics
            overall_percentage = (total_with_embeddings / total_docs * 100) if total_docs > 0 else 0
            print(f"{'TOTAL':15} {total_docs:12,} {total_with_embeddings:15,} {overall_percentage:10.1f}%")
            print("=" * 80)
            
            if overall_valid and overall_percentage >= 95:
                print("✓ Vector embedding validation PASSED - All entity types have sufficient embeddings")
                self.logger.info(f"Embedding validation passed: {overall_percentage:.1f}% coverage")
            elif overall_percentage >= 80:
                print("⚠ Vector embedding validation PARTIAL - Some entities have low embedding coverage")
                self.logger.warning(f"Embedding validation partial: {overall_percentage:.1f}% coverage")
                overall_valid = False
            else:
                print("✗ Vector embedding validation FAILED - Insufficient embedding coverage")
                self.logger.error(f"Embedding validation failed: {overall_percentage:.1f}% coverage")
                overall_valid = False
            
            print("\nRecommendations:")
            if overall_percentage < 95:
                print("- Run the data pipeline with embedding generation enabled")
                print("- Check embedding provider configuration (API keys, etc.)")
                print("- Verify embedding generation didn't fail during pipeline execution")
            else:
                print("- Embedding coverage is excellent - ready for semantic search")
            
            return overall_valid
            
        except Exception as e:
            self.logger.error(f"Failed to validate embeddings: {str(e)}")
            print(f"✗ Error validating embeddings: {str(e)}")
            return False

    def delete_indices(self, index_names: list = None) -> bool:
        """
        Delete specified indices or all test indices.
        
        Args:
            index_names: List of index names to delete, or None for test indices only
            
        Returns:
            True if deletion was successful
        """
        if index_names is None:
            index_names = [IndexName.TEST_PROPERTIES]
        
        self.logger.info(f"Deleting indices: {index_names}")
        
        try:
            results = {}
            for index_name in index_names:
                try:
                    results[index_name] = self.index_manager.delete_index(index_name)
                except Exception as e:
                    results[index_name] = False
                    self.logger.error(f"Failed to delete {index_name}: {str(e)}")
            
            # Print results
            print("\nIndex Deletion Results:")
            print("=" * 50)
            
            all_successful = True
            for name, success in results.items():
                status = "✓ DELETED" if success else "✗ FAILED"
                print(f"{name:30} {status}")
                if not success:
                    all_successful = False
            
            print("=" * 50)
            
            if all_successful:
                print("✓ All indices deleted successfully!")
                self.logger.info("All specified indices deleted successfully")
            else:
                print("✗ Some indices failed to delete")
                self.logger.error("Some indices failed to delete")
            
            return all_successful
            
        except Exception as e:
            self.logger.error(f"Failed to delete indices: {str(e)}")
            print(f"✗ Error deleting indices: {str(e)}")
            return False
    
    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes into human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_count < 1024:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024
        return f"{bytes_count:.1f} TB"
    
    def run_demo_query(self, demo_number: int, verbose: bool = False) -> bool:
        """
        Run a specific demo query.
        
        Args:
            demo_number: Demo query number to run (1-8)
            verbose: If True, show detailed query DSL
            
        Returns:
            True if query executed successfully
        """
        # Map demo numbers to functions
        demo_queries = {
            1: (demo_basic_property_search, "Basic Property Search"),
            2: (demo_property_filter, "Property Filter Search"),
            3: (demo_geo_search, "Geographic Distance Search"),
            4: (demo_neighborhood_stats, "Neighborhood Statistics"),
            5: (demo_price_distribution, "Price Distribution Analysis"),
            6: (demo_semantic_search, "Semantic Similarity Search"),
            7: (demo_multi_entity_search, "Multi-Entity Combined Search"),
            8: (demo_wikipedia_search, "Wikipedia Article Search"),
            9: (demo_relationship_search, "Property-Neighborhood-Wikipedia Relationships"),
            10: (demo_wikipedia_fulltext, "Wikipedia Full-Text Search")
        }
        
        if demo_number not in demo_queries:
            print(f"✗ Invalid demo number: {demo_number}")
            print(f"Available demos: {', '.join(str(k) for k in demo_queries.keys())}")
            return False
        
        query_func, query_name = demo_queries[demo_number]
        
        try:
            print(f"\nRunning Demo {demo_number}: {query_name}")
            print("=" * 60)
            
            # Add special descriptions for specific demos
            if demo_number == 9:
                print("\n📊 Query Architecture Overview:")
                print("-" * 50)
                print("This demo performs three types of relationship queries:\n")
                print("1️⃣  Property → Neighborhood → Wikipedia")
                print("   Starting from a property, finds its neighborhood and related articles")
            elif demo_number == 10:
                print("\n🔍 Full-Text Search Overview:")
                print("-" * 50)
                print("This demo showcases Wikipedia full-text search after HTML enrichment:\n")
                print("• Searches across complete Wikipedia article content")
                print("• Demonstrates various query patterns and operators")
                print("• Shows highlighted relevant content from articles")
                print("   Shows: Property details, neighborhood context, location Wikipedia")
                print()
                print("2️⃣  Neighborhood → Properties + Wikipedia") 
                print("   Shows all properties in a neighborhood plus Wikipedia context")
                print("   Example: Pacific Heights with all its properties and articles")
                print()
                print("3️⃣  Location → Properties + Wikipedia")
                print("   City-level search combining real estate and encyclopedia data")
                print("   Example: All San Francisco properties with city Wikipedia articles")
                print()
                print("🔗 Relationships established through:")
                print("   • neighborhood_id field linking properties to neighborhoods")
                print("   • Location matching between Wikipedia and property/neighborhood data")
                print("   • Confidence scoring (primary=95%, neighborhood=85%, park=90%, etc.)")
                print("=" * 60)
            
            # Execute the demo query
            result = query_func(self.es_client.client)
            
            # Display results
            print(result.display(verbose=verbose))
            
            self.logger.info(f"Successfully executed demo {demo_number}: {query_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to execute demo {demo_number}: {str(e)}")
            print(f"✗ Error executing demo: {str(e)}")
            return False
    
    def list_demo_queries(self) -> bool:
        """
        List all available demo queries with descriptions.
        
        Returns:
            True always
        """
        print("\nAvailable Demo Queries:")
        print("=" * 70)
        
        demos = [
            (1, "Basic Property Search", "Multi-match search across property fields"),
            (2, "Property Filter Search", "Filter by type, bedrooms, price, location"),
            (3, "Geographic Distance Search", "Find properties within radius of point"),
            (4, "Neighborhood Statistics", "Aggregate property stats by neighborhood"),
            (5, "Price Distribution Analysis", "Histogram of prices by property type"),
            (6, "Semantic Similarity Search", "Find similar properties using embeddings"),
            (7, "Multi-Entity Combined Search", "Search across all entity types"),
            (8, "Wikipedia Article Search", "Search Wikipedia with location filters"),
            (9, "Property-Neighborhood-Wikipedia Relationships", "Demonstrates entity linking across indices")
        ]
        
        for num, name, description in demos:
            print(f"  {num}. {name}")
            print(f"     {description}")
            print()
        
        print("=" * 70)
        print("\nUsage: python -m real_estate_search.management demo <number>")
        print("Example: python -m real_estate_search.management demo 1")
        print("\nAdd --verbose flag to see the actual Elasticsearch query DSL")
        
        return True


def main():
    """Main entry point for index management CLI."""
    parser = argparse.ArgumentParser(
        description="Elasticsearch Index Management for Real Estate Search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m real_estate_search.management setup-indices
  python -m real_estate_search.management setup-indices --clear    # Reset and recreate indices
  python -m real_estate_search.management validate-indices
  python -m real_estate_search.management validate-embeddings     # Check vector embedding coverage
  python -m real_estate_search.management list-indices
  python -m real_estate_search.management delete-test-indices
  python -m real_estate_search.management demo --list           # List all demo queries
  python -m real_estate_search.management demo 1                # Run demo query 1
  python -m real_estate_search.management demo 2 --verbose      # Run demo 2 with query DSL
        """
    )
    
    parser.add_argument(
        'command',
        choices=['setup-indices', 'validate-indices', 'validate-embeddings', 'list-indices', 'delete-test-indices', 'demo'],
        help='Management command to execute'
    )
    
    parser.add_argument(
        'demo_number',
        type=int,
        nargs='?',
        choices=range(1, 11),
        help='Demo query number to run (1-10)'
    )
    
    parser.add_argument(
        '--clear',
        action='store_true',
        help='For setup-indices: Delete existing indices first (complete reset for demo)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='For demo: List all available demo queries'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='For demo: Show detailed query DSL'
    )
    
    parser.add_argument(
        '--config',
        type=Path,
        default=Path("config.yaml"),
        help='Configuration file path (default: config.yaml)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = AppConfig.from_yaml(args.config)
        
        # Override log level if specified
        if args.log_level:
            config.logging.level = args.log_level.upper()
        
        # Initialize CLI
        cli = IndexManagementCLI(config)
        
        # Execute command
        success = False
        if args.command == 'setup-indices':
            success = cli.setup_indices(clear=args.clear)
        elif args.command == 'validate-indices':
            success = cli.validate_indices()
        elif args.command == 'validate-embeddings':
            success = cli.validate_embeddings()
        elif args.command == 'list-indices':
            success = cli.list_indices()
        elif args.command == 'delete-test-indices':
            success = cli.delete_indices([IndexName.TEST_PROPERTIES])
        elif args.command == 'demo':
            if args.list:
                success = cli.list_demo_queries()
            elif args.demo_number:
                success = cli.run_demo_query(args.demo_number, verbose=args.verbose)
            else:
                print("Please specify a demo number (1-9) or use --list to see available demos")
                print("Example: python -m real_estate_search.management demo 1")
                success = False
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"✗ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()