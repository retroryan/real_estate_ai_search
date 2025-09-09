"""
Query construction module for Wikipedia search.

This module provides pure query building functions that create Elasticsearch
query DSL structures without any side effects or dependencies on Elasticsearch client.
"""

from typing import List, Dict, Any
from .models import SearchQuery, HighlightConfig


class WikipediaQueryBuilder:
    """Builder for Wikipedia search queries."""
    
    def __init__(self):
        """Initialize the query builder."""
        self.default_fields = ["full_content", "title^2", "short_summary", "long_summary"]
        self.source_fields = [
            "page_id", "title", "city", "state", 
            "categories", "content", "content_length", 
            "short_summary", "url"
        ]
    
    def create_highlight_config(self) -> Dict[str, Any]:
        """Create default highlight configuration.
        
        Returns:
            Dictionary with Elasticsearch highlight configuration
        """
        config = HighlightConfig()
        return {
            "fields": {
                "full_content": {
                    "fragment_size": config.fragment_size,
                    "number_of_fragments": config.number_of_fragments,
                    "pre_tags": config.pre_tags,
                    "post_tags": config.post_tags
                }
            },
            "require_field_match": config.require_field_match
        }
    
    def build_multi_match_query(
        self,
        query_text: str,
        fields: List[str] = None,
        operator: str = "or"
    ) -> Dict[str, Any]:
        """Build a multi-match query.
        
        Args:
            query_text: Text to search for
            fields: Fields to search in (uses defaults if None)
            operator: Boolean operator (or/and)
            
        Returns:
            Elasticsearch multi-match query DSL
        """
        return {
            "multi_match": {
                "query": query_text,
                "fields": fields or self.default_fields,
                "operator": operator
            }
        }
    
    def build_boolean_query(
        self,
        should_clauses: List[Dict[str, Any]],
        must_clauses: List[Dict[str, Any]] = None,
        minimum_should_match: int = 1
    ) -> Dict[str, Any]:
        """Build a boolean query with multiple clauses.
        
        Args:
            should_clauses: List of should (OR) clauses
            must_clauses: List of must (AND) clauses
            minimum_should_match: Minimum number of should clauses that must match
            
        Returns:
            Elasticsearch boolean query DSL
        """
        query = {
            "bool": {
                "should": should_clauses,
                "minimum_should_match": minimum_should_match
            }
        }
        
        if must_clauses:
            query["bool"]["must"] = must_clauses
            
        return query
    
    def build_match_query(self, field: str, value: str) -> Dict[str, Any]:
        """Build a simple match query.
        
        Args:
            field: Field to search in
            value: Value to search for
            
        Returns:
            Elasticsearch match query DSL
        """
        return {"match": {field: value}}
    
    def get_historical_events_query(self) -> SearchQuery:
        """Get query for historical events search.
        
        Returns:
            SearchQuery for finding articles about 1906 San Francisco earthquake
        """
        return SearchQuery(
            title="🌉 Historical Events Search",
            description="Finding articles about the 1906 San Francisco earthquake and its impact",
            query=self.build_multi_match_query(
                query_text="1906 earthquake fire San Francisco reconstruction Golden Gate",
                operator="or"
            )
        )
    
    def get_architecture_query(self) -> SearchQuery:
        """Get query for architecture and landmarks.
        
        Returns:
            SearchQuery for Victorian architecture and historical buildings
        """
        return SearchQuery(
            title="🏛️ Architecture and Landmarks",
            description="Searching for Victorian architecture and historical buildings",
            query=self.build_multi_match_query(
                query_text="Victorian architecture Golden Gate Bridge Coit Tower Painted Ladies",
                operator="or"
            )
        )
    
    def get_transportation_query(self) -> SearchQuery:
        """Get query for transportation infrastructure.
        
        Returns:
            SearchQuery for cable cars, BART, and public transit
        """
        should_clauses = [
            self.build_match_query("full_content", "cable car"),
            self.build_match_query("full_content", "BART"),
            self.build_match_query("full_content", "public transportation"),
            self.build_match_query("title", "transportation")
        ]
        
        return SearchQuery(
            title="🚋 Transportation Infrastructure",
            description="Finding content about cable cars, BART, and public transit systems",
            query=self.build_boolean_query(should_clauses=should_clauses)
        )
    
    def get_parks_query(self) -> SearchQuery:
        """Get query for parks and recreation.
        
        Returns:
            SearchQuery for national parks and recreation areas
        """
        should_clauses = [
            self.build_match_query("full_content", "Golden Gate Park"),
            self.build_match_query("full_content", "Presidio"),
            self.build_match_query("full_content", "Yosemite"),
            self.build_match_query("full_content", "Muir Woods"),
            self.build_match_query("title", "park")
        ]
        
        return SearchQuery(
            title="🏞️ Parks and Recreation",
            description="Searching for national parks, recreation areas, and natural landmarks",
            query=self.build_boolean_query(should_clauses=should_clauses)
        )
    
    def get_cultural_heritage_query(self) -> SearchQuery:
        """Get query for cultural heritage.
        
        Returns:
            SearchQuery for museums, theaters, and cultural institutions
        """
        return SearchQuery(
            title="🎭 Cultural Heritage",
            description="Finding articles about museums, theaters, and cultural institutions",
            query={
                "multi_match": {
                    "query": "museum theater cultural arts gallery exhibition",
                    "fields": self.default_fields,
                    "type": "most_fields"
                }
            }
        )
    
    def get_demo_queries(self) -> List[SearchQuery]:
        """Get all demonstration queries.
        
        Returns:
            List of SearchQuery objects for demo
        """
        return [
            self.get_historical_events_query(),
            self.get_architecture_query(),
            self.get_transportation_query(),
            self.get_parks_query(),
            self.get_cultural_heritage_query()
        ]
    
    def build_complete_search_request(
        self,
        query: SearchQuery,
        include_highlights: bool = True
    ) -> Dict[str, Any]:
        """Build complete Elasticsearch search request.
        
        Args:
            query: SearchQuery object with query configuration
            include_highlights: Whether to include highlighting
            
        Returns:
            Complete Elasticsearch search request body
        """
        request = {
            "query": query.query,
            "size": query.size,
            "_source": self.source_fields
        }
        
        if include_highlights:
            request["highlight"] = self.create_highlight_config()
            
        return request