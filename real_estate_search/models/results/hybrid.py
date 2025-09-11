"""
Hybrid search result models.

Models for hybrid search combining vector and text search.
"""

from typing import List, Dict, Any, Optional
from pydantic import Field

from .base import BaseQueryResult


class HybridSearchResult(BaseQueryResult):
    """
    Result from hybrid search combining vector and text search.
    
    Includes properties with hybrid scores from RRF fusion.
    """
    
    results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of properties with hybrid scores"
    )
    
    def display(self, verbose: bool = False) -> str:
        """Display hybrid search results."""
        output = []
        output.append(f"\n{self.query_name}")
        output.append("=" * 60)
        
        if self.query_description:
            output.append(f"\nDescription: {self.query_description}")
        
        output.append(f"\nTotal hits: {self.total_hits}")
        output.append(f"Returned: {self.returned_hits}")
        output.append(f"Execution time: {self.execution_time_ms}ms")
        
        if self.results:
            output.append("\nTop Results (Hybrid Score):")
            for i, result in enumerate(self.results[:5], 1):
                address = result.get('address', {})
                if isinstance(address, dict):
                    address_str = f"{address.get('street', '')} {address.get('city', '')}"
                else:
                    address_str = str(address)
                
                price = result.get('price', 0)
                score = result.get('_hybrid_score', 0)
                
                output.append(f"  {i}. {address_str.strip()} - ${price:,.0f} (Score: {score:.4f})")
        
        if verbose and self.es_features:
            output.append("\nElasticsearch Features:")
            for feature in self.es_features:
                output.append(f"  - {feature}")
        
        return "\n".join(output)