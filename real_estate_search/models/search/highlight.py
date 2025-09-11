"""
Highlight configuration models.

Models for Elasticsearch highlight configuration.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class HighlightField(BaseModel):
    """Configuration for a specific field's highlighting."""
    fragment_size: Optional[int] = Field(150, description="Size of highlighted fragments")
    number_of_fragments: Optional[int] = Field(3, description="Number of fragments to return")
    pre_tags: Optional[List[str]] = Field(None, description="Pre-highlight tags")
    post_tags: Optional[List[str]] = Field(None, description="Post-highlight tags")


class HighlightConfiguration(BaseModel):
    """Elasticsearch highlight configuration."""
    fields: dict[str, HighlightField] = Field(..., description="Fields to highlight")
    pre_tags: Optional[List[str]] = Field(["<em>"], description="Default pre-highlight tags")
    post_tags: Optional[List[str]] = Field(["</em>"], description="Default post-highlight tags")
    fragment_size: Optional[int] = Field(150, description="Default fragment size")
    number_of_fragments: Optional[int] = Field(3, description="Default number of fragments")
    encoder: Optional[str] = Field(None, description="Encoder type (default, html)")
    
    def to_dict(self) -> dict:
        """Convert to Elasticsearch highlight format."""
        config = {}
        
        # Add global settings
        if self.pre_tags:
            config["pre_tags"] = self.pre_tags
        if self.post_tags:
            config["post_tags"] = self.post_tags
        if self.fragment_size:
            config["fragment_size"] = self.fragment_size
        if self.number_of_fragments:
            config["number_of_fragments"] = self.number_of_fragments
        if self.encoder:
            config["encoder"] = self.encoder
            
        # Add field-specific settings
        if self.fields:
            config["fields"] = {}
            for field_name, field_config in self.fields.items():
                config["fields"][field_name] = field_config.model_dump(exclude_none=True)
                
        return config