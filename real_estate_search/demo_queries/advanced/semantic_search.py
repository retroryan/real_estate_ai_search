"""
Semantic similarity search using vector embeddings.

This module provides KNN (k-nearest neighbor) search capabilities
for finding semantically similar properties using dense vector embeddings.
"""

from typing import Dict, Any, Optional, List
import random
import logging

from ...models.property import PropertyListing
from ...models.address import Address
from .models import SearchRequest

logger = logging.getLogger(__name__)


class SemanticSearchBuilder:
    """Builds semantic similarity search queries using vector embeddings."""
    
    def build_similarity_search(
        self, 
        reference_embedding: List[float],
        reference_property_id: str,
        size: int = 10
    ) -> SearchRequest:
        """
        Build a KNN similarity search query.
        
        Args:
            reference_embedding: The embedding vector to find similar ones to
            reference_property_id: ID of the reference property to exclude
            size: Number of similar properties to return
            
        Returns:
            SearchRequest with KNN query
        """
        query = {
            "knn": {
                "field": "embedding",
                "query_vector": reference_embedding,
                "k": size + 1,  # +1 as reference might be included
                "num_candidates": 100  # Number of candidates per shard
            },
            "query": {
                "bool": {
                    "must_not": [
                        {"term": {"_id": reference_property_id}}
                    ]
                }
            },
            "size": size,
            "_source": [
                "listing_id", "property_type", "price", "bedrooms", "bathrooms",
                "square_feet", "address", "description", "features"
            ]
        }
        
        return SearchRequest(
            query=query,
            size=size,
            source_fields=[
                "listing_id", "property_type", "price", "bedrooms", "bathrooms",
                "square_feet", "address", "description", "features"
            ],
            index="properties"
        )
    
    def build_random_property_query(self, seed: Optional[int] = None) -> SearchRequest:
        """
        Build a query to get a random property.
        
        Args:
            seed: Optional random seed for reproducibility
            
        Returns:
            SearchRequest for random property selection
        """
        if seed is None:
            seed = random.randint(1, 10000)
            
        query = {
            "query": {
                "function_score": {
                    "query": {"match_all": {}},
                    "random_score": {"seed": seed}
                }
            },
            "size": 1
        }
        
        return SearchRequest(
            query=query,
            size=1,
            index="properties"
        )
    
    def extract_reference_property(self, es_response: Dict[str, Any]) -> Optional[PropertyListing]:
        """
        Extract reference property from Elasticsearch response.
        
        Args:
            es_response: Elasticsearch get or search response
            
        Returns:
            PropertyListing if found and has embedding, None otherwise
        """
        # Handle both get response and search response
        source = None
        property_id = None
        
        if '_source' in es_response:
            # Direct get response
            source = es_response['_source']
            property_id = es_response.get('_id')
        elif 'hits' in es_response and es_response['hits']['hits']:
            # Search response
            hit = es_response['hits']['hits'][0]
            source = hit.get('_source', {})
            property_id = hit.get('_id')
        
        if not source or not property_id:
            return None
            
        if 'embedding' not in source:
            logger.warning(f"Property {property_id} has no embedding")
            return None
            
        # Set the listing_id to match property_id
        source['listing_id'] = property_id
        
        return PropertyListing.from_elasticsearch(source)