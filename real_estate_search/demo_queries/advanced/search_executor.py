"""
Elasticsearch execution module for advanced searches.

This module handles the execution of search requests against Elasticsearch
and processes the responses into typed result models.
"""

from typing import Dict, Any, List, Tuple, Optional
from pydantic import BaseModel, Field
from elasticsearch import Elasticsearch
import logging

from ..result_models import (
    PropertySearchResult, WikipediaSearchResult, MixedEntityResult,
    WikipediaArticle
)
from ...models import PropertyListing
from ...models.property import PropertyListing
from ...models.address import Address
from .models import (
    SearchRequest, MultiIndexSearchRequest,
    WikipediaSearchRequest, EntityDiscriminationResult
)

logger = logging.getLogger(__name__)


class SemanticSearchResponse(BaseModel):
    """Response model for semantic search."""
    results: List[PropertyListing]
    reference_property: Optional[PropertyListing] = None
    execution_time_ms: int
    total_hits: int


class MultiEntityResponse(BaseModel):
    """Response model for multi-entity search."""
    property_results: List[PropertyListing]
    wikipedia_results: List[WikipediaArticle]
    neighborhood_results: List[Dict[str, Any]]
    aggregations: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: int
    total_hits: int


class WikipediaResponse(BaseModel):
    """Response model for Wikipedia search."""
    results: List[WikipediaArticle]
    execution_time_ms: int
    total_hits: int


