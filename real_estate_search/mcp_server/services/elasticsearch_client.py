"""Elasticsearch client wrapper with connection pooling and retry logic."""

import time
import logging
from typing import Dict, Any, Optional, List
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from elasticsearch.helpers import bulk
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from ..settings import ElasticsearchConfig
from ..models.search import ErrorResponse


logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """Elasticsearch client with connection pooling and retry logic."""
    
    def __init__(self, config: ElasticsearchConfig):
        """Initialize Elasticsearch client.
        
        Args:
            config: Elasticsearch configuration
        """
        self.config = config
        self._client: Optional[Elasticsearch] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Elasticsearch client with proper configuration."""
        client_kwargs = {
            "hosts": [self.config.url],
            "verify_certs": self.config.verify_certs,
            "request_timeout": self.config.request_timeout,
            "retry_on_timeout": self.config.retry_on_timeout,
            "max_retries": self.config.max_retries,
        }
        
        # Add authentication if provided
        if self.config.cloud_id:
            client_kwargs["cloud_id"] = self.config.cloud_id
            client_kwargs.pop("hosts")
        
        if self.config.api_key:
            client_kwargs["api_key"] = self.config.api_key
        elif self.config.username and self.config.password:
            client_kwargs["basic_auth"] = (self.config.username, self.config.password)
        
        try:
            self._client = Elasticsearch(**client_kwargs)
            logger.info("Elasticsearch client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Elasticsearch client: {e}")
            raise
    
    @property
    def client(self) -> Elasticsearch:
        """Get the Elasticsearch client instance."""
        if self._client is None:
            self._initialize_client()
        return self._client
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            es_exceptions.ConnectionError,
            es_exceptions.ConnectionTimeout,
            es_exceptions.TransportError
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def search(
        self,
        index: str,
        body: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a search query with retry logic.
        
        Args:
            index: Index name
            body: Search query body
            **kwargs: Additional search parameters
            
        Returns:
            Search response
        """
        try:
            response = self.client.search(
                index=index,
                body=body,
                **kwargs
            )
            return response
        except es_exceptions.NotFoundError as e:
            logger.error(f"Index not found: {index}")
            raise
        except es_exceptions.RequestError as e:
            logger.error(f"Invalid search request: {e}")
            raise
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            es_exceptions.ConnectionError,
            es_exceptions.ConnectionTimeout,
            es_exceptions.TransportError
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def multi_search(
        self,
        body: List[Dict[str, Any]],
        index: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute multiple search queries in a single request.
        
        Args:
            body: Multi-search body
            index: Optional index name
            **kwargs: Additional parameters
            
        Returns:
            Multi-search response
        """
        try:
            response = self.client.msearch(
                body=body,
                index=index,
                **kwargs
            )
            return response
        except Exception as e:
            logger.error(f"Multi-search failed: {e}")
            raise
    
    def index_document(
        self,
        index: str,
        document: Dict[str, Any],
        doc_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Index a single document.
        
        Args:
            index: Index name
            document: Document to index
            doc_id: Optional document ID
            **kwargs: Additional parameters
            
        Returns:
            Index response
        """
        try:
            response = self.client.index(
                index=index,
                body=document,
                id=doc_id,
                **kwargs
            )
            return response
        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            raise
    
    def bulk_index(
        self,
        index: str,
        documents: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        """Bulk index documents.
        
        Args:
            index: Index name
            documents: Documents to index
            **kwargs: Additional parameters
            
        Returns:
            Bulk response
        """
        try:
            actions = [
                {
                    "_index": index,
                    "_source": doc,
                    "_id": doc.get("id") or doc.get("listing_id") or doc.get("page_id")
                }
                for doc in documents
            ]
            
            success, failed = bulk(
                self.client,
                actions,
                raise_on_error=False,
                **kwargs
            )
            
            return {
                "success": success,
                "failed": failed,
                "total": len(documents)
            }
        except Exception as e:
            logger.error(f"Bulk indexing failed: {e}")
            raise
    
    def get_document(
        self,
        index: str,
        doc_id: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Get a document by ID.
        
        Args:
            index: Index name
            doc_id: Document ID
            **kwargs: Additional parameters
            
        Returns:
            Document or None if not found
        """
        try:
            response = self.client.get(
                index=index,
                id=doc_id,
                **kwargs
            )
            return response["_source"]
        except es_exceptions.NotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            raise
    
    def delete_document(
        self,
        index: str,
        doc_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Delete a document by ID.
        
        Args:
            index: Index name
            doc_id: Document ID
            **kwargs: Additional parameters
            
        Returns:
            Delete response
        """
        try:
            response = self.client.delete(
                index=index,
                id=doc_id,
                **kwargs
            )
            return response
        except es_exceptions.NotFoundError as e:
            logger.warning(f"Document not found for deletion: {doc_id}")
            raise
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            raise
    
    def count(
        self,
        index: str,
        body: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> int:
        """Count documents matching a query.
        
        Args:
            index: Index name
            body: Optional query body
            **kwargs: Additional parameters
            
        Returns:
            Document count
        """
        try:
            response = self.client.count(
                index=index,
                body=body,
                **kwargs
            )
            return response["count"]
        except Exception as e:
            logger.error(f"Failed to count documents: {e}")
            raise
    
    def ping(self) -> bool:
        """Check if Elasticsearch is reachable.
        
        Returns:
            True if reachable, False otherwise
        """
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Failed to ping Elasticsearch: {e}")
            return False
    
    def get_cluster_health(self) -> Dict[str, Any]:
        """Get cluster health information.
        
        Returns:
            Cluster health response
        """
        try:
            return self.client.cluster.health()
        except Exception as e:
            logger.error(f"Failed to get cluster health: {e}")
            raise
    
    def index_exists(self, index: str) -> bool:
        """Check if an index exists.
        
        Args:
            index: Index name
            
        Returns:
            True if exists, False otherwise
        """
        try:
            return self.client.indices.exists(index=index)
        except Exception as e:
            logger.error(f"Failed to check index existence: {e}")
            return False
    
    def create_index(
        self,
        index: str,
        body: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create an index.
        
        Args:
            index: Index name
            body: Index configuration
            **kwargs: Additional parameters
            
        Returns:
            Create response
        """
        try:
            response = self.client.indices.create(
                index=index,
                body=body,
                **kwargs
            )
            logger.info(f"Created index: {index}")
            return response
        except es_exceptions.RequestError as e:
            if "resource_already_exists_exception" in str(e):
                logger.warning(f"Index already exists: {index}")
            raise
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            raise
    
    def delete_index(self, index: str) -> Dict[str, Any]:
        """Delete an index.
        
        Args:
            index: Index name
            
        Returns:
            Delete response
        """
        try:
            response = self.client.indices.delete(index=index)
            logger.info(f"Deleted index: {index}")
            return response
        except es_exceptions.NotFoundError:
            logger.warning(f"Index not found for deletion: {index}")
            raise
        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            raise
    
    def refresh_index(self, index: str) -> Dict[str, Any]:
        """Refresh an index.
        
        Args:
            index: Index name
            
        Returns:
            Refresh response
        """
        try:
            return self.client.indices.refresh(index=index)
        except Exception as e:
            logger.error(f"Failed to refresh index: {e}")
            raise
    
    def close(self):
        """Close the Elasticsearch client connection."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Elasticsearch client connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()