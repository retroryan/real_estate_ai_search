"""
Command classes for CLI operations.
"""

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
from elasticsearch import Elasticsearch, helpers
from tqdm import tqdm

from ..config import AppConfig
from ..infrastructure.elasticsearch_client import ElasticsearchClientFactory, ElasticsearchClient
from ..indexer.index_manager import ElasticsearchIndexManager
from ..indexer.enums import IndexName
from .models import (
    CLIArguments, 
    OperationStatus,
    WikipediaEnrichmentConfig,
    WikipediaEnrichmentResult
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


class WikipediaDocument:
    """Lightweight class for Wikipedia document data."""
    
    def __init__(self, page_id: int, title: str, article_filename: Optional[str] = None, 
                 content_loaded: Optional[bool] = False, full_content: Optional[str] = None):
        self.page_id = page_id
        self.title = title
        self.article_filename = article_filename
        self.content_loaded = content_loaded if content_loaded is not None else False
        self.full_content = full_content
    
    def needs_enrichment(self) -> bool:
        """Check if document needs content enrichment."""
        return self.article_filename is not None and not self.content_loaded


class EnrichWikipediaCommand(BaseCommand):
    """
    Command to enrich Wikipedia articles with full HTML content.
    
    This command:
    1. Queries Elasticsearch for Wikipedia documents needing enrichment
    2. Loads full HTML content from disk
    3. Uses Elasticsearch ingest pipeline to process HTML
    4. Bulk updates documents for efficient indexing
    """
    
    def __init__(self, config: AppConfig, args: CLIArguments):
        """Initialize the command."""
        super().__init__(config, args)
        self.enrichment_config = WikipediaEnrichmentConfig(
            batch_size=args.batch_size or 50,
            max_documents=args.max_documents,
            dry_run=args.dry_run,
            data_dir="../data",
            pipeline_name="wikipedia_ingest_pipeline"
        )
        self.result = WikipediaEnrichmentResult()
    
    def _query_documents(self) -> List[WikipediaDocument]:
        """Query Elasticsearch for documents needing enrichment."""
        self.output.info("Querying Elasticsearch for documents...")
        
        # Build query to find documents with article_filename but not content_loaded
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"exists": {"field": "article_filename"}}
                    ],
                    "must_not": [
                        {"term": {"content_loaded": True}}
                    ]
                }
            },
            "size": self.enrichment_config.max_documents or 10000,
            "_source": ["page_id", "title", "article_filename", "content_loaded", "full_content"]
        }
        
        try:
            response = self.raw_es_client.search(index="wikipedia", body=query)
            hits = response.get("hits", {}).get("hits", [])
            
            documents = []
            for hit in hits:
                doc_data = hit["_source"]
                doc = WikipediaDocument(
                    page_id=doc_data.get("page_id"),
                    title=doc_data.get("title"),
                    article_filename=doc_data.get("article_filename"),
                    content_loaded=doc_data.get("content_loaded", False),
                    full_content=doc_data.get("full_content")
                )
                if doc.needs_enrichment():
                    documents.append(doc)
            
            self.result.total_documents_scanned = len(hits)
            self.result.documents_needing_enrichment = len(documents)
            
            self.output.info(f"Found {len(documents)} documents needing enrichment")
            return documents
            
        except Exception as e:
            error_msg = f"Failed to query documents: {e}"
            self.logger.error(error_msg)
            self.result.errors.append(error_msg)
            return []
    
    def _read_html_file(self, filename: str) -> Optional[str]:
        """Read HTML content from file."""
        # Resolve file path
        if filename.startswith('data/'):
            file_path = Path(filename)
        else:
            file_path = Path(self.enrichment_config.data_dir) / filename
        
        if not file_path.exists():
            self.result.files_not_found += 1
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return content
        except Exception as e:
            error_msg = f"Failed to read {file_path}: {e}"
            self.logger.warning(error_msg)
            self.result.errors.append(error_msg)
            return None
    
    def _prepare_bulk_actions(self, documents: List[WikipediaDocument]) -> List[Dict[str, Any]]:
        """Prepare bulk update actions for Elasticsearch."""
        actions = []
        
        # Show progress bar if verbose
        iterator = tqdm(documents, desc="Reading HTML files", disable=not self.args.verbose)
        
        for doc in iterator:
            if not doc.article_filename:
                continue
            
            # Load HTML content from disk
            html_content = self._read_html_file(doc.article_filename)
            if html_content is None:
                continue
            
            # Get existing document to preserve all fields
            try:
                existing_doc = self.raw_es_client.get(index="wikipedia", id=str(doc.page_id))['_source']
                
                # Add the full HTML content
                existing_doc['full_content'] = html_content
                
                # Prepare bulk action
                action = {
                    "_op_type": "index",
                    "_index": "wikipedia",
                    "_id": str(doc.page_id),
                    "_source": existing_doc
                }
                actions.append(action)
                
            except Exception as e:
                self.logger.warning(f"Could not get document {doc.page_id}: {e}")
                continue
        
        return actions
    
    def _perform_bulk_updates(self, actions: List[Dict[str, Any]]) -> None:
        """
        Perform bulk updates to Elasticsearch using an ingest pipeline.
        
        This method leverages Elasticsearch's ingest pipeline feature for efficient
        document processing. The pipeline ("wikipedia_ingest_pipeline") performs
        transformations on documents BEFORE they are indexed:
        
        1. HTML Processing: Strips HTML tags, extracts text content
        2. Text Analysis: Generates summaries, extracts entities
        3. Field Enrichment: Adds metadata, timestamps, computed fields
        4. Content Validation: Ensures required fields are present
        
        The bulk API with pipeline processing is ideal for:
        - Large-scale document enrichment (100s to 1000s of docs)
        - Consistent document transformations
        - CPU-intensive processing (offloaded to Elasticsearch nodes)
        - Atomic updates (all-or-nothing per document)
        
        Pipeline processing happens on the Elasticsearch cluster, not the client,
        which distributes the computational load across nodes.
        """
        if not actions:
            self.output.info("No documents to update")
            return
        
        if self.enrichment_config.dry_run:
            self.output.warning(f"DRY RUN: Would update {len(actions)} documents")
            self.result.documents_enriched = len(actions)
            return
        
        self.output.info(f"Updating {len(actions)} documents...")
        
        # Process in batches to avoid memory issues and network timeouts
        # Default batch_size is 50-100 documents for optimal throughput
        batch_size = self.enrichment_config.batch_size
        for i in range(0, len(actions), batch_size):
            batch = actions[i:i + batch_size]
            
            try:
                # Use helpers.bulk for efficient bulk indexing with pipeline processing
                # 
                # Key parameters:
                # - pipeline: Name of the ingest pipeline to process documents through
                #             The pipeline runs ON THE SERVER before indexing
                # - stats_only: Return only success/failure counts, not full responses
                #               Reduces network traffic for large batches
                # - raise_on_error: False allows partial success (some docs may fail)
                #
                # The pipeline parameter is the KEY feature here:
                # It tells Elasticsearch to run each document through the pipeline
                # BEFORE indexing, allowing complex transformations at scale
                success, failed = helpers.bulk(
                    self.raw_es_client,
                    batch,
                    pipeline=self.enrichment_config.pipeline_name,  # "wikipedia_ingest_pipeline"
                    stats_only=True,        # Don't return full responses (saves memory)
                    raise_on_error=False    # Continue on partial failures
                )
                
                self.result.documents_enriched += success
                self.result.documents_failed += failed
                
                if failed > 0:
                    # Some documents failed pipeline processing
                    # Common causes: missing fields, pipeline errors, mapping conflicts
                    self.output.warning(f"Failed to update {failed} documents in batch")
                    
            except Exception as e:
                # Catastrophic failure - entire batch failed
                # Usually network issues or pipeline configuration problems
                error_msg = f"Bulk update failed: {e}"
                self.logger.error(error_msg)
                self.result.errors.append(error_msg)
                self.result.documents_failed += len(batch)
    
    def execute(self) -> OperationStatus:
        """Execute the Wikipedia enrichment command."""
        start_time = time.time()
        
        try:
            self.output.header("Wikipedia Article Enrichment")
            
            # Step 1: Query documents needing enrichment
            documents = self._query_documents()
            
            if not documents:
                self.output.success("No documents need enrichment")
                return OperationStatus(
                    operation="enrich-wikipedia",
                    success=True,
                    message="No documents need enrichment"
                )
            
            # Step 2: Prepare bulk update actions
            self.output.info("Preparing bulk update actions...")
            actions = self._prepare_bulk_actions(documents)
            
            # Step 3: Perform bulk updates
            self._perform_bulk_updates(actions)
            
            # Calculate execution time
            self.result.execution_time_ms = (time.time() - start_time) * 1000
            
            # Print summary
            self._print_summary()
            
            # Determine success
            success = self.result.documents_failed == 0 and len(self.result.errors) == 0
            
            return OperationStatus(
                operation="enrich-wikipedia",
                success=success,
                message=f"Enriched {self.result.documents_enriched} documents",
                details={
                    "total_scanned": self.result.total_documents_scanned,
                    "needing_enrichment": self.result.documents_needing_enrichment,
                    "enriched": self.result.documents_enriched,
                    "failed": self.result.documents_failed,
                    "files_not_found": self.result.files_not_found,
                    "execution_time_ms": self.result.execution_time_ms
                }
            )
            
        except Exception as e:
            self.logger.error(f"Enrichment failed: {e}")
            return OperationStatus(
                operation="enrich-wikipedia",
                success=False,
                message=f"Enrichment failed: {str(e)}"
            )
    
    def _print_summary(self):
        """Print enrichment summary."""
        self.output.section("Enrichment Summary")
        
        # Basic stats
        stats = [
            ("Total documents scanned", self.result.total_documents_scanned),
            ("Documents needing enrichment", self.result.documents_needing_enrichment),
            ("Documents successfully enriched", self.result.documents_enriched),
            ("Documents failed", self.result.documents_failed),
            ("Files not found", self.result.files_not_found),
        ]
        
        for label, value in stats:
            status = "✓" if label.startswith("Documents successfully") else ""
            if label.startswith("Documents failed") and value > 0:
                status = "✗"
            elif label.startswith("Files not found") and value > 0:
                status = "⚠"
            
            self.output.info(f"{label}: {value} {status}")
        
        # Execution time
        if self.result.execution_time_ms:
            self.output.info(f"Execution time: {self.result.execution_time_ms:.2f}ms")
        
        # Errors
        if self.result.errors:
            self.output.warning(f"\nErrors encountered ({len(self.result.errors)}):")
            for error in self.result.errors[:5]:  # Show first 5 errors
                self.output.error(f"  - {error}")
            if len(self.result.errors) > 5:
                self.output.info(f"  ... and {len(self.result.errors) - 5} more errors")
        
        # Final status
        if self.result.documents_failed == 0 and not self.result.errors:
            self.output.success("\n✓ Enrichment completed successfully")
        else:
            self.output.error("\n✗ Enrichment completed with errors")