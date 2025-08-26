"""
ID generation utilities for consistent entity identification.

Provides standardized ID generation functions for all entity types.
"""

import re
from typing import Optional


def normalize_for_id(text: str) -> str:
    """
    Normalize text for use in IDs.
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text suitable for IDs
    """
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace spaces and special characters with underscore
    text = re.sub(r'[^a-z0-9]+', '_', text)
    
    # Remove leading/trailing underscores
    text = text.strip('_')
    
    # Replace multiple underscores with single
    text = re.sub(r'_+', '_', text)
    
    return text


def generate_feature_id(feature_name: str) -> str:
    """
    Generate a standardized feature ID.
    
    Args:
        feature_name: Feature name
        
    Returns:
        Feature ID
    """
    return f"feature:{normalize_for_id(feature_name)}"


def generate_property_type_id(property_type: str) -> str:
    """
    Generate a standardized property type ID.
    
    Args:
        property_type: Property type name
        
    Returns:
        Property type ID
    """
    return f"property_type:{normalize_for_id(property_type)}"


def generate_price_range_id(label: str) -> str:
    """
    Generate a standardized price range ID.
    
    Args:
        label: Price range label
        
    Returns:
        Price range ID
    """
    # Special handling for "+" to "plus"
    label = label.replace("+", "plus")
    return f"price_range:{normalize_for_id(label)}"


def generate_county_id(county_name: str, state: str) -> str:
    """
    Generate a standardized county ID.
    
    Args:
        county_name: County name
        state: State abbreviation
        
    Returns:
        County ID
    """
    county_norm = normalize_for_id(county_name)
    state_norm = normalize_for_id(state)
    return f"county:{county_norm}_{state_norm}"


def generate_topic_cluster_id(category: str) -> str:
    """
    Generate a standardized topic cluster ID.
    
    Args:
        category: Topic category
        
    Returns:
        Topic cluster ID
    """
    return f"topic_cluster:{normalize_for_id(category)}"


def generate_property_id(listing_id: str) -> str:
    """
    Generate a standardized property ID.
    
    Args:
        listing_id: Property listing ID
        
    Returns:
        Property ID
    """
    return f"property:{normalize_for_id(listing_id)}"


def generate_neighborhood_id(neighborhood_name: str, city: Optional[str] = None) -> str:
    """
    Generate a standardized neighborhood ID.
    
    Args:
        neighborhood_name: Neighborhood name
        city: Optional city name for disambiguation
        
    Returns:
        Neighborhood ID
    """
    base_id = f"neighborhood:{normalize_for_id(neighborhood_name)}"
    if city:
        base_id += f"_{normalize_for_id(city)}"
    return base_id


def generate_city_id(city_name: str, state: str) -> str:
    """
    Generate a standardized city ID.
    
    Args:
        city_name: City name
        state: State abbreviation
        
    Returns:
        City ID
    """
    city_norm = normalize_for_id(city_name)
    state_norm = normalize_for_id(state)
    return f"city:{city_norm}_{state_norm}"


def generate_amenity_id(amenity_name: str, location: Optional[str] = None) -> str:
    """
    Generate a standardized amenity ID.
    
    Args:
        amenity_name: Amenity name
        location: Optional location for disambiguation
        
    Returns:
        Amenity ID
    """
    base_id = f"amenity:{normalize_for_id(amenity_name)}"
    if location:
        base_id += f"_{normalize_for_id(location)}"
    return base_id