"""Simple historical data generation for neighborhoods and properties.

Generates 10 years of annual historical data with basic price trends.
No market cycles, no seasonal patterns, just simple appreciation.
"""

import random
from typing import List, Dict, Any, Optional

# Constants for historical data generation
CURRENT_YEAR = 2024
HISTORICAL_YEARS = 10
BASE_APPRECIATION_RATE = 0.05
APPRECIATION_VARIATION = 0.02
PROPERTY_VARIATION = 0.05
DEFAULT_AVG_PRICE = 800000
BASE_SALES_COUNT = 50
MIN_SALES_COUNT = 10


def generate_neighborhood_historical(
    neighborhood_id: str,
    current_avg_price: float = DEFAULT_AVG_PRICE
) -> List[Dict[str, Any]]:
    """Generate simple annual historical data for a neighborhood.
    
    Args:
        neighborhood_id: Unique neighborhood identifier
        current_avg_price: Current average price in the neighborhood
        
    Returns:
        List of 10 annual records with year, avg_price, and sales_count
    """
    records = []
    
    # Use neighborhood_id hash for consistent but varied results
    seed = hash(neighborhood_id) % 10000
    random.seed(seed)
    
    # Work backwards from current year
    price = current_avg_price
    
    # Generate historical years of data
    for year in range(CURRENT_YEAR, CURRENT_YEAR - HISTORICAL_YEARS, -1):
        # Add minor variation to appreciation
        variation = random.uniform(-APPRECIATION_VARIATION, APPRECIATION_VARIATION)
        annual_change = BASE_APPRECIATION_RATE + variation
        
        # Sales count with some variation
        sales_variation = random.randint(-10, 15)
        sales_count = max(MIN_SALES_COUNT, BASE_SALES_COUNT + sales_variation)
        
        # Create record
        record = {
            "year": year,
            "avg_price": float(round(price, 0)),  # Ensure float type for Elasticsearch
            "sales_count": sales_count
        }
        
        records.append(record)
        
        # Calculate previous year's price (working backwards)
        price = price / (1 + annual_change)
    
    # Return in chronological order (2015 first)
    records.reverse()
    
    return records


def generate_property_historical(
    property_id: str,
    current_price: float,
    neighborhood_avg_changes: Optional[List[float]] = None
) -> List[Dict[str, Any]]:
    """Generate simple annual historical data for a property.
    
    Args:
        property_id: Unique property identifier
        current_price: Current property price
        neighborhood_avg_changes: Optional list of neighborhood price changes
        
    Returns:
        List of 10 annual records with year and price
    """
    records = []
    
    # Use property_id hash for consistent but varied results
    seed = hash(property_id) % 10000
    random.seed(seed)
    
    # If no neighborhood changes provided, use default appreciation
    if not neighborhood_avg_changes:
        neighborhood_avg_changes = [BASE_APPRECIATION_RATE] * HISTORICAL_YEARS
    
    # Work backwards from current year
    price = current_price
    
    # Generate historical years of data
    for i, year in enumerate(range(CURRENT_YEAR, CURRENT_YEAR - HISTORICAL_YEARS, -1)):
        # Property varies within +/- 5% of neighborhood average
        base_change = neighborhood_avg_changes[i] if i < len(neighborhood_avg_changes) else BASE_APPRECIATION_RATE
        property_variation = random.uniform(-PROPERTY_VARIATION, PROPERTY_VARIATION)
        
        # Create record
        record = {
            "year": year,
            "price": float(round(price, 0))  # Ensure float type for Elasticsearch
        }
        
        records.append(record)
        
        # Calculate previous year's price (working backwards)
        actual_change = base_change + property_variation
        price = price / (1 + actual_change)
    
    # Return in chronological order (2015 first)
    records.reverse()
    
    return records