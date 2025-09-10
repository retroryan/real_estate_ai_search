"""
Search executor for rich listing queries.

This module executes Elasticsearch queries and transforms responses into
Pydantic models with proper validation and error handling.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError

from .models import (
    RichListingModel,
    RichListingSearchResult,
    NeighborhoodModel
)
from .query_builder import RichListingQueryBuilder
from real_estate_search.models import PropertyListing, WikipediaArticle


logger = logging.getLogger(__name__)


class RichListingSearchExecutor:
    """
    Executes searches against the property_relationships index.
    
    This class handles query execution, response transformation,
    and error handling for rich listing searches.
    """
    
    def __init__(self, es_client: Elasticsearch):
        """
        Initialize the search executor.
        
        Args:
            es_client: Elasticsearch client instance
        """
        self.es_client = es_client
        self.query_builder = RichListingQueryBuilder()
        self.index_name = "property_relationships"
    
    def execute_listing_query(
        self,
        listing_id: str
    ) -> RichListingSearchResult:
        """
        Execute a query to retrieve a specific listing by ID.
        
        Args:
            listing_id: The listing ID to search for
            
        Returns:
            RichListingSearchResult with the found listing or empty result
        """
        # Build the query
        query_dsl = self.query_builder.build_listing_query(listing_id)
        
        # Execute the search
        return self._execute_search(query_dsl)
    
    def execute_search_query(
        self,
        query_text: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        property_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_bedrooms: Optional[int] = None,
        size: Optional[int] = None
    ) -> RichListingSearchResult:
        """
        Execute a search query with optional filters.
        
        Args:
            query_text: Text to search across property fields
            city: Filter by city
            state: Filter by state
            property_type: Filter by property type
            min_price: Minimum price filter
            max_price: Maximum price filter
            min_bedrooms: Minimum bedrooms filter
            size: Number of results to return
            
        Returns:
            RichListingSearchResult with matching listings
        """
        # Build the query
        query_dsl = self.query_builder.build_search_query(
            query_text=query_text,
            city=city,
            state=state,
            property_type=property_type,
            min_price=min_price,
            max_price=max_price,
            min_bedrooms=min_bedrooms,
            size=size
        )
        
        # Execute the search
        return self._execute_search(query_dsl)
    
    def execute_aggregation_query(
        self,
        aggregation_type: str = "data_sources"
    ) -> RichListingSearchResult:
        """
        Execute an aggregation query to get statistics.
        
        Args:
            aggregation_type: Type of aggregation to perform
            
        Returns:
            RichListingSearchResult with aggregation results
        """
        # Build the query
        query_dsl = self.query_builder.build_aggregation_query(aggregation_type)
        
        # Execute the search
        return self._execute_search(query_dsl, include_documents=False)
    
    def _execute_search(
        self,
        query_dsl: Dict[str, Any],
        include_documents: bool = True
    ) -> RichListingSearchResult:
        """
        Execute an Elasticsearch query and transform the response.
        
        Args:
            query_dsl: The query DSL to execute
            include_documents: Whether to include documents in results
            
        Returns:
            RichListingSearchResult with search results
        """
        start_time = datetime.now()
        
        try:
            # Validate the query
            self.query_builder.validate_query(query_dsl)
            
            # Execute the search
            response = self.es_client.search(
                index=self.index_name,
                body=query_dsl
            )
            
            # Calculate execution time
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Extract results
            total_hits = response['hits']['total']['value']
            hits = response['hits']['hits'] if include_documents else []
            
            # Transform hits to models
            listings = []
            for hit in hits:
                try:
                    listing_model = self._transform_hit_to_model(hit)
                    if listing_model:
                        listings.append(listing_model)
                except Exception as e:
                    logger.error(f"Error transforming hit to model: {e}")
                    continue
            
            # Extract aggregations if present
            aggregations = response.get('aggregations')
            
            return RichListingSearchResult(
                listings=listings,
                total_hits=total_hits,
                returned_hits=len(listings),
                execution_time_ms=execution_time_ms,
                query_dsl=query_dsl,
                aggregations=aggregations
            )
            
        except RequestError as e:
            logger.error(f"Elasticsearch error during search: {e}")
            return self._create_error_result(
                query_dsl=query_dsl,
                error_message=str(e),
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            return self._create_error_result(
                query_dsl=query_dsl,
                error_message=str(e),
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
    
    def _transform_hit_to_model(self, hit: Dict[str, Any]) -> Optional[RichListingModel]:
        """
        Transform an Elasticsearch hit to a RichListingModel.
        
        Args:
            hit: Elasticsearch hit document
            
        Returns:
            RichListingModel or None if transformation fails
        """
        try:
            source = hit['_source']
            
            # Extract property data
            property_data = self._extract_property_data(source)
            property_model = PropertyListing(**property_data)
            
            # Extract neighborhood data if present
            neighborhood_model = None
            if 'neighborhood' in source and source['neighborhood']:
                neighborhood_data = source['neighborhood']
                neighborhood_model = NeighborhoodModel(**neighborhood_data)
            
            # Extract Wikipedia articles if present
            wikipedia_articles = []
            if 'wikipedia_articles' in source and source['wikipedia_articles']:
                for article_data in source['wikipedia_articles']:
                    try:
                        article = WikipediaArticle(**article_data)
                        wikipedia_articles.append(article)
                    except Exception as e:
                        logger.debug(f"Error creating WikipediaArticle: {e}")
                        continue
            
            # Create the rich listing model
            return RichListingModel(
                property_data=property_model,
                neighborhood=neighborhood_model,
                wikipedia_articles=wikipedia_articles,
                source_index=self.index_name
            )
            
        except Exception as e:
            logger.error(f"Error transforming hit to RichListingModel: {e}")
            return None
    
    def _extract_property_data(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract property data from the source document.
        
        The property_relationships index embeds all data, so we need to
        extract just the property-specific fields.
        
        Args:
            source: Source document from Elasticsearch
            
        Returns:
            Dictionary of property data
        """
        # Create a copy to avoid modifying the original
        property_data = dict(source)
        
        # Remove embedded data fields that aren't part of PropertyListing
        fields_to_remove = ['neighborhood', 'wikipedia_articles']
        for field in fields_to_remove:
            property_data.pop(field, None)
        
        # Ensure required fields are present
        if 'listing_id' not in property_data:
            raise ValueError("Missing required field: listing_id")
        
        if 'address' not in property_data:
            # Create a minimal address if missing
            property_data['address'] = {
                'street': '',
                'city': '',
                'state': '',
                'zip_code': ''
            }
        
        if 'property_type' not in property_data:
            property_data['property_type'] = 'other'
        
        if 'price' not in property_data:
            property_data['price'] = 0
        
        return property_data
    
    def _create_error_result(
        self,
        query_dsl: Dict[str, Any],
        error_message: str,
        execution_time_ms: int
    ) -> RichListingSearchResult:
        """
        Create an error result when search fails.
        
        Args:
            query_dsl: The query that was attempted
            error_message: Error message to include
            execution_time_ms: Execution time before error
            
        Returns:
            RichListingSearchResult with error information
        """
        return RichListingSearchResult(
            listings=[],
            total_hits=0,
            returned_hits=0,
            execution_time_ms=execution_time_ms,
            query_dsl=query_dsl,
            aggregations={"error": error_message}
        )