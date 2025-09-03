"""Pydantic models for demo query inputs and outputs."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime


class PropertySearchParams(BaseModel):
    """Parameters for property search queries."""
    model_config = ConfigDict(populate_by_name=True)
    
    query_text: str = Field(..., description="Search query text")
    size: int = Field(10, description="Number of results to return")
    from_: int = Field(0, description="Offset for pagination", alias="from")


class PropertyFilterParams(BaseModel):
    """Parameters for property filter queries."""
    property_type: Optional[str] = Field(None, description="Property type (condo, single-family, etc)")
    min_bedrooms: Optional[int] = Field(None, description="Minimum number of bedrooms")
    max_bedrooms: Optional[int] = Field(None, description="Maximum number of bedrooms")
    min_bathrooms: Optional[float] = Field(None, description="Minimum number of bathrooms")
    min_price: Optional[float] = Field(None, description="Minimum price")
    max_price: Optional[float] = Field(None, description="Maximum price")
    min_square_feet: Optional[int] = Field(None, description="Minimum square feet")
    max_square_feet: Optional[int] = Field(None, description="Maximum square feet")
    cities: Optional[List[str]] = Field(None, description="List of cities to filter")
    features: Optional[List[str]] = Field(None, description="Required features")
    size: int = Field(10, description="Number of results")
    

class GeoSearchParams(BaseModel):
    """Parameters for geographic search."""
    latitude: float = Field(..., description="Center latitude")
    longitude: float = Field(..., description="Center longitude")
    distance: str = Field("5km", description="Search radius (e.g., '5km', '10mi')")
    size: int = Field(10, description="Number of results")


class AggregationParams(BaseModel):
    """Parameters for aggregation queries."""
    field: str = Field(..., description="Field to aggregate on")
    size: int = Field(20, description="Number of buckets to return")
    include_stats: bool = Field(True, description="Include statistical aggregations")


class SemanticSearchParams(BaseModel):
    """Parameters for semantic similarity search."""
    embedding_vector: Optional[List[float]] = Field(None, description="Embedding vector for similarity")
    query_text: Optional[str] = Field(None, description="Text to generate embedding from")
    min_score: float = Field(0.7, description="Minimum similarity score")
    size: int = Field(10, description="Number of results")


class MultiEntitySearchParams(BaseModel):
    """Parameters for multi-entity search."""
    query_text: str = Field(..., description="Search query text")
    include_properties: bool = Field(True, description="Include property results")
    include_neighborhoods: bool = Field(True, description="Include neighborhood results")
    include_wikipedia: bool = Field(True, description="Include Wikipedia results")
    size_per_index: int = Field(5, description="Results per index")


class PropertyFeatures(BaseModel):
    """Model for property features to ensure consistent structure."""
    bedrooms: Optional[int] = Field(0, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(0, description="Number of bathrooms")
    square_feet: Optional[int] = Field(0, description="Square footage")
    
    @classmethod
    def from_result(cls, result: Dict[str, Any]) -> 'PropertyFeatures':
        """Create PropertyFeatures from a result dict."""
        features = result.get('features', {})
        
        # Try to extract from features dict or fall back to top-level
        try:
            # Try to use features as a dict
            if features:
                bedrooms = features.get('bedrooms', result.get('bedrooms', 0))
                bathrooms = features.get('bathrooms', result.get('bathrooms', 0))
                square_feet = features.get('square_feet', result.get('square_feet', 0))
                return cls(
                    bedrooms=bedrooms,
                    bathrooms=bathrooms,
                    square_feet=square_feet
                )
        except (AttributeError, TypeError):
            # features is not dict-like, fall through to top-level
            pass
        
        # Fall back to top-level fields
        return cls(
            bedrooms=result.get('bedrooms', 0),
            bathrooms=result.get('bathrooms', 0),
            square_feet=result.get('square_feet', 0)
        )


class DemoQueryResult(BaseModel):
    """Standard result format for demo queries."""
    query_name: str = Field(..., description="Name of the demo query")
    query_description: Optional[str] = Field(None, description="Description of what the query searches for")
    execution_time_ms: int = Field(..., description="Query execution time in milliseconds")
    total_hits: int = Field(..., description="Total number of matching documents")
    returned_hits: int = Field(..., description="Number of documents returned")
    results: List[Dict[str, Any]] = Field(..., description="Query results")
    aggregations: Optional[Dict[str, Any]] = Field(None, description="Aggregation results if applicable")
    query_dsl: Dict[str, Any] = Field(..., description="The actual Elasticsearch query used")
    es_features: Optional[List[str]] = Field(None, description="Elasticsearch features demonstrated")
    indexes_used: Optional[List[str]] = Field(None, description="Indexes queried")
    
    def display(self, verbose: bool = False) -> str:
        """Format results for display with top 5 results in a table."""
        import json
        from rich.console import Console
        from rich.table import Table
        from rich.text import Text
        from rich import box
        from io import StringIO
        
        # Create a string buffer to capture rich output
        string_buffer = StringIO()
        console = Console(file=string_buffer, force_terminal=True, width=150)
        
        # Header
        console.print(f"\n{'='*80}", style="cyan")
        console.print(f"🔍 Demo Query: {self.query_name}", style="bold cyan")
        console.print(f"{'='*80}", style="cyan")
        
        # Add search description if provided
        if self.query_description:
            console.print(f"\n📝 SEARCH DESCRIPTION:", style="bold yellow")
            console.print(f"   {self.query_description}", style="yellow")
        
        # Add Elasticsearch features if provided
        if self.es_features:
            console.print(f"\n📊 ELASTICSEARCH FEATURES:", style="bold green")
            for feature in self.es_features:
                console.print(f"   • {feature}", style="green")
        
        # Add indexes used if provided
        if self.indexes_used:
            console.print(f"\n📁 INDEXES & DOCUMENTS:", style="bold blue")
            for index_info in self.indexes_used:
                console.print(f"   • {index_info}", style="blue")
        
        console.print(f"\n{'─'*80}", style="dim")
        console.print(f"⏱️  Execution Time: {self.execution_time_ms}ms | 📊 Total Hits: {self.total_hits} | 📄 Returned: {self.returned_hits}", style="cyan")
        
        # Display top 5 results in a nice table if we have results
        if self.results and len(self.results) > 0:
            console.print(f"\n🏠 TOP 5 SEARCH RESULTS:", style="bold magenta")
            
            table = Table(
                box=box.ROUNDED,
                show_header=True,
                header_style="bold magenta",
                title_style="bold cyan",
                expand=False,
                padding=(0, 1)
            )
            
            # Add columns
            table.add_column("#", style="dim", width=3, justify="center")
            table.add_column("Property Details", style="white", width=35)
            table.add_column("Location", style="blue", width=25)
            table.add_column("Price", style="green bold", justify="right", width=12)
            table.add_column("Description", style="yellow", width=45)
            if any('_hybrid_score' in r for r in self.results[:5]):
                table.add_column("Score", style="cyan bold", width=10, justify="center")
            
            # Add top 5 results
            for idx, result in enumerate(self.results[:5], 1):
                # Property details
                prop_type = result.get('property_type', 'Unknown')
                bedrooms = result.get('bedrooms', 0)
                bathrooms = result.get('bathrooms', 0)
                sqft = result.get('square_feet', 0)
                year_built = result.get('year_built', 'N/A')
                
                property_text = Text()
                property_text.append(f"{prop_type}\n", style="bold")
                property_text.append(f"{bedrooms}bd/{bathrooms}ba • {sqft:,} sqft\n", style="cyan")
                property_text.append(f"Built {year_built}", style="dim")
                
                # Location
                address = result.get('address', {})
                location_parts = []
                if address.get('street'):
                    location_parts.append(address['street'])
                if address.get('city'):
                    location_parts.append(address['city'])
                if address.get('state'):
                    location_parts.append(address['state'])
                location = '\n'.join(location_parts) if location_parts else 'N/A'
                
                # Price
                price = result.get('price', 0)
                price_text = f"${price:,.0f}" if price > 0 else "N/A"
                
                # Description (truncated)
                description = result.get('description', 'No description')
                if len(description) > 100:
                    description = description[:97] + "..."
                
                # Build row
                row_data = [str(idx), property_text, location, price_text, description]
                
                # Add score if it exists
                if '_hybrid_score' in result:
                    score = result.get('_hybrid_score', 0)
                    score_text = f"{score:.3f}"
                    row_data.append(score_text)
                
                table.add_row(*row_data)
            
            console.print(table)
        
        if verbose:
            console.print(f"\n{'-'*40}", style="dim")
            console.print("Query DSL:", style="bold cyan")
            console.print(f"{'-'*40}", style="dim")
            # Show full query DSL without truncation
            console.print(json.dumps(self.query_dsl, indent=2), style="green")
        
        # Get the string output
        output = string_buffer.getvalue()
        string_buffer.close()
        
        return output
    
    def display_location_understanding(self, verbose: bool = False) -> str:
        """Format location understanding results for display."""
        import json
        from rich.console import Console
        from rich.table import Table
        from rich import box
        from io import StringIO
        
        # Create a string buffer to capture rich output
        string_buffer = StringIO()
        console = Console(file=string_buffer, force_terminal=True, width=150)
        
        # Header
        console.print(f"\n{'='*80}", style="cyan")
        console.print(f"🔍 Demo Query: {self.query_name}", style="bold cyan")
        console.print(f"{'='*80}", style="cyan")
        
        # Add search description if provided
        if self.query_description:
            console.print(f"\n📝 SEARCH DESCRIPTION:", style="bold yellow")
            console.print(f"   {self.query_description}", style="yellow")
        
        # Add Elasticsearch features if provided
        if self.es_features:
            console.print(f"\n📊 ELASTICSEARCH FEATURES:", style="bold green")
            for feature in self.es_features:
                console.print(f"   • {feature}", style="green")
        
        console.print(f"\n{'─'*80}", style="dim")
        console.print(f"⏱️  Execution Time: {self.execution_time_ms}ms | 📊 Total Hits: {self.total_hits} | 📄 Returned: {self.returned_hits}", style="cyan")
        
        # Display location extraction results
        if self.results and len(self.results) > 0:
            console.print(f"\n🗺️  LOCATION EXTRACTION RESULTS:", style="bold magenta")
            
            table = Table(
                box=box.ROUNDED,
                show_header=True,
                header_style="bold magenta",
                expand=False,
                padding=(0, 1)
            )
            
            # Add columns for location results
            table.add_column("#", style="dim", width=3, justify="center")
            table.add_column("Query", style="white", width=40)
            table.add_column("City", style="blue", width=20)
            table.add_column("State", style="green", width=15)
            table.add_column("Has Location", style="cyan", width=12, justify="center")
            table.add_column("Cleaned Query", style="yellow", width=30)
            
            # Add results
            for idx, result in enumerate(self.results[:10], 1):  # Show up to 10 location results
                query = result.get('query', 'N/A')
                city = result.get('city', 'N/A') 
                state = result.get('state', 'N/A') or 'N/A'
                has_location = "✅" if result.get('has_location', False) else "❌"
                cleaned_query = result.get('cleaned_query', 'N/A')
                
                # Truncate long text
                if len(query) > 35:
                    query = query[:32] + "..."
                if len(cleaned_query) > 25:
                    cleaned_query = cleaned_query[:22] + "..."
                
                table.add_row(
                    str(idx),
                    query,
                    city,
                    state, 
                    has_location,
                    cleaned_query
                )
            
            console.print(table)
        
        if verbose:
            console.print(f"\n{'-'*40}", style="dim")
            console.print("Query DSL:", style="bold cyan")
            console.print(f"{'-'*40}", style="dim")
            console.print(json.dumps(self.query_dsl, indent=2), style="green")
        
        # Get the string output
        output = string_buffer.getvalue()
        string_buffer.close()
        
        return output


class LocationUnderstandingResult(DemoQueryResult):
    """Specialized result class for location understanding demos."""
    
    def display(self, verbose: bool = False) -> str:
        """Use the specialized location understanding display."""
        return self.display_location_understanding(verbose=verbose)
