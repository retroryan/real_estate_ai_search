"""Tool wrapper utilities for consistent behavior across MCP tools."""

import functools
import time
import logging
from typing import Callable, Dict, Any, Optional
import asyncio
from .responses import create_error_response

logger = logging.getLogger(__name__)


def with_error_handling(
    tool_name: str,
    error_response_factory: Optional[Callable] = None
):
    """Decorator to add consistent error handling to MCP tools.
    
    Args:
        tool_name: Name of the tool for logging and error responses
        error_response_factory: Optional custom error response factory
        
    Returns:
        Decorated function with error handling
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Dict[str, Any]:
            start_time = time.time()
            
            try:
                # Log tool invocation
                logger.info(
                    f"Tool '{tool_name}' invoked",
                    extra={
                        "tool": tool_name,
                        "args": args,
                        "kwargs": kwargs
                    }
                )
                
                # Execute the tool
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Log successful execution
                execution_time = (time.time() - start_time) * 1000
                logger.info(
                    f"Tool '{tool_name}' completed successfully in {execution_time:.2f}ms",
                    extra={
                        "tool": tool_name,
                        "execution_time_ms": execution_time
                    }
                )
                
                return result
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                
                # Log the error
                logger.error(
                    f"Tool '{tool_name}' failed after {execution_time:.2f}ms: {e}",
                    exc_info=True,
                    extra={
                        "tool": tool_name,
                        "execution_time_ms": execution_time,
                        "error": str(e)
                    }
                )
                
                # Create error response
                if error_response_factory:
                    return error_response_factory(error=e, **kwargs)
                else:
                    # Extract query if present in kwargs
                    query = kwargs.get("query")
                    return create_error_response(
                        error=e,
                        tool_name=tool_name,
                        query=query,
                        **kwargs
                    )
        
        return wrapper
    return decorator


def with_timing(tool_name: str):
    """Decorator to add execution timing to tools.
    
    Args:
        tool_name: Name of the tool for logging
        
    Returns:
        Decorated function with timing
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Dict[str, Any]:
            start_time = time.time()
            
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Add execution time to result if it's a dict
            if isinstance(result, dict):
                result["_execution_time_ms"] = execution_time
            
            return result
        
        return wrapper
    return decorator


def with_validation(
    required_params: Optional[list] = None,
    required_response_fields: Optional[list] = None
):
    """Decorator to add parameter and response validation.
    
    Args:
        required_params: List of required parameter names
        required_response_fields: List of required response field names
        
    Returns:
        Decorated function with validation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Dict[str, Any]:
            # Validate required parameters
            if required_params:
                missing_params = [p for p in required_params if p not in kwargs]
                if missing_params:
                    raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
            
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Validate response fields
            if required_response_fields and isinstance(result, dict):
                missing_fields = [f for f in required_response_fields if f not in result]
                if missing_fields:
                    logger.warning(
                        f"Response missing required fields: {', '.join(missing_fields)}",
                        extra={"function": func.__name__, "result": result}
                    )
            
            return result
        
        return wrapper
    return decorator