"""
Command classes for CLI operations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional
from elasticsearch import Elasticsearch

from ..config import AppConfig
from ..infrastructure.elasticsearch_client import ElasticsearchClientFactory, ElasticsearchClient
from ..indexer.index_manager import ElasticsearchIndexManager
from ..indexer.enums import IndexName
from .models import CLIArguments, OperationStatus
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
            # Create client factory and client
            client_factory = ElasticsearchClientFactory(self.config.elasticsearch)
            raw_client = client_factory.create_client()
            
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
            results = self.index_operations.setup_indices(clear=self.args.clear)
            self.output.print_index_setup_results(results, clear=self.args.clear)
            
            all_successful = all(r.success for r in results if "reset" not in r.message.lower())
            
            return OperationStatus(
                operation="setup-indices",
                success=all_successful,
                message="All indices set up successfully" if all_successful else "Some indices failed to set up"
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
                full_result = query_func(self.es_client.client)
                
                # Print the result display if it has one
                if hasattr(full_result, 'display'):
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