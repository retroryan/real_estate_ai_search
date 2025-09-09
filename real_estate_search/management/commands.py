"""
Command classes for CLI operations.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path

from ..config import AppConfig
from ..infrastructure.elasticsearch_client import ElasticsearchClientFactory, ElasticsearchClient
from ..indexer.index_manager import ElasticsearchIndexManager
from ..indexer.enums import IndexName
from ..indexer import WikipediaIndexer
from ..indexer.wikipedia_indexer import (
    WikipediaEnrichmentConfig,
    WikipediaEnrichmentResult
)
from .models import (
    CLIArguments, 
    OperationStatus
)
from .index_operations import IndexOperations
from .validation import ValidationService
from .demo_runner import DemoRunner
from .cli_output import CLIOutput


class BaseCommand(ABC):
    """Base class for all CLI commands."""
    
    def __init__(self, config: AppConfig, args: CLIArguments):
        """
        Initialize command with configuration.
        
        Args:
            config: Application configuration
            args: CLI arguments
        """
        self.config = config
        self.args = args
        self.logger = logging.getLogger(self.__class__.__name__)
        self.output = CLIOutput()
        
        # Initialize Elasticsearch components
        self._init_elasticsearch()
    
    def _init_elasticsearch(self):
        """Initialize Elasticsearch client and related components."""
        try:
            # Load environment variables for auth
            import os
            from dotenv import load_dotenv
            from pathlib import Path
            
            # Load .env from parent directory
            env_path = Path(__file__).parent.parent.parent / '.env'
            if env_path.exists():
                load_dotenv(env_path)
            
            # Create client factory and client
            client_factory = ElasticsearchClientFactory(self.config.elasticsearch)
            raw_client = client_factory.create_client()
            
            # Store raw client for commands that need it
            self.raw_es_client = raw_client
            
            # Create enhanced client and index manager
            self.es_client = ElasticsearchClient(raw_client)
            self.index_manager = ElasticsearchIndexManager(raw_client)
            
            # Create service objects
            self.index_operations = IndexOperations(self.es_client, self.index_manager)
            self.validation_service = ValidationService(self.es_client, self.index_operations)
            
            self.logger.info("Elasticsearch components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Elasticsearch: {str(e)}")
            raise
    
    @abstractmethod
    def execute(self) -> OperationStatus:
        """
        Execute the command.
        
        Returns:
            Operation status
        """
        pass


class SetupIndicesCommand(BaseCommand):
    """Command to set up Elasticsearch indices."""
    
    def execute(self) -> OperationStatus:
        """Execute index setup."""
        try:
            results = self.index_operations.setup_indices(
                clear=self.args.clear,
                build_relationships=self.args.build_relationships
            )
            self.output.print_index_setup_results(results, clear=self.args.clear)
            
            all_successful = all(r.success for r in results if "reset" not in r.message.lower())
            
            # Update success message if relationships were built
            success_msg = "All indices set up successfully"
            if self.args.build_relationships and all_successful:
                success_msg += " and property relationships built"
            
            return OperationStatus(
                operation="setup-indices",
                success=all_successful,
                message=success_msg if all_successful else "Some operations failed"
            )
        except Exception as e:
            self.logger.error(f"Failed to setup indices: {str(e)}")
            print(f"✗ Error setting up indices: {str(e)}")
            return OperationStatus(
                operation="setup-indices",
                success=False,
                message=f"Failed to setup indices: {str(e)}"
            )


class ValidateIndicesCommand(BaseCommand):
    """Command to validate indices."""
    
    def execute(self) -> OperationStatus:
        """Execute index validation."""
        try:
            all_valid, statuses = self.validation_service.validate_indices()
            self.output.print_validation_results(all_valid, statuses)
            
            return OperationStatus(
                operation="validate-indices",
                success=all_valid,
                message="All indices are valid" if all_valid else "Some indices have validation issues"
            )
        except Exception as e:
            self.logger.error(f"Failed to validate indices: {str(e)}")
            print(f"✗ Error validating indices: {str(e)}")
            return OperationStatus(
                operation="validate-indices",
                success=False,
                message=f"Failed to validate indices: {str(e)}"
            )


class ValidateEmbeddingsCommand(BaseCommand):
    """Command to validate embeddings."""
    
    def execute(self) -> OperationStatus:
        """Execute embedding validation."""
        try:
            overall_valid, results, overall_percentage = self.validation_service.validate_embeddings()
            self.output.print_embedding_validation_results(overall_valid, results, overall_percentage)
            
            return OperationStatus(
                operation="validate-embeddings",
                success=overall_valid,
                message=f"Embedding validation {'passed' if overall_valid else 'failed'} with {overall_percentage:.1f}% coverage"
            )
        except Exception as e:
            self.logger.error(f"Failed to validate embeddings: {str(e)}")
            print(f"✗ Error validating embeddings: {str(e)}")
            return OperationStatus(
                operation="validate-embeddings",
                success=False,
                message=f"Failed to validate embeddings: {str(e)}"
            )


class ListIndicesCommand(BaseCommand):
    """Command to list indices."""
    
    def execute(self) -> OperationStatus:
        """Execute index listing."""
        try:
            statuses = self.index_operations.list_indices()
            cluster_health = self.index_operations.get_cluster_health()
            self.output.print_index_list(statuses, cluster_health)
            
            return OperationStatus(
                operation="list-indices",
                success=True,
                message="Successfully listed all indices"
            )
        except Exception as e:
            self.logger.error(f"Failed to list indices: {str(e)}")
            print(f"✗ Error listing indices: {str(e)}")
            return OperationStatus(
                operation="list-indices",
                success=False,
                message=f"Failed to list indices: {str(e)}"
            )


class DeleteTestIndicesCommand(BaseCommand):
    """Command to delete test indices."""
    
    def execute(self) -> OperationStatus:
        """Execute test index deletion."""
        try:
            results = self.index_operations.delete_indices([IndexName.TEST_PROPERTIES])
            self.output.print_deletion_results(results)
            
            all_successful = all(r.success for r in results)
            
            return OperationStatus(
                operation="delete-test-indices",
                success=all_successful,
                message="All test indices deleted successfully" if all_successful else "Some indices failed to delete"
            )
        except Exception as e:
            self.logger.error(f"Failed to delete test indices: {str(e)}")
            print(f"✗ Error deleting test indices: {str(e)}")
            return OperationStatus(
                operation="delete-test-indices",
                success=False,
                message=f"Failed to delete test indices: {str(e)}"
            )


class DemoCommand(BaseCommand):
    """Command to run demo queries."""
    
    def __init__(self, config: AppConfig, args: CLIArguments):
        """Initialize demo command."""
        super().__init__(config, args)
        self.demo_runner = DemoRunner(self.es_client.client)
    
    def execute(self) -> OperationStatus:
        """Execute demo query."""
        try:
            if self.args.list:
                demos = self.demo_runner.get_demo_list()
                self.output.print_demo_list(demos)
                return OperationStatus(
                    operation="demo-list",
                    success=True,
                    message="Listed all demo queries"
                )
            
            if not self.args.demo_number:
                print("Please specify a demo number (1-11) or use --list to see available demos")
                print("Example: python -m real_estate_search.management demo 1")
                return OperationStatus(
                    operation="demo",
                    success=False,
                    message="No demo number specified"
                )
            
            # Print header and special description FIRST
            print(f"\nRunning Demo {self.args.demo_number}: {self.demo_runner.demo_registry[self.args.demo_number].name}")
            print("=" * 60)
            
            # Get and print special description if available
            special_descriptions = self.demo_runner.get_demo_descriptions()
            special_desc = special_descriptions.get(self.args.demo_number)
            if special_desc:
                print(special_desc)
                print("=" * 60)
            
            # Now run the demo (which will print its own output)
            query_func = self.demo_runner._get_demo_function(self.args.demo_number)
            
            try:
                # Execute the demo with the actual Elasticsearch client
                full_result = query_func(self.es_client.client)
                
                # Handle demos that return a list of results (demo 12 and 27)
                if self.args.demo_number in [12, 27]:
                    # These demos handle their own display internally
                    # Just check if we got results
                    if full_result:
                        return OperationStatus(
                            operation="demo",
                            success=True,
                            message=f"Demo {self.args.demo_number} executed successfully"
                        )
                    else:
                        return OperationStatus(
                            operation="demo",
                            success=False,
                            message=f"Demo {self.args.demo_number} returned no results"
                        )
                else:
                    # All other demo results inherit from BaseQueryResult and have display method
                    if full_result:
                        print(full_result.display(verbose=self.args.verbose))
                
                    return OperationStatus(
                        operation="demo",
                        success=True,
                        message=f"Demo {self.args.demo_number} executed successfully"
                    )
            except Exception as e:
                print(f"✗ Error executing demo: {str(e)}")
                return OperationStatus(
                    operation="demo",
                    success=False,
                    message=f"Demo {self.args.demo_number} failed: {str(e)}"
                )
            
        except Exception as e:
            self.logger.error(f"Failed to execute demo: {str(e)}")
            print(f"✗ Error executing demo: {str(e)}")
            return OperationStatus(
                operation="demo",
                success=False,
                message=f"Failed to execute demo: {str(e)}"
            )


class EnrichWikipediaCommand(BaseCommand):
    """
    Command to enrich Wikipedia articles with full HTML content.
    
    This command uses the WikipediaIndexer to:
    1. Query Elasticsearch for Wikipedia documents needing enrichment
    2. Load full HTML content from disk
    3. Process documents through the wikipedia_ingest_pipeline
    4. Bulk update documents with processed content
    
    The pipeline strips HTML, trims text, and sets metadata fields.
    """
    
    def __init__(self, config: AppConfig, args: CLIArguments):
        """Initialize the command."""
        super().__init__(config, args)
        
        self.enrichment_config = WikipediaEnrichmentConfig(
            batch_size=args.batch_size or 50,
            max_documents=args.max_documents,
            dry_run=args.dry_run,
            data_dir=config.data.wikipedia_pages_dir,
            pipeline_name="wikipedia_ingest_pipeline",
            index_name="wikipedia"
        )
        
        # Create the indexer
        self.indexer = WikipediaIndexer(self.raw_es_client, self.enrichment_config)
        self.result = WikipediaEnrichmentResult()
    
    def _verify_pipeline(self) -> bool:
        """Verify that the ingest pipeline exists."""
        if not self.indexer.verify_pipeline_exists():
            self.output.warning("Wikipedia ingest pipeline not found")
            
            # Try to create it from the definition file
            pipeline_path = Path(__file__).parent.parent / "elasticsearch" / "pipelines" / "wikipedia_ingest.json"
            if pipeline_path.exists():
                with open(pipeline_path, 'r') as f:
                    pipeline_def = json.load(f)
                
                if self.indexer.create_pipeline(pipeline_def):
                    self.output.success("Created wikipedia_ingest_pipeline")
                    return True
                else:
                    self.output.error("Failed to create pipeline")
                    return False
            else:
                self.output.error(f"Pipeline definition not found: {pipeline_path}")
                return False
        
        self.output.info("Pipeline wikipedia_ingest_pipeline exists")
        return True
    
    def _show_progress(self, message: str):
        """Show progress message if verbose mode is enabled."""
        if self.args.verbose:
            self.output.info(message)
    
    def execute(self) -> OperationStatus:
        """Execute the Wikipedia enrichment command."""
        try:
            self.output.header("Wikipedia Article Enrichment")
            
            # Step 1: Verify pipeline exists
            if not self._verify_pipeline():
                return OperationStatus(
                    operation="enrich-wikipedia",
                    success=False,
                    message="Pipeline verification failed"
                )
            
            # Step 2: Run enrichment using the indexer
            self.output.info("Starting document enrichment...")
            self.output.info(f"Configuration: batch_size={self.enrichment_config.batch_size}, "
                           f"max_documents={self.enrichment_config.max_documents or 'all'}, "
                           f"dry_run={self.enrichment_config.dry_run}")
            
            result = self.indexer.enrich_documents()
            
            # Step 3: Print summary
            self._print_summary(result)
            
            # Determine success
            success = result.documents_failed == 0 and len(result.errors) == 0
            
            return OperationStatus(
                operation="enrich-wikipedia",
                success=success,
                message=f"Enriched {result.documents_enriched} documents",
                details={
                    "total_scanned": result.total_documents_scanned,
                    "needing_enrichment": result.documents_needing_enrichment,
                    "enriched": result.documents_enriched,
                    "failed": result.documents_failed,
                    "files_not_found": len(result.files_not_found),
                    "execution_time_ms": result.execution_time_ms
                }
            )
            
        except Exception as e:
            self.logger.error(f"Enrichment failed: {e}")
            return OperationStatus(
                operation="enrich-wikipedia",
                success=False,
                message=f"Enrichment failed: {str(e)}"
            )
    
    def _print_summary(self, result):
        """Print enrichment summary."""
        self.output.section("Enrichment Summary")
        
        # Basic stats
        stats = [
            ("Total documents scanned", result.total_documents_scanned),
            ("Documents needing enrichment", result.documents_needing_enrichment),
            ("Documents successfully enriched", result.documents_enriched),
            ("Documents failed", result.documents_failed),
            ("Files not found", len(result.files_not_found)),
        ]
        
        for label, value in stats:
            status = "✓" if label.startswith("Documents successfully") else ""
            if label.startswith("Documents failed") and value > 0:
                status = "✗"
            elif label.startswith("Files not found") and value > 0:
                status = "⚠"
            
            self.output.info(f"{label}: {value} {status}")
        
        # Execution time
        if result.execution_time_ms:
            self.output.info(f"Execution time: {result.execution_time_ms:.2f}ms")
        
        # Errors
        if result.errors:
            self.output.warning(f"\nErrors encountered ({len(result.errors)}):")
            for error in result.errors[:5]:  # Show first 5 errors
                self.output.error(f"  - {error}")
            if len(result.errors) > 5:
                self.output.info(f"  ... and {len(result.errors) - 5} more errors")
        
        # Final status
        if result.documents_failed == 0 and not result.errors:
            self.output.success("\n✓ Enrichment completed successfully")
        else:
            self.output.error("\n✗ Enrichment completed with errors")


class HealthCheckCommand(BaseCommand):
    """Command to check Elasticsearch health."""
    
    def execute(self) -> OperationStatus:
        """Execute health check."""
        try:
            factory = ElasticsearchClientFactory(self.config.elasticsearch)
            es_client = factory.create_client()
            
            # Get cluster health
            health = es_client.cluster.health()
            
            print("\n📊 Cluster Health:")
            print(f"  Cluster Name: {health['cluster_name']}")
            print(f"  Status: {health['status']}")
            print(f"  Number of Nodes: {health['number_of_nodes']}")
            print(f"  Active Primary Shards: {health['active_primary_shards']}")
            print(f"  Active Shards: {health['active_shards']}")
            
            # Check if healthy
            if health['status'] in ['green', 'yellow']:
                print("\n✅ Elasticsearch is healthy and accessible")
                return OperationStatus(
                    operation="health-check",
                    success=True,
                    message=f"Elasticsearch cluster '{health['cluster_name']}' is healthy (status: {health['status']})"
                )
            else:
                print(f"\n⚠️ Elasticsearch cluster status is {health['status']}")
                return OperationStatus(
                    operation="health-check",
                    success=False,
                    message=f"Elasticsearch cluster status is {health['status']}"
                )
                
        except Exception as e:
            print(f"\n❌ Failed to connect to Elasticsearch: {str(e)}")
            return OperationStatus(
                operation="health-check",
                success=False,
                message=f"Failed to connect to Elasticsearch: {str(e)}"
            )


class StatsCommand(BaseCommand):
    """Command to show Elasticsearch statistics."""
    
    def execute(self) -> OperationStatus:
        """Execute stats command."""
        try:
            factory = ElasticsearchClientFactory(self.config.elasticsearch)
            es_client = factory.create_client()
            
            # Get cluster health
            health = es_client.cluster.health()
            
            print("\n📊 Cluster Health:")
            print(f"  Cluster Name: {health['cluster_name']}")
            print(f"  Status: {health['status']}")
            print(f"  Number of Nodes: {health['number_of_nodes']}")
            print(f"  Active Primary Shards: {health['active_primary_shards']}")
            
            # Get index stats
            indices = es_client.cat.indices(format='json')
            
            print("\n📈 Index Statistics:")
            print("  " + "━" * 56)
            print(f"  {'Index Name':<30} {'Documents':>10} {'Size':>12}")
            print("  " + "━" * 56)
            
            total_docs = 0
            for index in indices:
                if not index['index'].startswith('.'):  # Skip system indices
                    doc_count = int(index.get('docs.count', 0))
                    total_docs += doc_count
                    size = index.get('store.size', 'N/A')
                    print(f"  {index['index']:<30} {doc_count:>10,} {size:>12}")
            
            print("  " + "━" * 56)
            print(f"  {'TOTAL':<30} {total_docs:>10,}")
            
            # Health status
            print("\n✅ Health Status:")
            if total_docs > 0:
                print("  Database:     HEALTHY")
                print("  Connectivity: OK")
                print(f"  Data Present: YES ({total_docs:,} documents)")
            else:
                print("  Database:     EMPTY")
                print("  Connectivity: OK")
                print("  Data Present: NO")
            
            return OperationStatus(
                operation="stats",
                success=True,
                message=f"Stats retrieved successfully ({total_docs} total documents)",
                details={"total_documents": total_docs}
            )
            
        except Exception as e:
            print(f"\n❌ Failed to get stats: {str(e)}")
            return OperationStatus(
                operation="stats",
                success=False,
                message=f"Failed to get stats: {str(e)}"
            )


class SampleQueryCommand(BaseCommand):
    """Command to run a sample query."""
    
    def execute(self) -> OperationStatus:
        """Execute sample query."""
        try:
            factory = ElasticsearchClientFactory(self.config.elasticsearch)
            es_client = factory.create_client()
            
            print("\n🔍 Running sample query...")
            print("Searching for properties in San Francisco ($500K-$2M)...")
            
            # Build the query
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"address.city": "San Francisco"}}
                        ],
                        "filter": [
                            {"range": {"price": {"gte": 500000, "lte": 2000000}}}
                        ]
                    }
                },
                "size": 3,
                "_source": ["listing_id", "address", "price", "bedrooms", "bathrooms", "square_feet"]
            }
            
            # Execute the query
            response = es_client.search(index="properties", body=query)
            
            total_hits = response['hits']['total']['value']
            
            if total_hits > 0:
                print(f"\nFound {total_hits} properties. Showing first 3:")
                print("-" * 60)
                
                for hit in response['hits']['hits']:
                    source = hit['_source']
                    print(f"Property ID: {source.get('listing_id', 'N/A')}")
                    
                    address = source.get('address', {})
                    print(f"  Address: {address.get('street', 'N/A')}, {address.get('city', 'N/A')}")
                    
                    price = source.get('price', 0)
                    print(f"  Price: ${price:,.0f}")
                    
                    print(f"  Bedrooms: {source.get('bedrooms', 'N/A')} | "
                          f"Bathrooms: {source.get('bathrooms', 'N/A')} | "
                          f"Sq Ft: {source.get('square_feet', 'N/A')}")
                    print()
                
                return OperationStatus(
                    operation="sample-query",
                    success=True,
                    message=f"Sample query completed successfully ({total_hits} results)",
                    details={"total_hits": total_hits}
                )
            else:
                print("\n⚠️ No properties found in the sample query")
                return OperationStatus(
                    operation="sample-query",
                    success=True,
                    message="Sample query completed (no results found)",
                    details={"total_hits": 0}
                )
                
        except Exception as e:
            print(f"\n❌ Failed to run sample query: {str(e)}")
            return OperationStatus(
                operation="sample-query",
                success=False,
                message=f"Failed to run sample query: {str(e)}"
            )