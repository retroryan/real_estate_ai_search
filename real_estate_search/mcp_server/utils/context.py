"""Context management for MCP server tools."""

from typing import Optional, Any, Dict
from dataclasses import dataclass
import uuid


@dataclass
class ToolContext:
    """Context object passed to MCP tools containing services and request info."""
    
    # Services
    config: Any
    es_client: Optional[Any] = None
    embedding_service: Optional[Any] = None
    property_search_service: Optional[Any] = None
    wikipedia_search_service: Optional[Any] = None
    health_check_service: Optional[Any] = None
    hybrid_search_engine: Optional[Any] = None
    
    # Request metadata
    request_id: str = None
    
    def __post_init__(self):
        """Generate request ID if not provided."""
        if not self.request_id:
            self.request_id = str(uuid.uuid4())
    
    def get(self, key: str) -> Optional[Any]:
        """Get a service by name.
        
        Args:
            key: Service name to retrieve
            
        Returns:
            Service instance or None if not found
        """
        return getattr(self, key, None)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for compatibility."""
        return {
            "config": self.config,
            "es_client": self.es_client,
            "embedding_service": self.embedding_service,
            "property_search_service": self.property_search_service,
            "wikipedia_search_service": self.wikipedia_search_service,
            "health_check_service": self.health_check_service,
            "hybrid_search_engine": self.hybrid_search_engine,
            "request_id": self.request_id
        }
    
    @classmethod
    def from_server(cls, server: Any) -> "ToolContext":
        """Create context from MCP server instance.
        
        Args:
            server: MCPServer instance
            
        Returns:
            ToolContext with services from server
        """
        return cls(
            config=server.config,
            es_client=server.es_client,
            embedding_service=server.embedding_service,
            property_search_service=server.property_search_service,
            wikipedia_search_service=server.wikipedia_search_service,
            health_check_service=server.health_check_service,
            hybrid_search_engine=server.hybrid_search_engine
        )