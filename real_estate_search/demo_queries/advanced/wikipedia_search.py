"""
Wikipedia article search with geographic filtering.

This module provides specialized search capabilities for Wikipedia
articles with location-based filtering, topic filtering, and
neighborhood association searches.
"""

from typing import Dict, Any, List, Optional
import logging

from .models import WikipediaSearchRequest, LocationFilter

logger = logging.getLogger(__name__)


class WikipediaSearchBuilder:
    """Builds Wikipedia-specific search queries with filtering."""
    
    def build_location_search(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        topics: Optional[List[str]] = None,
        size: int = 10
    ) -> WikipediaSearchRequest:
        """
        Build a Wikipedia search with location and topic filtering.
        
        Args:
            city: Filter by city
            state: Filter by state
            topics: Filter by topics/categories
            size: Number of results
            
        Returns:
            WikipediaSearchRequest with location and topic filters
        """
        must_clauses = []
        
        # Add topic search if provided
        if topics:
            must_clauses.append({
                "multi_match": {
                    "query": " ".join(topics),
                    "fields": [
                        "title^2",
                        "summary^1.5",
                        "categories",
                        "content"
                    ],
                    "type": "best_fields"
                }
            })
        
        filter_clauses = []
        
        # Geographic filters
        if city:
            filter_clauses.append({
                "bool": {
                    "should": [
                        {"match": {"city": city}},
                        {"match": {"title": city}}
                    ],
                    "minimum_should_match": 1
                }
            })
        
        if state:
            filter_clauses.append({
                "bool": {
                    "should": [
                        {"match": {"state": state}},
                        {"term": {"state": state.upper()}}
                    ],
                    "minimum_should_match": 1
                }
            })
        
        # Ensure articles have city data
        filter_clauses.append({
            "exists": {"field": "city"}
        })
        
        # Build the complete query
        if filter_clauses:
            query = {
                "query": {
                    "bool": {
                        "must": must_clauses if must_clauses else [{"match_all": {}}],
                        "filter": filter_clauses,
                        "should": [
                            {"range": {"article_quality_score": {"gte": 0.8, "boost": 2.0}}},
                            {"match": {"title": {"query": city or "", "boost": 1.5}}},
                            {"range": {"content_length": {"gte": 5000, "boost": 1.2}}}
                        ]
                    }
                }
            }
        else:
            query = {
                "query": {
                    "bool": {"must": must_clauses} if must_clauses else {"match_all": {}}
                }
            }
        
        source_fields = [
            "page_id", "title", "url", "short_summary", "long_summary", 
            "city", "state", "location", "article_quality_score", "topics", 
            "full_content", "neighborhood_ids", "neighborhood_names", 
            "primary_neighborhood_name", "has_neighborhood_association"
        ]
        
        highlight = {
            "fields": {
                "summary": {"fragment_size": 150},
                "content": {"fragment_size": 200}
            }
        }
        
        sort = [
            "_score",
            {"article_quality_score": {"order": "desc", "missing": "_last"}}
        ]
        
        return WikipediaSearchRequest(
            query=query,
            size=size,
            source_fields=source_fields,
            highlight=highlight,
            sort=sort,
            index="wikipedia"
        )
    
    def build_neighborhood_association_search(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        size: int = 10
    ) -> WikipediaSearchRequest:
        """
        Build a search for articles with neighborhood associations.
        
        Args:
            city: Filter by city
            state: Filter by state
            size: Number of results
            
        Returns:
            WikipediaSearchRequest for neighborhood-associated articles
        """
        filter_clauses = [
            {"term": {"has_neighborhood_association": True}}
        ]
        
        # Special handling for San Francisco
        if city and "San Francisco" in city:
            filter_clauses.append({
                "bool": {
                    "should": [
                        {"match": {"city": city}},
                        {"match_phrase": {"title": "San Francisco"}},
                        {"terms": {"city": [
                            "Mission District", "Pacific Heights",
                            "Sunset District", "Noe Valley", "SOMA"
                        ]}}
                    ],
                    "minimum_should_match": 1
                }
            })
        elif city:
            filter_clauses.append({"match": {"city": city}})
        
        if state:
            filter_clauses.append({"match": {"state": state}})
        
        query = {
            "query": {
                "bool": {
                    "filter": filter_clauses
                }
            },
            "size": size,
            "_source": [
                "page_id", "title", "city", "state", 
                "neighborhood_ids", "neighborhood_names", 
                "primary_neighborhood_name"
            ],
            "sort": [
                {"neighborhood_count": {"order": "desc", "missing": "_last"}},
                "_score"
            ]
        }
        
        return WikipediaSearchRequest(
            query=query,
            size=size,
            source_fields=[
                "page_id", "title", "city", "state",
                "neighborhood_ids", "neighborhood_names",
                "primary_neighborhood_name"
            ],
            sort=[
                {"neighborhood_count": {"order": "desc", "missing": "_last"}},
                "_score"
            ],
            index="wikipedia"
        )
    
    def build_specific_neighborhood_search(
        self,
        neighborhood_name: str,
        neighborhood_id: Optional[str] = None,
        size: int = 5
    ) -> WikipediaSearchRequest:
        """
        Build a search for a specific neighborhood.
        
        Args:
            neighborhood_name: Name of the neighborhood
            neighborhood_id: Optional neighborhood ID
            size: Number of results
            
        Returns:
            WikipediaSearchRequest for specific neighborhood
        """
        should_clauses = [
            {"match": {"neighborhood_names": neighborhood_name}},
            {"match_phrase": {"title": neighborhood_name}},
            {"match": {"long_summary": neighborhood_name}}
        ]
        
        if neighborhood_id:
            should_clauses.append({"term": {"neighborhood_ids": neighborhood_id}})
        
        query = {
            "query": {
                "bool": {
                    "should": should_clauses,
                    "minimum_should_match": 1
                }
            },
            "size": size,
            "_source": [
                "page_id", "title", "city", "state",
                "neighborhood_ids", "neighborhood_names", "short_summary"
            ],
            "highlight": {
                "fields": {
                    "title": {},
                    "long_summary": {"fragment_size": 150},
                    "neighborhood_names": {}
                }
            }
        }
        
        return WikipediaSearchRequest(
            query=query,
            size=size,
            source_fields=[
                "page_id", "title", "city", "state",
                "neighborhood_ids", "neighborhood_names", "short_summary"
            ],
            highlight={
                "fields": {
                    "title": {},
                    "long_summary": {"fragment_size": 150},
                    "neighborhood_names": {}
                }
            },
            index="wikipedia"
        )
    
    def extract_summary(self, article: Dict[str, Any]) -> str:
        """
        Extract summary from Wikipedia article.
        
        Args:
            article: Wikipedia article source
            
        Returns:
            Extracted summary text
        """
        # Try multiple fields for summary
        summary = article.get('short_summary', '').strip()
        
        if not summary:
            summary = article.get('long_summary', '').strip()
        
        if not summary and article.get('full_content'):
            content = article['full_content']
            lines = content.split('\n')
            # Find first non-empty line after the title
            for i, line in enumerate(lines):
                if i > 0 and line.strip() and line.strip() != article.get('title', ''):
                    summary = ' '.join(line.split())[:250]
                    break
        
        return summary if summary else 'No summary available'