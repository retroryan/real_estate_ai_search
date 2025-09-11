"""
Wikipedia search result models.

Models for Wikipedia search results.
"""

from typing import List, Optional, Dict
from pydantic import Field
from .base import BaseQueryResult
from ..wikipedia import WikipediaArticle


class WikipediaSearchResult(BaseQueryResult):
    """
    Result for Wikipedia searches.
    
    Contains Wikipedia article search results.
    """
    results: List[WikipediaArticle] = Field(..., description="Wikipedia article results")
    highlights: Optional[dict[str, List[str]]] = Field(None, description="Search highlights")
    
    def display(self, verbose: bool = False) -> str:
        """Display Wikipedia search results."""
        output = []
        # Don't duplicate header - it's already shown by the command runner
        output.append(f"\nSearch Query: {self.query_name.replace('Wikipedia Location Search: ', '')}")
        if self.query_description:
            output.append(f"Description: {self.query_description}")
        output.append(f"Total hits: {self.total_hits}")
        output.append(f"Returned: {self.returned_hits}")
        output.append(f"Execution time: {self.execution_time_ms}ms")
        
        if self.results:
            output.append("\nWikipedia articles found:")
            for i, article in enumerate(self.results[:10], 1):
                output.append(f"{i}. {article.title}")
                # Use short_summary if available, otherwise long_summary
                summary_text = article.short_summary or article.long_summary
                if summary_text:
                    # Show first 150 chars of summary
                    summary = summary_text[:150] + "..." if len(summary_text) > 150 else summary_text
                    output.append(f"   {summary}")
                # Score is not part of WikipediaArticle model
        
        if verbose and self.es_features:
            output.append("\nElasticsearch Features:")
            for feature in self.es_features:
                output.append(f"  - {feature}")
        
        return "\n".join(output)