"""
Mixed entity result models.

Models for search results containing multiple entity types.
"""

from typing import List, Optional
from pydantic import Field, model_validator
from .base import BaseQueryResult
from ..property import PropertyListing
from ..neighborhood import Neighborhood
from ..wikipedia import WikipediaArticle


class MixedEntityResult(BaseQueryResult):
    """
    Result containing multiple entity types.
    
    Used for searches that return properties, neighborhoods, and Wikipedia articles.
    """
    properties: List[PropertyListing] = Field(default_factory=list, description="Property results")
    neighborhoods: List[Neighborhood] = Field(default_factory=list, description="Neighborhood results")
    wikipedia_articles: List[WikipediaArticle] = Field(default_factory=list, description="Wikipedia results")
    
    @model_validator(mode='before')
    @classmethod
    def handle_compatibility_fields(cls, values):
        """Handle old field names for backward compatibility."""
        # Map old field names to new ones
        if 'property_results' in values and 'properties' not in values:
            values['properties'] = values.pop('property_results')
        if 'neighborhood_results' in values and 'neighborhoods' not in values:
            values['neighborhoods'] = values.pop('neighborhood_results')
        if 'wikipedia_results' in values and 'wikipedia_articles' not in values:
            values['wikipedia_articles'] = values.pop('wikipedia_results')
        return values
    
    # Counts for each entity type
    property_count: int = Field(0, description="Number of properties found")
    neighborhood_count: int = Field(0, description="Number of neighborhoods found")
    wikipedia_count: int = Field(0, description="Number of Wikipedia articles found")
    
    # Compatibility properties for existing code
    @property
    def property_results(self) -> List[PropertyListing]:
        """Alias for properties to maintain compatibility."""
        return self.properties
    
    @property
    def neighborhood_results(self) -> List[Neighborhood]:
        """Alias for neighborhoods to maintain compatibility."""
        return self.neighborhoods
    
    @property
    def wikipedia_results(self) -> List[WikipediaArticle]:
        """Alias for wikipedia_articles to maintain compatibility."""
        return self.wikipedia_articles
    
    def display(self, verbose: bool = False) -> str:
        """Display mixed entity search results."""
        output = []
        output.append(f"\n{self.query_name}")
        output.append("=" * 60)
        if self.query_description:
            output.append(f"Description: {self.query_description}")
        output.append(f"Total hits: {self.total_hits}")
        output.append(f"Execution time: {self.execution_time_ms}ms")
        
        if self.properties:
            output.append(f"\n📍 Properties ({self.property_count} found):")
            for i, prop in enumerate(self.properties[:5], 1):
                output.append(f"{i}. {prop.address.full_address}")
                output.append(f"   {prop.display_price} | {prop.summary}")
        
        if self.neighborhoods:
            output.append(f"\n🏘️ Neighborhoods ({self.neighborhood_count} found):")
            for i, hood in enumerate(self.neighborhoods[:5], 1):
                output.append(f"{i}. {hood.name}, {hood.city}")
                if hood.description:
                    desc = hood.description[:100] + "..." if len(hood.description) > 100 else hood.description
                    output.append(f"   {desc}")
        
        if self.wikipedia_articles:
            output.append(f"\n📚 Wikipedia Articles ({self.wikipedia_count} found):")
            for i, article in enumerate(self.wikipedia_articles[:5], 1):
                output.append(f"{i}. {article.title}")
                if article.summary:
                    summary = article.summary[:100] + "..." if len(article.summary) > 100 else article.summary
                    output.append(f"   {summary}")
        
        if verbose and self.es_features:
            output.append("\nElasticsearch Features:")
            for feature in self.es_features:
                output.append(f"  - {feature}")
        
        return "\n".join(output)