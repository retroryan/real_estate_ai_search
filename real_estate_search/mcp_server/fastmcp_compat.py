"""
FastMCP compatibility layer for testing environments.
"""

try:
    from fastmcp import Context
    FASTMCP_AVAILABLE = True
except ImportError:
    # Create mock classes for testing environments
    class Context:
        def __init__(self, *args, **kwargs):
            pass
    
    FASTMCP_AVAILABLE = False

__all__ = ['Context', 'FASTMCP_AVAILABLE']