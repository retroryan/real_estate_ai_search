"""Property details demos using MCP client."""

import asyncio
from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from ..client.client import get_mcp_client
from ..utils.models import (
    PropertySearchRequest,
    SearchType,
    DemoResult
)


console = Console()


async def demo_property_details_deep_dive(
    listing_id: str = "prop_001"
) -> DemoResult:
    """Demo 7: Property Details Deep Dive.
    
    Get comprehensive details for a specific property by its listing ID,
    showcasing all available property information.
    
    Args:
        listing_id: Property listing ID to fetch
        
    Returns:
        Demo execution result
    """
    console.print(Panel.fit(
        f"[bold cyan]Demo 7: Property Details Deep Dive[/bold cyan]\n"
        f"Listing ID: {listing_id}",
        border_style="cyan"
    ))
    
    client = get_mcp_client()
    
    try:
        # First, search for a property to get a real ID
        search_request = PropertySearchRequest(
            query="luxury home",
            size=1,
            search_type=SearchType.HYBRID
        )
        search_response = await client.search_properties(search_request)
        
        if search_response.properties:
            # Use the first property's ID
            actual_id = search_response.properties[0].listing_id
            console.print(f"[yellow]Found property: {actual_id}[/yellow]\n")
        else:
            actual_id = listing_id
        
        # Get detailed property information
        result = await client.get_property_details(actual_id)
        
        if "error" not in result:
            property_data = result.get("property", result)
            
            # Create a rich display of property details
            tree = Tree(f"[bold yellow]🏠 Property: {actual_id}[/bold yellow]")
            
            # Basic Information
            basic = tree.add("[cyan]Basic Information[/cyan]")
            basic.add(f"Type: {property_data.get('property_type', 'N/A')}")
            basic.add(f"Price: ${property_data.get('price', 0):,.0f}")
            basic.add(f"Bedrooms: {property_data.get('bedrooms', 'N/A')}")
            basic.add(f"Bathrooms: {property_data.get('bathrooms', 'N/A')}")
            basic.add(f"Square Feet: {property_data.get('square_feet', 'N/A')}")
            
            # Address
            if property_data.get("address"):
                addr_tree = tree.add("[cyan]Address[/cyan]")
                addr = property_data["address"]
                addr_tree.add(f"Street: {addr.get('street', 'N/A')}")
                addr_tree.add(f"City: {addr.get('city', 'N/A')}")
                addr_tree.add(f"State: {addr.get('state', 'N/A')}")
                addr_tree.add(f"ZIP: {addr.get('zip_code', 'N/A')}")
            
            # Features & Amenities
            if property_data.get("amenities"):
                amenities = tree.add("[cyan]Amenities[/cyan]")
                for amenity in property_data["amenities"][:10]:
                    amenities.add(f"✓ {amenity}")
            
            if property_data.get("features"):
                features = tree.add("[cyan]Features[/cyan]")
                for feature in property_data["features"][:10]:
                    features.add(f"★ {feature}")
            
            # Description
            if property_data.get("description"):
                desc_tree = tree.add("[cyan]Description[/cyan]")
                desc = property_data["description"]
                # Break description into lines for better display
                for line in desc[:300].split(". ")[:3]:
                    if line:
                        desc_tree.add(line.strip() + ".")
            
            console.print(tree)
            
            # Additional metadata in a table
            if any(property_data.get(k) for k in ["year_built", "lot_size", "garage", "pool"]):
                metadata_table = Table(title="Additional Details", show_header=False)
                metadata_table.add_column("Property", style="cyan")
                metadata_table.add_column("Value", style="yellow")
                
                if property_data.get("year_built"):
                    metadata_table.add_row("Year Built", str(property_data["year_built"]))
                if property_data.get("lot_size"):
                    metadata_table.add_row("Lot Size", f"{property_data['lot_size']} sq ft")
                if property_data.get("garage"):
                    metadata_table.add_row("Garage", "Yes" if property_data["garage"] else "No")
                if property_data.get("pool"):
                    metadata_table.add_row("Pool", "Yes" if property_data["pool"] else "No")
                
                console.print("\n", metadata_table)
            
            console.print(f"\n[green]✓[/green] Successfully retrieved property details")
            
            return DemoResult(
                demo_name="Property Details Deep Dive",
                success=True,
                execution_time_ms=50,  # Mock timing
                total_results=1,
                returned_results=1,
                sample_results=[property_data]
            )
        else:
            console.print(f"[red]Property not found: {actual_id}[/red]")
            return DemoResult(
                demo_name="Property Details Deep Dive",
                success=False,
                execution_time_ms=0,
                total_results=0,
                returned_results=0,
                sample_results=[],
                error=result.get("error", "Property not found")
            )
            
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")
        return DemoResult(
            demo_name="Property Details Deep Dive",
            success=False,
            execution_time_ms=0,
            total_results=0,
            returned_results=0,
            sample_results=[],
            error=str(e)
        )