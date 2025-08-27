"""
Repository for property data access with constructor injection.
All Elasticsearch operations for properties go through this repository.
"""

from typing import List, Optional, Dict, Any
from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import ApiError
import logging

from real_estate_search.indexer.models import Property, PropertyDocument, IndexStats
from real_estate_search.search.models import SearchRequest, SearchResponse, PropertyHit

logger = logging.getLogger(__name__)


class PropertyRepository:
    """
    Repository for property data in Elasticsearch.
    All dependencies injected through constructor.
    """
    
    def __init__(self, es_client: Elasticsearch, index_name: str):
        """
        Initialize repository with Elasticsearch client and index name.
        
        Args:
            es_client: Configured Elasticsearch client
            index_name: Name of the property index
        """
        self.es_client = es_client
        self.index_name = index_name
        logger.info(f"Property repository initialized for index: {index_name}")
    
    def index_exists(self) -> bool:
        """
        Check if the property index exists.
        
        Returns:
            True if index exists, False otherwise
        """
        try:
            return self.es_client.indices.exists(index=self.index_name)
        except ApiError as e:
            logger.error(f"Error checking index existence: {e}")
            return False
    
    def create_index(self, mappings: Dict[str, Any]) -> bool:
        """
        Create the property index with mappings.
        
        Args:
            mappings: Index mappings and settings
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.es_client.indices.create(
                index=self.index_name,
                body=mappings
            )
            logger.info(f"Created index: {self.index_name}")
            return True
        except ApiError as e:
            logger.error(f"Error creating index: {e}")
            return False
    
    def delete_index(self) -> bool:
        """
        Delete the property index.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.es_client.indices.delete(index=self.index_name)
            logger.info(f"Deleted index: {self.index_name}")
            return True
        except ApiError as e:
            logger.error(f"Error deleting index: {e}")
            return False
    
    def index_property(self, property_doc: Dict[str, Any]) -> bool:
        """
        Index a single property document.
        
        Args:
            property_doc: Property document to index
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.es_client.index(
                index=self.index_name,
                id=property_doc.get('listing_id'),
                body=property_doc
            )
            return result.get('result') in ['created', 'updated']
        except ApiError as e:
            logger.error(f"Error indexing property {property_doc.get('listing_id')}: {e}")
            return False
    
    def bulk_index_properties(self, property_docs: List[Dict[str, Any]]) -> IndexStats:
        """
        Bulk index multiple property documents.
        
        Args:
            property_docs: List of property documents to index
            
        Returns:
            IndexStats with results
        """
        stats = IndexStats(total=len(property_docs))
        
        if not property_docs:
            return stats
        
        # Prepare bulk actions
        actions = []
        for doc in property_docs:
            action = {
                "_index": self.index_name,
                "_id": doc.get("listing_id"),
                "_source": doc
            }
            actions.append(action)
        
        # Execute bulk operation
        try:
            success, failed = helpers.bulk(
                self.es_client,
                actions,
                chunk_size=500,
                raise_on_error=False,
                stats_only=False
            )
            
            stats.success = success
            stats.failed = len(failed) if failed else 0
            
            # Log any failures
            if failed:
                for item in failed[:5]:  # Log first 5 failures
                    logger.error(f"Failed to index: {item}")
                    stats.errors.append(item)
            
            logger.info(f"Bulk indexed {stats.success}/{stats.total} properties")
            
        except Exception as e:
            logger.error(f"Bulk indexing error: {e}")
            stats.failed = stats.total
            stats.errors.append({"error": str(e)})
        
        return stats
    
    def get_property_by_id(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a property by its listing ID.
        
        Args:
            listing_id: Property listing ID
            
        Returns:
            Property document or None if not found
        """
        try:
            result = self.es_client.get(
                index=self.index_name,
                id=listing_id
            )
            return result.get('_source')
        except ApiError as e:
            if e.status_code != 404:
                logger.error(f"Error getting property {listing_id}: {e}")
            return None
    
    def update_property(self, listing_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a property document.
        
        Args:
            listing_id: Property listing ID
            updates: Fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.es_client.update(
                index=self.index_name,
                id=listing_id,
                body={"doc": updates}
            )
            return result.get('result') == 'updated'
        except ApiError as e:
            logger.error(f"Error updating property {listing_id}: {e}")
            return False
    
    def delete_property(self, listing_id: str) -> bool:
        """
        Delete a property from the index.
        
        Args:
            listing_id: Property listing ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.es_client.delete(
                index=self.index_name,
                id=listing_id
            )
            return result.get('result') == 'deleted'
        except ApiError as e:
            if e.status_code != 404:
                logger.error(f"Error deleting property {listing_id}: {e}")
            return False
    
    def search(self, query: Dict[str, Any], size: int = 10, from_: int = 0) -> Dict[str, Any]:
        """
        Execute a search query.
        
        Args:
            query: Elasticsearch query
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Raw Elasticsearch response
        """
        try:
            response = self.es_client.search(
                index=self.index_name,
                body=query,
                size=size,
                from_=from_
            )
            return response
        except ApiError as e:
            logger.error(f"Search error: {e}")
            return {
                "hits": {"hits": [], "total": {"value": 0}},
                "took": 0,
                "error": str(e)
            }
    
    def count(self, query: Optional[Dict[str, Any]] = None) -> int:
        """
        Count documents matching a query.
        
        Args:
            query: Optional Elasticsearch query
            
        Returns:
            Document count
        """
        try:
            if query:
                result = self.es_client.count(
                    index=self.index_name,
                    body=query
                )
            else:
                result = self.es_client.count(index=self.index_name)
            
            return result.get('count', 0)
        except ApiError as e:
            logger.error(f"Count error: {e}")
            return 0
    
    def get_aggregations(self, aggs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get aggregations without returning documents.
        
        Args:
            aggs: Aggregation definitions
            
        Returns:
            Aggregation results
        """
        try:
            response = self.es_client.search(
                index=self.index_name,
                body={
                    "size": 0,
                    "aggs": aggs
                }
            )
            return response.get('aggregations', {})
        except ApiError as e:
            logger.error(f"Aggregation error: {e}")
            return {}
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the index.
        
        Returns:
            Index statistics
        """
        try:
            stats = self.es_client.indices.stats(index=self.index_name)
            count = self.es_client.count(index=self.index_name)
            
            return {
                "index_name": self.index_name,
                "document_count": count.get("count", 0),
                "size_in_bytes": stats["indices"][self.index_name]["total"]["store"]["size_in_bytes"],
                "segments": stats["indices"][self.index_name]["total"]["segments"]["count"]
            }
        except ApiError as e:
            logger.error(f"Error getting index stats: {e}")
            return {
                "index_name": self.index_name,
                "error": str(e)
            }
    
    def refresh_index(self) -> bool:
        """
        Refresh the index to make recent changes searchable.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.es_client.indices.refresh(index=self.index_name)
            return True
        except ApiError as e:
            logger.error(f"Error refreshing index: {e}")
            return False