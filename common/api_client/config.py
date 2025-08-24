"""API Client Configuration Models."""

from typing import Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class APIClientConfig(BaseModel):
    """Configuration for API clients."""
    
    base_url: HttpUrl = Field(..., description="Base URL for the API")
    timeout: float = Field(default=30.0, description="Request timeout in seconds", gt=0)
    default_headers: Optional[Dict[str, str]] = Field(
        default=None, 
        description="Default headers to include with all requests"
    )
    
    model_config = ConfigDict(validate_assignment=True, extra="forbid")