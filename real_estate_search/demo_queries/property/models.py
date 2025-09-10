"""Property search result model."""

import json
from typing import List
from pydantic import Field
from io import StringIO
from rich.console import Console

from real_estate_search.models import PropertyListing
from real_estate_search.demo_queries.result_models import BaseQueryResult
from .common_property_display import PropertyTableDisplay, PropertyDisplayConfig


class PropertySearchResult(BaseQueryResult):
    """Result for property searches."""
    results: List[PropertyListing] = Field(..., description="Property search results")
    
    def display(self, verbose: bool = False) -> str:
        """Format property results for display using common display utilities."""
        string_buffer = StringIO()
        console = Console(file=string_buffer, force_terminal=True, width=150)
        
        # Display header using inherited method
        self._display_header(console)
        
        # Use PropertyTableDisplay for standardized property table rendering
        if self.results:
            # Show top 5 properties
            display_properties = self.results[:5]
            console.print(f"\n🏠 TOP {len(display_properties)} PROPERTY RESULTS:", style="bold magenta")
            
            # Configure display
            config = PropertyDisplayConfig(
                show_description=True,
                show_score=any(r.score for r in display_properties),
                show_details=True,
                score_label="Score",
                table_title="",  # Empty to avoid duplicate title
                max_results=5
            )
            
            # Create PropertyTableDisplay with the console buffer
            property_display = PropertyTableDisplay(console)
            
            # Display properties using standardized display
            property_display.display_properties(
                properties=display_properties,
                config=config,
                total_hits=None,  # Don't show stats here, we handle them separately
                execution_time_ms=None
            )
        
        # Display verbose query DSL if requested
        if verbose:
            console.print(f"\n{'-'*40}", style="dim")
            console.print("Query DSL:", style="bold cyan")
            console.print(f"{'-'*40}", style="dim")
            console.print(json.dumps(self.query_dsl, indent=2), style="green")
        
        output = string_buffer.getvalue()
        string_buffer.close()
        return output