"""Data loading and processing module"""
from .loader import (
    load_property_data,
    validate_property_data,
    get_unique_neighborhoods,
    get_unique_features,
    get_unique_cities,
    categorize_feature
)

__all__ = [
    'load_property_data',
    'validate_property_data',
    'get_unique_neighborhoods',
    'get_unique_features',
    'get_unique_cities',
    'categorize_feature'
]