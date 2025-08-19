"""
Property indexer for Elasticsearch.
Handles index creation, document indexing, and updates with proper error handling.
"""

import hashlib
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Generator, Tuple
import structlog
from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import (
    ApiError as ElasticsearchException,
    ConnectionError as ESConnectionError,
    RequestError,
    NotFoundError
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from .models import Property, PropertyDocument, IndexStats
from .mappings import PROPERTY_MAPPINGS
from .enums import IndexName, FieldName, ErrorCode
from .exceptions import (
    PropertyIndexerError,
    IndexCreationError,
    BulkIndexingError,
    ConnectionError
)
from ..config.settings import Settings


logger = structlog.get_logger(__name__)


class PropertyIndexer:
    """
    Manages property indexing operations with Elasticsearch.
    
    This class handles:
    - Index lifecycle management (create, delete, reindex)
    - Document indexing with validation
    - Bulk operations with error handling
    - Zero-downtime index updates using aliases
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the property indexer.
        
        Args:
            settings: Configuration settings. If None, loads from environment.
        """
        self.settings = settings or Settings.load()
        self.es_settings = self.settings.elasticsearch
        self.index_settings = self.settings.index
        self.indexing_settings = self.settings.indexing
        
        self.index_name = self.index_settings.name
        self.index_alias = self.index_settings.alias
        
        self._es_client: Optional[Elasticsearch] = None
        self.logger = logger.bind(component="PropertyIndexer")
    
    @property
    def es(self) -> Elasticsearch:
        """
        Get or create Elasticsearch client with lazy initialization.
        
        Returns:
            Elasticsearch client instance.
            
        Raises:
            ConnectionError: If unable to connect to Elasticsearch.
        """
        if self._es_client is None:
            self._es_client = self._create_client()
        return self._es_client
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(ESConnectionError)
    )
    def _create_client(self) -> Elasticsearch:
        """
        Create Elasticsearch client with retry logic.
        
        Returns:
            Configured Elasticsearch client.
            
        Raises:
            ConnectionError: If unable to establish connection.
        """
        try:
            # Build connection parameters
            es_params = {
                "hosts": [self.es_settings.url],
                "request_timeout": self.es_settings.timeout,
                "retry_on_timeout": self.es_settings.retry_on_timeout,
                "max_retries": self.es_settings.max_retries
            }
            
            # Add authentication if configured
            if self.es_settings.has_auth:
                es_params["basic_auth"] = (
                    self.es_settings.username,
                    self.es_settings.password
                )
                self.logger.info("Using authenticated connection", username=self.es_settings.username)
            
            # Add SSL verification settings
            if self.es_settings.scheme == "https":
                es_params["verify_certs"] = self.es_settings.verify_certs
                if self.es_settings.ca_certs:
                    es_params["ca_certs"] = self.es_settings.ca_certs
            
            client = Elasticsearch(**es_params)
            
            # Test connection
            if not client.ping():
                raise ConnectionError(
                    f"Cannot connect to Elasticsearch at {self.es_settings.url}",
                    error_code=ErrorCode.CONNECTION_ERROR
                )
            
            self.logger.info("Connected to Elasticsearch", url=self.es_settings.url)
            return client
            
        except Exception as e:
            self.logger.error("Failed to connect to Elasticsearch", error=str(e))
            raise ConnectionError(
                f"Failed to connect to Elasticsearch: {e}",
                error_code=ErrorCode.CONNECTION_ERROR
            )
    
    def create_index(self, force: bool = False) -> bool:
        """
        Create a new index with versioning and alias management.
        
        Args:
            force: If True, creates new index even if alias exists.
            
        Returns:
            True if index was created, False if already exists.
            
        Raises:
            IndexCreationError: If index creation fails.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        versioned_index = f"{self.index_name}_{timestamp}"
        
        try:
            # Check if alias exists
            if self.es.indices.exists_alias(name=self.index_alias) and not force:
                self.logger.info("Index alias already exists", alias=self.index_alias)
                return False
            
            # Create new index with mappings
            self.es.indices.create(
                index=versioned_index,
                body=PROPERTY_MAPPINGS,
                ignore=400  # Ignore if already exists
            )
            self.logger.info("Created index", index=versioned_index)
            
            # Update alias atomically
            self._update_alias(versioned_index)
            
            return True
            
        except RequestError as e:
            self.logger.error("Invalid index configuration", error=str(e))
            raise IndexCreationError(
                f"Invalid index configuration: {e}",
                error_code=ErrorCode.CONFIGURATION_ERROR
            )
        except Exception as e:
            self.logger.error("Failed to create index", error=str(e))
            raise IndexCreationError(
                f"Failed to create index: {e}",
                error_code=ErrorCode.INDEX_NOT_FOUND
            )
    
    def _update_alias(self, new_index: str) -> None:
        """
        Update index alias atomically for zero-downtime updates.
        
        Args:
            new_index: Name of the new index to point alias to.
        """
        actions = []
        
        # Remove alias from old indices
        if self.es.indices.exists_alias(name=self.index_alias):
            old_indices = list(self.es.indices.get_alias(name=self.index_alias).keys())
            for old_index in old_indices:
                actions.append({
                    "remove": {
                        "index": old_index,
                        "alias": self.index_alias
                    }
                })
                self.logger.info("Removing alias from old index", index=old_index)
        
        # Add alias to new index
        actions.append({
            "add": {
                "index": new_index,
                "alias": self.index_alias
            }
        })
        
        if actions:
            self.es.indices.update_aliases(body={"actions": actions})
            self.logger.info("Updated alias", alias=self.index_alias, index=new_index)
    
    def index_properties(
        self,
        properties: List[Property],
        validate: bool = True
    ) -> IndexStats:
        """
        Index multiple properties with bulk operations.
        
        Args:
            properties: List of Property models to index.
            validate: Whether to validate properties before indexing.
            
        Returns:
            IndexStats with success/failure counts.
            
        Raises:
            BulkIndexingError: If bulk indexing fails.
        """
        if not properties:
            return IndexStats(total=0)
        
        start_time = time.time()
        stats = IndexStats(total=len(properties))
        
        try:
            # Convert properties to documents
            documents = []
            for prop in properties:
                try:
                    if validate:
                        # Pydantic validation happens automatically
                        doc = PropertyDocument.from_property(prop)
                    else:
                        doc = PropertyDocument.from_property(prop)
                    documents.append(doc)
                except Exception as e:
                    stats.failed += 1
                    stats.errors.append({
                        "listing_id": getattr(prop, 'listing_id', 'unknown'),
                        "error": str(e)
                    })
                    self.logger.warning("Failed to convert property", error=str(e))
            
            if not documents:
                self.logger.warning("No valid documents to index")
                return stats
            
            # Prepare bulk actions
            actions = self._prepare_bulk_actions(documents)
            
            # Execute bulk indexing
            success_count, errors = self._execute_bulk_index(actions)
            
            stats.success = success_count
            stats.failed += len(errors)
            
            for error in errors:
                stats.errors.append(error)
            
            # Refresh index if configured
            if self.indexing_settings.refresh_after_index:
                self.es.indices.refresh(index=self.index_alias)
            
        except Exception as e:
            self.logger.error("Bulk indexing failed", error=str(e))
            raise BulkIndexingError(
                f"Bulk indexing failed: {e}",
                error_code=ErrorCode.BULK_INDEX_ERROR
            )
        
        finally:
            stats.duration_seconds = time.time() - start_time
            self.logger.info(
                "Indexing complete",
                success=stats.success,
                failed=stats.failed,
                total=stats.total,
                duration=stats.duration_seconds
            )
        
        return stats
    
    def _prepare_bulk_actions(
        self,
        documents: List[PropertyDocument]
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Prepare documents for bulk indexing.
        
        Args:
            documents: List of PropertyDocument instances.
            
        Yields:
            Bulk action dictionaries for Elasticsearch.
        """
        for doc in documents:
            doc_id = self._generate_document_id(doc.listing_id, doc.mls_number)
            
            yield {
                "_index": self.index_alias,
                "_id": doc_id,
                "_source": doc.model_dump(exclude_none=True)
            }
    
    def _execute_bulk_index(
        self,
        actions: Generator[Dict[str, Any], None, None]
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Execute bulk indexing with parallel processing.
        
        Args:
            actions: Generator of bulk actions.
            
        Returns:
            Tuple of (success_count, list of errors).
        """
        success_count = 0
        errors = []
        
        for success, info in helpers.parallel_bulk(
            self.es,
            actions,
            chunk_size=self.indexing_settings.batch_size,
            thread_count=self.indexing_settings.parallel_threads,
            raise_on_error=False
        ):
            if success:
                success_count += 1
            else:
                errors.append(info)
                self.logger.warning("Failed to index document", info=info)
            
            # Log progress
            if (success_count + len(errors)) % 100 == 0:
                self.logger.info(
                    "Indexing progress",
                    success=success_count,
                    failed=len(errors)
                )
        
        return success_count, errors
    
    def _generate_document_id(self, listing_id: str, mls_number: Optional[str]) -> str:
        """
        Generate a deterministic document ID.
        
        Args:
            listing_id: Property listing ID.
            mls_number: MLS number if available.
            
        Returns:
            Hexadecimal document ID.
        """
        id_string = f"{listing_id}_{mls_number or ''}"
        return hashlib.md5(id_string.encode()).hexdigest()
    
    def update_property(
        self,
        listing_id: str,
        updates: Dict[str, Any],
        mls_number: Optional[str] = None
    ) -> bool:
        """
        Update a single property document.
        
        Args:
            listing_id: Property listing ID.
            updates: Dictionary of fields to update.
            mls_number: MLS number for ID generation.
            
        Returns:
            True if update succeeded, False otherwise.
        """
        doc_id = self._generate_document_id(listing_id, mls_number)
        
        try:
            self.es.update(
                index=self.index_alias,
                id=doc_id,
                body={"doc": updates}
            )
            self.logger.info("Updated property", listing_id=listing_id)
            return True
            
        except NotFoundError:
            self.logger.warning("Property not found for update", listing_id=listing_id)
            return False
        except Exception as e:
            self.logger.error("Failed to update property", listing_id=listing_id, error=str(e))
            return False
    
    def delete_property(
        self,
        listing_id: str,
        mls_number: Optional[str] = None
    ) -> bool:
        """
        Delete a property document from the index.
        
        Args:
            listing_id: Property listing ID.
            mls_number: MLS number for ID generation.
            
        Returns:
            True if deletion succeeded, False otherwise.
        """
        doc_id = self._generate_document_id(listing_id, mls_number)
        
        try:
            self.es.delete(index=self.index_alias, id=doc_id)
            self.logger.info("Deleted property", listing_id=listing_id)
            return True
            
        except NotFoundError:
            self.logger.warning("Property not found for deletion", listing_id=listing_id)
            return False
        except Exception as e:
            self.logger.error("Failed to delete property", listing_id=listing_id, error=str(e))
            return False
    
    def close(self) -> None:
        """Close the Elasticsearch connection."""
        if self._es_client:
            self._es_client.close()
            self._es_client = None
            self.logger.info("Closed Elasticsearch connection")