"""Separate result models for different entity types."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
from real_estate_search.models import PropertyListing, WikipediaArticle


class BaseQueryResult(BaseModel):
    """Base class for all query results."""
    query_name: str = Field(..., description="Name of the demo query")
    query_description: Optional[str] = Field(None, description="Description of what the query searches for")
    execution_time_ms: int = Field(..., description="Query execution time in milliseconds")
    total_hits: int = Field(..., description="Total number of matching documents")
    returned_hits: int = Field(..., description="Number of documents returned")
    query_dsl: Dict[str, Any] = Field(..., description="The actual Elasticsearch query used")
    es_features: Optional[List[str]] = Field(None, description="Elasticsearch features demonstrated")
    indexes_used: Optional[List[str]] = Field(None, description="Indexes queried")
    
    @abstractmethod
    def display(self, verbose: bool = False) -> str:
        """Format results for display."""
        pass
    
    def _display_header(self, console, style_buffer=None):
        """Common header display logic."""
        console.print(f"\n{'='*80}", style="cyan")
        console.print(f"🔍 Demo Query: {self.query_name}", style="bold cyan")
        console.print(f"{'='*80}", style="cyan")
        
        if self.query_description:
            console.print(f"\n📝 SEARCH DESCRIPTION:", style="bold yellow")
            console.print(f"   {self.query_description}", style="yellow")
        
        if self.es_features:
            console.print(f"\n📊 ELASTICSEARCH FEATURES:", style="bold green")
            for feature in self.es_features:
                console.print(f"   • {feature}", style="green")
        
        if self.indexes_used:
            console.print(f"\n📁 INDEXES & DOCUMENTS:", style="bold blue")
            for index_info in self.indexes_used:
                console.print(f"   • {index_info}", style="blue")
        
        console.print(f"\n{'─'*80}", style="dim")
        console.print(f"⏱️  Execution Time: {self.execution_time_ms}ms | 📊 Total Hits: {self.total_hits} | 📄 Returned: {self.returned_hits}", style="cyan")




class PropertySearchResult(BaseQueryResult):
    """Result for property searches."""
    results: List[PropertyListing] = Field(..., description="Property search results")
    already_displayed: bool = Field(False, description="Whether results have already been displayed")
    
    def display(self, verbose: bool = False) -> str:
        """Format property results for display."""
        # If already displayed by PropertyDisplayService, show minimal output
        if self.already_displayed:
            import json
            from rich.console import Console
            from io import StringIO
            
            string_buffer = StringIO()
            console = Console(file=string_buffer, force_terminal=True, width=150)
            
            # Only show the technical details section without repeating the query name
            if self.es_features:
                console.print(f"\n📊 ELASTICSEARCH FEATURES:", style="bold green")
                for feature in self.es_features:
                    console.print(f"   • {feature}", style="green")
            
            if self.indexes_used:
                console.print(f"\n📁 INDEXES & DOCUMENTS:", style="bold blue")
                for index_info in self.indexes_used:
                    console.print(f"   • {index_info}", style="blue")
            
            if verbose:
                console.print(f"\n{'-'*40}", style="dim")
                console.print("Query DSL:", style="bold cyan")
                console.print(f"{'-'*40}", style="dim")
                console.print(json.dumps(self.query_dsl, indent=2), style="green")
            
            output = string_buffer.getvalue()
            string_buffer.close()
            return output
        
        # Normal display if not already shown
        import json
        from rich.console import Console
        from rich.table import Table
        from rich.text import Text
        from rich import box
        from io import StringIO
        
        string_buffer = StringIO()
        console = Console(file=string_buffer, force_terminal=True, width=150)
        
        self._display_header(console)
        
        if self.results and len(self.results) > 0:
            console.print(f"\n🏠 TOP 5 PROPERTY RESULTS:", style="bold magenta")
            
            table = Table(
                box=box.ROUNDED,
                show_header=True,
                header_style="bold magenta",
                expand=False,
                padding=(0, 1)
            )
            
            table.add_column("#", style="dim", width=3, justify="center")
            table.add_column("Property Details", style="white", width=35)
            table.add_column("Location", style="blue", width=25)
            table.add_column("Price", style="green bold", justify="right", width=12)
            table.add_column("Description", style="yellow", width=45)
            if any(r.score for r in self.results[:5]):
                table.add_column("Score", style="cyan bold", width=10, justify="center")
            
            for idx, result in enumerate(self.results[:5], 1):
                property_text = Text()
                property_text.append(f"{result.display_property_type}\n", style="bold")
                property_text.append(f"{result.bedrooms}bd/{result.bathrooms}ba • {result.square_feet:,} sqft\n", style="cyan")
                property_text.append(f"Built {result.year_built if result.year_built else 'N/A'}", style="dim")
                
                location = result.address.full_address
                
                price_text = result.display_price
                
                description = result.description
                if len(description) > 100:
                    description = description[:97] + "..."
                
                row_data = [str(idx), property_text, location, price_text, description]
                
                if result.score:
                    row_data.append(f"{result.score:.3f}")
                
                table.add_row(*row_data)
            
            console.print(table)
        
        if verbose:
            console.print(f"\n{'-'*40}", style="dim")
            console.print("Query DSL:", style="bold cyan")
            console.print(f"{'-'*40}", style="dim")
            console.print(json.dumps(self.query_dsl, indent=2), style="green")
        
        output = string_buffer.getvalue()
        string_buffer.close()
        return output



class WikipediaSearchResult(BaseQueryResult):
    """Result for Wikipedia searches."""
    results: List[WikipediaArticle] = Field(..., description="Wikipedia article results")
    
    def display(self, verbose: bool = False) -> str:
        """Format Wikipedia results for display."""
        import json
        from rich.console import Console
        from rich.table import Table
        from rich import box
        from io import StringIO
        
        string_buffer = StringIO()
        console = Console(file=string_buffer, force_terminal=True, width=150)
        
        self._display_header(console)
        
        if self.results and len(self.results) > 0:
            console.print(f"\n📚 TOP WIKIPEDIA ARTICLES:", style="bold magenta")
            
            table = Table(
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan",
                show_lines=True,
                width=None
            )
            
            table.add_column("ID", style="dim", width=8, no_wrap=True)
            table.add_column("Score", style="magenta", justify="right", width=8)
            table.add_column("Title", style="cyan", width=35)
            table.add_column("Location", style="green", width=25)
            table.add_column("Summary", style="bright_blue", overflow="fold", width=50)
            
            for result in self.results[:10]:
                location = f"{result.city or 'N/A'}, {result.state or 'N/A'}"
                
                summary = result.long_summary or ''
                if len(summary) > 150:
                    summary = summary[:147] + "..."
                
                table.add_row(
                    result.page_id[:6] + "..." if len(result.page_id) > 6 else result.page_id,
                    f"{result.score:.2f}" if result.score else "N/A",
                    result.title,
                    location,
                    summary
                )
            
            console.print(table)
        
        if verbose:
            console.print(f"\n{'-'*40}", style="dim")
            console.print("Query DSL:", style="bold cyan")
            console.print(f"{'-'*40}", style="dim")
            console.print(json.dumps(self.query_dsl, indent=2), style="green")
        
        output = string_buffer.getvalue()
        string_buffer.close()
        return output


class AggregationBucket(BaseModel):
    """Individual aggregation bucket."""
    key: str = Field(..., description="Bucket key")
    doc_count: int = Field(..., description="Document count in bucket")
    sub_aggregations: Optional[Dict[str, Any]] = Field(None, description="Sub-aggregations")


class AggregationSearchResult(BaseQueryResult):
    """Result for aggregation queries."""
    aggregations: Dict[str, Any] = Field(..., description="Aggregation results")
    top_properties: List[PropertyListing] = Field(default_factory=list, description="Sample properties if included")
    already_displayed: bool = Field(False, description="Whether results have already been displayed")
    
    def display(self, verbose: bool = False) -> str:
        """Format aggregation results for display."""
        # If already displayed by the aggregation display functions, show minimal output
        if self.already_displayed:
            return self.display_aggregation_metadata(verbose)
        
        # Otherwise show full display
        import json
        from rich.console import Console
        from rich.table import Table
        from rich.text import Text
        from rich import box
        from io import StringIO
        
        string_buffer = StringIO()
        console = Console(file=string_buffer, force_terminal=True, width=150)
        
        self._display_header(console)
        
        # Display aggregations (custom per aggregation type)
        # Note: Aggregation display is handled by the specific demo functions
        # (e.g., display_neighborhood_stats, display_price_distribution)
        # to avoid duplicate output
            
        # Display sample properties if included
        if self.top_properties:
            console.print(f"\n🏠 TOP 5 PROPERTIES IN RANGE:", style="bold magenta")
            
            table = Table(
                box=box.ROUNDED,
                show_header=True,
                header_style="bold magenta",
                expand=False,
                padding=(0, 1)
            )
            
            table.add_column("#", style="dim", width=3, justify="center")
            table.add_column("Property Details", style="white", width=35)
            table.add_column("Location", style="blue", width=25)
            table.add_column("Price", style="green bold", justify="right", width=12)
            table.add_column("Description", style="yellow", width=45)
            
            for idx, result in enumerate(self.top_properties[:5], 1):
                property_text = Text()
                property_text.append(f"{result.property_type}\n", style="bold")
                property_text.append(f"{result.bedrooms}bd/{result.bathrooms}ba • {result.square_feet:,} sqft\n", style="cyan")
                property_text.append(f"Built {result.year_built if result.year_built else 'N/A'}", style="dim")
                
                # Use Address model's properties directly (it's always an Address object now)
                location_parts = []
                if result.address.street:
                    location_parts.append(result.address.street)
                if result.address.city:
                    location_parts.append(result.address.city)
                if result.address.state:
                    location_parts.append(result.address.state)
                location = '\n'.join(location_parts) if location_parts else 'N/A'
                
                price_text = f"${result.price:,.0f}"
                
                description = result.description
                if len(description) > 100:
                    description = description[:97] + "..."
                
                table.add_row(str(idx), property_text, location, price_text, description)
            
            console.print(table)
        
        if verbose:
            console.print(f"\n{'-'*40}", style="dim")
            console.print("Query DSL:", style="bold cyan")
            console.print(f"{'-'*40}", style="dim")
            console.print(json.dumps(self.query_dsl, indent=2), style="green")
        
        output = string_buffer.getvalue()
        string_buffer.close()
        return output
    
    def display_aggregation_metadata(self, verbose: bool = False) -> str:
        """Display only the metadata for aggregation results (no duplicate data)."""
        import json
        from rich.console import Console
        from io import StringIO
        
        string_buffer = StringIO()
        console = Console(file=string_buffer, force_terminal=True, width=150)
        
        # Only show the technical details, not the query name again
        
        if self.es_features:
            console.print(f"\n📊 ELASTICSEARCH FEATURES:", style="bold green")
            for feature in self.es_features:
                console.print(f"   • {feature}", style="green")
        
        if self.indexes_used:
            console.print(f"\n📁 INDEXES & DOCUMENTS:", style="bold blue")
            for index_info in self.indexes_used:
                console.print(f"   • {index_info}", style="blue")
        
        console.print(f"\n{'─'*80}", style="dim")
        console.print(f"⏱️  Execution Time: {self.execution_time_ms}ms | 📊 Total Hits: {self.total_hits} | 📄 Returned: {self.returned_hits}", style="cyan")
        
        if verbose:
            console.print(f"\n{'-'*40}", style="dim")
            console.print("Query DSL:", style="bold cyan")
            console.print(f"{'-'*40}", style="dim")
            console.print(json.dumps(self.query_dsl, indent=2), style="green")
        
        output = string_buffer.getvalue()
        string_buffer.close()
        return output


class MixedEntityResult(BaseQueryResult):
    """Result for multi-entity searches."""
    property_results: List[PropertyListing] = Field(default_factory=list, description="Property results")
    wikipedia_results: List[WikipediaArticle] = Field(default_factory=list, description="Wikipedia results")
    neighborhood_results: List[Dict[str, Any]] = Field(default_factory=list, description="Neighborhood results")
    
    def display(self, verbose: bool = False) -> str:
        """Format mixed entity results for display."""
        import json
        from rich.console import Console
        from rich.table import Table
        from rich.text import Text
        from rich import box
        from io import StringIO
        
        string_buffer = StringIO()
        console = Console(file=string_buffer, force_terminal=True, width=150)
        
        self._display_header(console)
        
        # Display properties
        if self.property_results:
            console.print(f"\n🏠 TOP PROPERTIES:", style="bold magenta")
            
            table = Table(
                box=box.ROUNDED,
                show_header=True,
                header_style="bold magenta",
                expand=False,
                padding=(0, 1)
            )
            
            table.add_column("#", style="dim", width=3, justify="center")
            table.add_column("Property", style="white", width=35)
            table.add_column("Location", style="blue", width=25)
            table.add_column("Price", style="green bold", justify="right", width=12)
            
            for idx, result in enumerate(self.property_results[:5], 1):
                property_text = f"{result.property_type} - {result.bedrooms}bd/{result.bathrooms}ba"
                
                location_parts = []
                if result.address.city:
                    location_parts.append(result.address.city)
                if result.address.state:
                    location_parts.append(result.address.state)
                location = ', '.join(location_parts) if location_parts else 'N/A'
                
                table.add_row(
                    str(idx),
                    property_text,
                    location,
                    f"${result.price:,.0f}"
                )
            
            console.print(table)
        
        if verbose:
            console.print(f"\n{'-'*40}", style="dim")
            console.print("Query DSL:", style="bold cyan")
            console.print(f"{'-'*40}", style="dim")
            console.print(json.dumps(self.query_dsl, indent=2), style="green")
        
        output = string_buffer.getvalue()
        string_buffer.close()
        return output