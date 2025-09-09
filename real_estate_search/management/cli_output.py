"""
CLI output formatting module for consistent display.
"""

from typing import List, Optional, Any
from .models import (
    IndexOperationResult,
    ValidationStatus,
    EmbeddingValidationResult,
    ClusterHealthInfo,
    DemoQuery,
    DemoExecutionResult
)


class CLIOutput:
    """Handles formatted output for CLI operations."""
    
    @staticmethod
    def format_bytes(bytes_count: int) -> str:
        """
        Format bytes into human-readable string.
        
        Args:
            bytes_count: Number of bytes
            
        Returns:
            Formatted string
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_count < 1024:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024
        return f"{bytes_count:.1f} TB"
    
    @staticmethod
    def print_index_setup_results(results: List[IndexOperationResult], clear: bool = False):
        """
        Print index setup results.
        
        Args:
            results: List of operation results
            clear: Whether indices were cleared first
        """
        if clear:
            print("\n🗑️  Clearing existing indices for demo reset...")
            clear_results = [r for r in results if "reset" in r.message.lower()]
            for result in clear_results:
                status = "✓" if result.success else "✗"
                print(f"   {status} {result.index_name}")
            print("")
        
        print("\nIndex Setup Results:")
        print("=" * 50)
        
        setup_results = [r for r in results if "reset" not in r.message.lower()]
        all_successful = all(r.success for r in setup_results)
        
        for result in setup_results:
            status = "✓ SUCCESS" if result.success else "✗ FAILED"
            print(f"{result.index_name:30} {status}")
            if result.error:
                print(f"  Error: {result.error}")
        
        print("=" * 50)
        
        if all_successful:
            print("✓ All indices set up successfully!")
        else:
            print("✗ Some indices failed to set up")
    
    @staticmethod
    def print_validation_results(all_valid: bool, statuses: List[ValidationStatus]):
        """
        Print index validation results.
        
        Args:
            all_valid: Whether all validations passed
            statuses: List of validation statuses
        """
        print("\nIndex Validation Results:")
        print("=" * 70)
        print(f"{'Index Name':20} {'Exists':8} {'Health':8} {'Docs':8} {'Mappings':10}")
        print("=" * 70)
        
        for status in statuses:
            exists_str = "✓" if status.exists else "✗"
            health_str = status.health if status.exists else "N/A"
            docs_str = str(status.docs_count) if status.exists else "N/A"
            mappings_str = "✓" if status.mapping_valid else "✗"
            
            print(f"{status.index_name:20} {exists_str:8} {health_str:8} {docs_str:8} {mappings_str:10}")
            
            if status.error_message:
                print(f"  Error: {status.error_message}")
        
        print("=" * 70)
        
        if all_valid:
            print("✓ All indices are valid!")
        else:
            print("✗ Some indices have validation issues")
    
    @staticmethod
    def print_embedding_validation_results(
        overall_valid: bool, 
        results: List[EmbeddingValidationResult], 
        overall_percentage: float
    ):
        """
        Print embedding validation results.
        
        Args:
            overall_valid: Whether validation passed
            results: List of embedding validation results
            overall_percentage: Overall percentage of docs with embeddings
        """
        print("\nVector Embedding Validation Results:")
        print("=" * 80)
        print(f"{'Entity Type':15} {'Total Docs':12} {'With Embeddings':15} {'Percentage':12} {'Dimension':10} {'Model':15}")
        print("-" * 80)
        
        total_docs = 0
        total_with_embeddings = 0
        
        for result in results:
            dimension_str = str(result.embedding_dimension) if result.embedding_dimension else "N/A"
            model_str = result.embedding_model if result.embedding_model else "N/A"
            
            print(f"{result.entity_type:15} {result.total_docs:12,} {result.docs_with_embeddings:15,} "
                  f"{result.percentage:10.1f}% {dimension_str:10} {model_str:15}")
            
            total_docs += result.total_docs
            total_with_embeddings += result.docs_with_embeddings
        
        print("-" * 80)
        print(f"{'TOTAL':15} {total_docs:12,} {total_with_embeddings:15,} {overall_percentage:10.1f}%")
        print("=" * 80)
        
        if overall_valid and overall_percentage >= 95:
            print("✓ Vector embedding validation PASSED - All entity types have sufficient embeddings")
        elif overall_percentage >= 80:
            print("⚠ Vector embedding validation PARTIAL - Some entities have low embedding coverage")
        else:
            print("✗ Vector embedding validation FAILED - Insufficient embedding coverage")
        
        print("\nRecommendations:")
        if overall_percentage < 95:
            print("- Run the data pipeline with embedding generation enabled")
            print("- Check embedding provider configuration (API keys, etc.)")
            print("- Verify embedding generation didn't fail during pipeline execution")
        else:
            print("- Embedding coverage is excellent - ready for semantic search")
    
    @staticmethod
    def print_index_list(statuses: List[ValidationStatus], cluster_health: ClusterHealthInfo):
        """
        Print detailed index listing.
        
        Args:
            statuses: List of validation statuses
            cluster_health: Cluster health information
        """
        print("\nElasticsearch Index Status:")
        print("=" * 80)
        
        for status in statuses:
            print(f"\nIndex: {status.index_name}")
            print(f"  Exists: {'✓ Yes' if status.exists else '✗ No'}")
            
            if status.exists:
                print(f"  Health: {status.health}")
                print(f"  Documents: {status.docs_count:,}")
                print(f"  Store Size: {CLIOutput.format_bytes(status.store_size_bytes)}")
                print(f"  Mappings Valid: {'✓ Yes' if status.mapping_valid else '✗ No'}")
            elif status.error_message:
                print(f"  Error: {status.error_message}")
        
        print("=" * 80)
        
        print(f"\nCluster Status: {cluster_health.status}")
        print(f"Number of Nodes: {cluster_health.number_of_nodes}")
        print(f"Active Primary Shards: {cluster_health.active_primary_shards}")
        print(f"Active Shards: {cluster_health.active_shards}")
        if cluster_health.unassigned_shards:
            print(f"Unassigned Shards: {cluster_health.unassigned_shards}")
    
    @staticmethod
    def print_demo_list(demos: List[DemoQuery]):
        """
        Print list of available demo queries.
        
        Args:
            demos: List of demo queries
        """
        print("\nAvailable Demo Queries:")
        print("=" * 70)
        
        for demo in demos:
            print(f"  {demo.number}. {demo.name}")
            print(f"     {demo.description}")
            print()
        
        print("=" * 70)
        print("\nUsage: python -m real_estate_search.management demo <number>")
        print("Example: python -m real_estate_search.management demo 1")
        print("\nAdd --verbose flag to see the actual Elasticsearch query DSL")
    
    @staticmethod
    def print_demo_execution(
        demo_result: DemoExecutionResult, 
        special_description: Optional[str] = None,
        verbose: bool = False,
        full_result: Optional[Any] = None
    ):
        """
        Print demo execution results.
        
        Args:
            demo_result: Demo execution result
            special_description: Optional special description
            verbose: Whether to show verbose output
            full_result: Full result object from demo query
        """
        print(f"\nRunning Demo {demo_result.demo_number}: {demo_result.demo_name}")
        print("=" * 60)
        
        if special_description:
            print(special_description)
            print("=" * 60)
        
        if not demo_result.success:
            print(f"✗ Error executing demo: {demo_result.error}")
        else:
            if full_result:
                # All demo results inherit from BaseQueryResult and have display method
                print(full_result.display(verbose=verbose))
            else:
                print(f"✓ Demo executed successfully")
                if demo_result.execution_time_ms:
                    print(f"  Execution time: {demo_result.execution_time_ms}ms")
                if demo_result.total_hits:
                    print(f"  Total hits: {demo_result.total_hits}")
                if demo_result.returned_hits:
                    print(f"  Returned hits: {demo_result.returned_hits}")
                
                if verbose and demo_result.query_dsl:
                    print("\nQuery DSL:")
                    import json
                    print(json.dumps(demo_result.query_dsl, indent=2))
    
    @staticmethod
    def print_deletion_results(results: List[IndexOperationResult]):
        """
        Print index deletion results.
        
        Args:
            results: List of operation results
        """
        print("\nIndex Deletion Results:")
        print("=" * 50)
        
        all_successful = all(r.success for r in results)
        
        for result in results:
            status = "✓ DELETED" if result.success else "✗ FAILED"
            print(f"{result.index_name:30} {status}")
            if result.error:
                print(f"  Error: {result.error}")
        
        print("=" * 50)
        
        if all_successful:
            print("✓ All indices deleted successfully!")
        else:
            print("✗ Some indices failed to delete")
    
    def header(self, text: str):
        """Print a header."""
        print(f"\n{text}")
        print("=" * len(text))
    
    def section(self, text: str):
        """Print a section header."""
        print(f"\n{text}")
        print("-" * len(text))
    
    def info(self, message: str):
        """Print an info message."""
        print(f"ℹ️  {message}")
    
    def success(self, message: str):
        """Print a success message."""
        print(f"✓ {message}")
    
    def warning(self, message: str):
        """Print a warning message."""
        print(f"⚠️  {message}")
    
    def error(self, message: str):
        """Print an error message."""
        print(f"✗ {message}")