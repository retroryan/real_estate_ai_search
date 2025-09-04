"""Standardized response utilities for MCP server."""

from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback
import logging

logger = logging.getLogger(__name__)


def create_error_response(
    error: Exception,
    tool_name: str,
    query: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create a standardized error response for any tool.
    
    Args:
        error: The exception that occurred
        tool_name: Name of the tool that failed
        query: Optional query parameter if applicable
        **kwargs: Additional fields to include in the response
    
    Returns:
        Standardized error response dict
    """
    base_response = {
        "success": False,
        "error": str(error),
        "error_type": type(error).__name__,
        "tool": tool_name,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    # Add query if provided
    if query is not None:
        base_response["query"] = query
    
    # Add any additional fields
    base_response.update(kwargs)
    
    # Log the error with traceback for debugging
    logger.error(
        f"Tool '{tool_name}' failed: {error}",
        exc_info=True,
        extra={"tool": tool_name, "query": query}
    )
    
    return base_response


def create_property_error_response(
    error: Exception,
    query: str,
    search_type: str = "hybrid"
) -> Dict[str, Any]:
    """Create an error response specifically for property search tools.
    
    Returns a response that matches the expected PropertySearchResponse structure
    but with empty results and error information.
    """
    return {
        "properties": [],
        "total_results": 0,
        "returned_results": 0,
        "execution_time_ms": 0,
        "query": query,
        "search_type": search_type,
        "location_extracted": None,
        "error": str(error),
        "error_type": type(error).__name__,
        "success": False
    }


def create_wikipedia_error_response(
    error: Exception,
    query: Optional[str] = None,
    city: Optional[str] = None
) -> Dict[str, Any]:
    """Create an error response for Wikipedia search tools."""
    base = {
        "articles": [],
        "total_results": 0,
        "returned_results": 0,
        "execution_time_ms": 0,
        "error": str(error),
        "error_type": type(error).__name__,
        "success": False
    }
    
    if query:
        base["query"] = query
    if city:
        base["city"] = city
        
    return base


def create_details_error_response(
    error: Exception,
    listing_id: str
) -> Dict[str, Any]:
    """Create an error response for property details tools."""
    return {
        "listing_id": listing_id,
        "property": None,
        "error": str(error),
        "error_type": type(error).__name__,
        "success": False
    }


def validate_response(response: Dict[str, Any], required_fields: List[str]) -> bool:
    """Validate that a response contains all required fields.
    
    Args:
        response: Response dict to validate
        required_fields: List of field names that must be present
        
    Returns:
        True if all required fields are present, False otherwise
    """
    return all(field in response for field in required_fields)