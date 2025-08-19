"""
Custom exceptions for the wiki_summary module.
Provides specific error types for better error handling and debugging.
"""


class WikiSummaryException(Exception):
    """Base exception for all wiki_summary errors."""
    pass


class ProcessingException(WikiSummaryException):
    """Exception raised during article processing."""
    pass


class LLMException(ProcessingException):
    """Exception raised when LLM operations fail."""
    pass


class DatabaseException(WikiSummaryException):
    """Exception raised for database operations."""
    pass


class FileReadException(WikiSummaryException):
    """Exception raised when file reading fails."""
    pass


class HTMLParsingException(WikiSummaryException):
    """Exception raised when HTML parsing fails."""
    pass


class LocationException(WikiSummaryException):
    """Exception raised for location-related operations."""
    pass


class ValidationException(WikiSummaryException):
    """Exception raised for input validation errors."""
    pass


class ConfigurationException(WikiSummaryException):
    """Exception raised for configuration errors."""
    pass