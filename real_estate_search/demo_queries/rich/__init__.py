"""
Rich listing demo module for displaying comprehensive property information.

This module provides functionality for retrieving and displaying complete
property listings with embedded neighborhood and Wikipedia data from a
single Elasticsearch query.
"""

from .demo_runner import RichListingDemoRunner
from .models import (
    RichListingModel,
    RichListingSearchResult,
    RichListingDisplayConfig,
    NeighborhoodModel
)

# Main entry point for backwards compatibility
def demo_rich_property_listing(es_client, listing_id=None):
    """
    Run rich property listing demo.
    
    Args:
        es_client: Elasticsearch client
        listing_id: Optional specific listing ID to display
        
    Returns:
        PropertySearchResult with search results
    """
    runner = RichListingDemoRunner(es_client)
    return runner.run_rich_listing(listing_id=listing_id)


# Backwards compatibility
def demo_15(es_client, verbose=False):
    """Demo 15: Rich Real Estate Listing with Single Query."""
    return demo_rich_property_listing(es_client)


__all__ = [
    'RichListingDemoRunner',
    'RichListingModel', 
    'RichListingSearchResult',
    'RichListingDisplayConfig',
    'NeighborhoodModel',
    'demo_rich_property_listing',
    'demo_15'
]