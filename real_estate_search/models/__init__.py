"""
Unified models for the real estate search application.

This module provides the single source of truth for all data structures
throughout the application.
"""

from .address import Address
from .enums import PropertyType, PropertyStatus, ParkingType
from .property import PropertyListing, Parking
from .wikipedia import WikipediaArticle

__all__ = [
    "Address",
    "PropertyType",
    "PropertyStatus", 
    "ParkingType",
    "PropertyListing",
    "Parking",
    "WikipediaArticle"
]