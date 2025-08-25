"""Enhanced data loading and processing module with Wikipedia integration"""
from .loader import (
    load_property_data,
    validate_property_data,
    get_unique_neighborhoods,
    get_unique_features,
    get_unique_cities,
    categorize_feature,
    load_enhanced_property_data,
    load_wikipedia_data
)

__all__ = [
    'load_property_data',
    'validate_property_data',
    'get_unique_neighborhoods',
    'get_unique_features',
    'get_unique_cities',
    'categorize_feature',
    'load_enhanced_property_data',
    'load_wikipedia_data'
]