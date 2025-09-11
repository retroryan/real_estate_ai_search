"""
Sort clause models.

Models for Elasticsearch sort criteria.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


class SortClause(BaseModel):
    """Single sort clause for search requests."""
    field: str = Field(..., description="Field to sort by")
    order: Literal["asc", "desc"] = Field("asc", description="Sort order")
    mode: Optional[Literal["min", "max", "sum", "avg", "median"]] = Field(None, description="Sort mode for array fields")
    missing: Optional[str] = Field(None, description="Value to use for missing documents (_first or _last)")
    
    def to_dict(self) -> dict:
        """Convert to Elasticsearch sort format."""
        if self.mode or self.missing:
            sort_config = {"order": self.order}
            if self.mode:
                sort_config["mode"] = self.mode
            if self.missing:
                sort_config["missing"] = self.missing
            return {self.field: sort_config}
        else:
            # Simple format
            return {self.field: self.order}