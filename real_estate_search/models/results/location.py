"""
Location understanding result models.

Models for location extraction and understanding results.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from .base import BaseQueryResult


class LocationExtractionResult(BaseModel):
    """Single location extraction result."""
    query: str = Field(..., description="Original query text")
    city: Optional[str] = Field(None, description="Extracted city")
    state: Optional[str] = Field(None, description="Extracted state")
    neighborhood: Optional[str] = Field(None, description="Extracted neighborhood")
    zip_code: Optional[str] = Field(None, description="Extracted ZIP code")
    has_location: bool = Field(..., description="Whether location was found")
    cleaned_query: str = Field(..., description="Query with location removed")
    confidence: float = Field(..., description="Extraction confidence score")
    error: Optional[str] = Field(None, description="Error message if extraction failed")


class LocationUnderstandingResult(BaseQueryResult):
    """
    Result from location understanding demo.
    
    Contains extracted location information from natural language queries.
    """
    results: List[dict] = Field(default_factory=list, description="Location extraction results")
    
    def display(self, verbose: bool = False) -> str:
        """Display location understanding results."""
        output = []
        output.append(f"\n{self.query_name}")
        output.append("=" * 60)
        if self.query_description:
            output.append(f"Description: {self.query_description}")
        output.append(f"Total hits: {self.total_hits}")
        output.append(f"Returned: {self.returned_hits}")
        output.append(f"Execution time: {self.execution_time_ms}ms")
        
        if self.results:
            output.append("\nLocation Extraction Results:")
            output.append("-" * 40)
            for result in self.results:
                if "error" in result:
                    output.append(f"\nQuery: '{result['query']}'")
                    output.append(f"  Error: {result['error']}")
                else:
                    output.append(f"\nQuery: '{result['query']}'")
                    city = result.get('city', 'None')
                    state = result.get('state', 'None')
                    output.append(f"  Location: {city}, {state}")
                    output.append(f"  Cleaned: '{result.get('cleaned_query', '')}'")
                    output.append(f"  Has Location: {result.get('has_location', False)}")
                    if 'confidence' in result:
                        output.append(f"  Confidence: {result['confidence']:.2f}")
        
        if verbose and self.es_features:
            output.append("\nElasticsearch Features:")
            for feature in self.es_features:
                output.append(f"  - {feature}")
        
        return "\n".join(output)