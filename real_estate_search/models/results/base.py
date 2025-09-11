"""
Base result models.

Base classes for all search result types.
"""

from typing import List, Optional
from abc import ABC
from pydantic import BaseModel, Field


class BaseQueryResult(BaseModel, ABC):
    """
    Base class for all query results.
    
    Contains common fields for all search results.
    """
    query_name: str = Field(..., description="Name of the demo query")
    query_description: Optional[str] = Field(None, description="Description of what the query searches for")
    execution_time_ms: int = Field(..., description="Query execution time in milliseconds")
    total_hits: int = Field(..., description="Total number of matching documents")
    returned_hits: int = Field(..., description="Number of documents returned")
    query_dsl: dict = Field(..., description="The actual Elasticsearch query used")
    es_features: Optional[List[str]] = Field(None, description="Elasticsearch features demonstrated")
    indexes_used: Optional[List[str]] = Field(None, description="Indexes queried")
    
    def display(self, verbose: bool = False) -> str:
        """Display the query result."""
        # Basic display implementation - subclasses can override
        output = []
        output.append(f"\n{self.query_name}")
        output.append("=" * 60)
        if self.query_description:
            output.append(f"Description: {self.query_description}")
        output.append(f"Total hits: {self.total_hits}")
        output.append(f"Returned: {self.returned_hits}")
        output.append(f"Execution time: {self.execution_time_ms}ms")
        
        if verbose and self.es_features:
            output.append("\nElasticsearch Features:")
            for feature in self.es_features:
                output.append(f"  - {feature}")
        
        return "\n".join(output)