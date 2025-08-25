"""
Custom exceptions for the Property Finder ecosystem.

Provides a hierarchy of exceptions for different error scenarios.
"""


class PropertyFinderError(Exception):
    """Base exception for all Property Finder errors."""
    pass


class ConfigurationError(PropertyFinderError):
    """Raised when configuration is invalid or missing."""
    pass


class DataLoadingError(PropertyFinderError):
    """Raised when data cannot be loaded from source."""
    pass


class StorageError(PropertyFinderError):
    """Raised when storage operations fail."""
    pass


class ValidationError(PropertyFinderError):
    """Raised when data validation fails."""
    pass


class MetadataError(PropertyFinderError):
    """Raised when metadata operations fail."""
    pass