"""
Property search result models.

Models for property search results.
"""

from typing import List
from pydantic import Field
from .base import BaseQueryResult
from ..property import PropertyListing


class PropertySearchResult(BaseQueryResult):
    """
    Result for property searches.
    
    Contains property search results.
    """
    results: List[PropertyListing] = Field(..., description="Property search results")
    already_displayed: bool = Field(False, description="Whether results have already been displayed")
    
    def display(self, verbose: bool = False) -> str:
        """Display property search results."""
        if self.already_displayed:
            # Results were already displayed by PropertyDemoRunner
            return ""
        
        output = []
        output.append(f"\n{self.query_name}")
        output.append("=" * 60)
        if self.query_description:
            output.append(f"Description: {self.query_description}")
        output.append(f"Total hits: {self.total_hits}")
        output.append(f"Returned: {self.returned_hits}")
        output.append(f"Execution time: {self.execution_time_ms}ms")
        
        if self.results:
            output.append("\nProperties found:")
            for i, prop in enumerate(self.results[:10], 1):
                output.append(f"{i}. {prop.address.full_address}")
                output.append(f"   {prop.display_price} | {prop.summary}")
                if prop.score:
                    output.append(f"   Score: {prop.score:.2f}")
        
        if verbose and self.es_features:
            output.append("\nElasticsearch Features:")
            for feature in self.es_features:
                output.append(f"  - {feature}")
        
        return "\n".join(output)