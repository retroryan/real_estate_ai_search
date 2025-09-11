"""
Base search models.

Core models for Elasticsearch search requests and responses.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class SearchHit(BaseModel):
    """Individual search hit from Elasticsearch."""
    index: str = Field(..., alias="_index", description="Index name")
    id: str = Field(..., alias="_id", description="Document ID")
    score: Optional[float] = Field(None, alias="_score", description="Relevance score")
    source: dict = Field(..., alias="_source", description="Document source")
    highlight: Optional[dict[str, List[str]]] = Field(None, description="Highlighted fields")
    sort: Optional[List] = Field(None, description="Sort values")
    
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class SourceFilter(BaseModel):
    """Source filtering configuration for limiting returned fields."""
    includes: Optional[List[str]] = Field(None, description="Fields to include")
    excludes: Optional[List[str]] = Field(None, description="Fields to exclude")
    
    model_config = ConfigDict(extra="ignore")
    
    def to_dict(self):
        """Convert to Elasticsearch source filter format."""
        if not self.includes and not self.excludes:
            return True
        result = {}
        if self.includes:
            result["includes"] = self.includes
        if self.excludes:
            result["excludes"] = self.excludes
        return result


class SearchRequest(BaseModel):
    """
    Search request configuration.
    
    Represents a complete Elasticsearch search request with query,
    aggregations, sorting, and other options.
    """
    index: List[str] = Field(..., description="Index(es) to search")
    query: dict = Field(..., description="Elasticsearch query DSL")
    size: int = Field(10, ge=0, le=10000, description="Number of results")
    from_: int = Field(0, ge=0, alias="from", description="Starting offset")
    sort: Optional[List[dict]] = Field(None, description="Sort criteria")
    aggs: Optional[dict[str, dict]] = Field(None, description="Aggregations")
    highlight: Optional[dict] = Field(None, description="Highlight configuration")
    source: Optional[SourceFilter] = Field(None, alias="_source", description="Source filtering")
    source_enabled: bool = Field(True, description="Whether to return source at all")
    track_total_hits: Optional[bool] = Field(None, description="Track total hits precisely")
    
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    
    def to_dict(self) -> dict:
        """Convert to Elasticsearch query dictionary."""
        query_dict = {
            "query": self.query,
            "size": self.size,
            "from": self.from_
        }
        
        if self.sort:
            query_dict["sort"] = self.sort
        if self.aggs:
            query_dict["aggs"] = self.aggs
        if self.highlight:
            query_dict["highlight"] = self.highlight
        if not self.source_enabled:
            query_dict["_source"] = False
        elif self.source:
            query_dict["_source"] = self.source.to_dict()
        if self.track_total_hits is not None:
            query_dict["track_total_hits"] = self.track_total_hits
            
        return query_dict


class SearchResponse(BaseModel):
    """
    Search response from Elasticsearch.
    
    Represents the complete response from an Elasticsearch search query.
    """
    took: int = Field(..., description="Query execution time in ms")
    timed_out: bool = Field(False, description="Whether query timed out")
    total_hits: int = Field(..., description="Total matching documents")
    max_score: Optional[float] = Field(None, description="Maximum relevance score")
    hits: List[SearchHit] = Field(default_factory=list, description="Search results")
    aggregations: Optional[dict] = Field(None, description="Aggregation results")
    
    model_config = ConfigDict(extra="ignore")
    
    @classmethod
    def from_elasticsearch(cls, response: dict) -> "SearchResponse":
        """Create from raw Elasticsearch response."""
        # Handle different total hits formats from Elasticsearch
        # ES 7+ returns {"value": n, "relation": "eq"}, older versions return just n
        total = response.get("hits", {}).get("total", 0)
        # Try to get value from dict format, fallback to direct value
        try:
            total_hits = total.get("value", 0)
        except AttributeError:
            # Not a dict, use the value directly
            total_hits = total
            
        return cls(
            took=response.get("took", 0),
            timed_out=response.get("timed_out", False),
            total_hits=total_hits,
            max_score=response.get("hits", {}).get("max_score"),
            hits=[SearchHit(**hit) for hit in response.get("hits", {}).get("hits", [])],
            aggregations=response.get("aggregations")
        )