class AdvancedSearchExecutor:
    """Executes advanced search requests against Elasticsearch."""
    
    def __init__(self, es_client: Elasticsearch):
        """
        Initialize the search executor.
        
        Args:
            es_client: Elasticsearch client instance
        """
        self.es_client = es_client
    
    def _discriminate_entity_type(self, hit: Dict[str, Any]) -> EntityDiscriminationResult:
        """
        Determine entity type from search hit.
        
        Args:
            hit: Elasticsearch search hit
            
        Returns:
            EntityDiscriminationResult with entity type information
        """
        index_name = hit.get('_index', '')
        
        if 'properties' in index_name:
            entity_type = 'property'
        elif 'neighborhoods' in index_name:
            entity_type = 'neighborhood'
        elif 'wikipedia' in index_name:
            entity_type = 'wikipedia'
        else:
            entity_type = 'unknown'
            
        return EntityDiscriminationResult(
            entity_type=entity_type,
            index_name=index_name,
            confidence=1.0
        )
    
    def execute_semantic(
        self, 
        request: SearchRequest,
        reference_property: Optional[PropertyListing] = None
    ) -> SemanticSearchResponse:
        """
        Execute a semantic similarity search.
        
        Args:
            request: Search request to execute
            reference_property: Optional reference property for context
            
        Returns:
            SemanticSearchResponse with results
        """
        try:
            response = self.es_client.search(
                index=request.index,
                body=request.query
            )
            
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                # Include similarity score
                source['_similarity_score'] = hit['_score']
                
                results.append(PropertyListing(**source))
            
            return SemanticSearchResponse(
                results=results,
                reference_property=reference_property,
                execution_time_ms=response.get('took', 0),
                total_hits=response['hits']['total']['value']
            )
            
        except Exception as e:
            logger.error(f"Error executing semantic search: {e}")
            return SemanticSearchResponse(
                results=[],
                reference_property=reference_property,
                execution_time_ms=0,
                total_hits=0
            )
    
    def execute_multi_entity(
        self,
        request: MultiIndexSearchRequest
    ) -> MultiEntityResponse:
        """
        Execute a multi-entity cross-index search.
        
        Args:
            request: Multi-index search request to execute
            
        Returns:
            MultiEntityResponse with grouped results
        """
        try:
            response = self.es_client.search(
                index=request.indices,
                body={
                    **request.query,
                    "aggs": request.aggregations or {}
                }
            )
            
            # Process results by entity type
            property_results = []
            wikipedia_results = []
            neighborhood_results = []
            
            for hit in response['hits']['hits']:
                source = hit['_source']
                
                # Discriminate entity type
                discrimination = self._discriminate_entity_type(hit)
                
                # Add metadata
                source['_index'] = hit['_index']
                source['_id'] = hit['_id']
                source['_score'] = hit['_score']
                source['_entity_type'] = discrimination.entity_type
                
                # Add highlights if present
                if 'highlight' in hit:
                    source['_highlights'] = hit['highlight']
                
                # Process by entity type
                if discrimination.entity_type == 'property':
                    property_results.append(PropertyListing(**source))
                elif discrimination.entity_type == 'wikipedia':
                    wikipedia_results.append(WikipediaArticle(
                        page_id=str(source.get('page_id', '')),
                        title=source.get('title', ''),
                        summary=source.get('short_summary', source.get('long_summary', '')),
                        city=source.get('city'),
                        state=source.get('state'),
                        url=source.get('url')
                    ))
                elif discrimination.entity_type == 'neighborhood':
                    neighborhood_results.append(source)
            
            aggregations = response.get('aggregations', {})
            
            return MultiEntityResponse(
                property_results=property_results,
                wikipedia_results=wikipedia_results,
                neighborhood_results=neighborhood_results,
                aggregations=aggregations,
                execution_time_ms=response.get('took', 0),
                total_hits=response['hits']['total']['value']
            )
            
        except Exception as e:
            logger.error(f"Error executing multi-entity search: {e}")
            return MultiEntityResponse(
                property_results=[],
                wikipedia_results=[],
                neighborhood_results=[],
                aggregations={},
                execution_time_ms=0,
                total_hits=0
            )
    
    def execute_wikipedia(
        self,
        request: WikipediaSearchRequest
    ) -> WikipediaResponse:
        """
        Execute a Wikipedia search.
        
        Args:
            request: Wikipedia search request to execute
            
        Returns:
            WikipediaResponse with results
        """
        try:
            body = {
                **request.query,
                "size": request.size,
                "_source": request.source_fields if request.source_fields else True
            }
            
            if request.highlight:
                body["highlight"] = request.highlight
                
            if request.sort:
                body["sort"] = request.sort
            
            response = self.es_client.search(
                index=request.index,
                body=body
            )
            
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                source['_score'] = hit['_score']
                
                # Add highlights if present
                if 'highlight' in hit:
                    source['_highlights'] = hit['highlight']
                
                results.append(WikipediaArticle(
                    page_id=str(source.get('page_id', hit.get('_id', ''))),
                    title=source.get('title', ''),
                    short_summary=source.get('short_summary', ''),
                    long_summary=source.get('long_summary', ''),
                    city=source.get('city'),
                    state=source.get('state'),
                    url=source.get('url'),
                    score=hit.get('_score')
                ))
            
            return WikipediaResponse(
                results=results,
                execution_time_ms=response.get('took', 0),
                total_hits=response['hits']['total']['value']
            )
            
        except Exception as e:
            logger.error(f"Error executing Wikipedia search: {e}")
            return WikipediaResponse(
                results=[],
                execution_time_ms=0,
                total_hits=0
            )
    
    def get_reference_property(self, property_id: str) -> Optional[PropertyListing]:
        """
        Get a reference property by ID.
        
        Args:
            property_id: Property ID to retrieve
            
        Returns:
            PropertyListing if found, None otherwise
        """
        try:
            response = self.es_client.get(
                index="properties",
                id=property_id
            )
            
            source = response.get('_source', {})
            if 'embedding' not in source:
                logger.warning(f"Property {property_id} has no embedding")
                return None
            
            # Set the listing_id to match the document ID
            source['listing_id'] = property_id
            
            return PropertyListing.from_elasticsearch(source)
            
        except Exception as e:
            logger.error(f"Error getting reference property: {e}")
            return None
    
    def get_random_property(self) -> Optional[PropertyListing]:
        """
        Get a random property with embedding.
        
        Returns:
            PropertyListing if found, None otherwise
        """
        try:
            import random
            
            query = {
                "query": {
                    "function_score": {
                        "query": {"match_all": {}},
                        "random_score": {"seed": random.randint(1, 10000)}
                    }
                },
                "size": 1
            }
            
            response = self.es_client.search(
                index="properties",
                body=query
            )
            
            if not response['hits']['hits']:
                return None
            
            hit = response['hits']['hits'][0]
            source = hit['_source']
            property_id = hit['_id']
            
            if 'embedding' not in source:
                logger.warning(f"Random property {property_id} has no embedding")
                return None
            
            # Set the listing_id to match the document ID
            source['listing_id'] = property_id
            
            return PropertyListing.from_elasticsearch(source, score=hit.get('_score'))
            
        except Exception as e:
            logger.error(f"Error getting random property: {e}")
            return None