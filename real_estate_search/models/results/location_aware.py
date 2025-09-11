"""
Location-aware search result models.

Models for location-aware search results that combine location understanding
with property search results.
"""

from typing import List, Optional, Any, Dict
from pydantic import Field
from .base import BaseQueryResult


class LocationAwareSearchResult(BaseQueryResult):
    """
    Result from location-aware search queries.
    
    Contains property search results with location context from natural language queries.
    """
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Property search results")
    location_intent: Optional[Dict[str, Any]] = Field(None, description="Extracted location information")
    
    def display(self, verbose: bool = False) -> str:
        """Display location-aware search results."""
        output = []
        output.append(f"\n{self.query_name}")
        output.append("=" * 60)
        if self.query_description:
            output.append(f"Description: {self.query_description}")
        output.append(f"Total hits: {self.total_hits}")
        output.append(f"Returned: {self.returned_hits}")
        output.append(f"Execution time: {self.execution_time_ms}ms")
        
        # Display location understanding
        if self.location_intent:
            output.append("\nLocation Extracted:")
            city = self.location_intent.get('city', 'N/A')
            state = self.location_intent.get('state', 'N/A') 
            output.append(f"  City: {city}")
            output.append(f"  State: {state}")
            if 'cleaned_query' in self.location_intent:
                output.append(f"  Search terms: {self.location_intent['cleaned_query']}")
        
        # Display properties found
        if self.results:
            output.append(f"\nProperties Found ({len(self.results)}):")
            for i, prop in enumerate(self.results[:10], 1):
                address = prop.get('address', {})
                street = address.get('street', 'Unknown')
                city = address.get('city', '')
                state = address.get('state', '')
                location = f"{city}, {state}" if city else "Unknown"
                
                price = prop.get('price', 0)
                price_str = f"${price/1000000:.1f}M" if price >= 1000000 else f"${price/1000:.0f}K"
                
                prop_type = prop.get('property_type', 'Unknown')
                bedrooms = prop.get('bedrooms', 0)
                bathrooms = prop.get('bathrooms', 0)
                
                output.append(f"{i:2}. {street}")
                output.append(f"    {location} • {price_str} • {bedrooms}bd/{bathrooms}ba • {prop_type}")
                
                # Show hybrid score if available
                if '_hybrid_score' in prop:
                    output.append(f"    Score: {prop['_hybrid_score']:.3f}")
        
        if verbose and self.es_features:
            output.append("\nElasticsearch Features:")
            for feature in self.es_features:
                output.append(f"  - {feature}")
        
        return "\n".join(output)