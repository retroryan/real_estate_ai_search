"""
Filter and aggregation models.

Models for Elasticsearch filters and aggregations.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field
from ..enums import AggregationType


class BucketAggregation(BaseModel):
    """Single bucket in an aggregation result."""
    key: str = Field(..., description="Bucket key (converted to string)")
    key_as_string: Optional[str] = Field(None, description="String representation of key")
    doc_count: int = Field(..., ge=0, description="Document count")
    sub_aggregations: Optional[dict] = Field(None, description="Nested aggregations")
    
    @field_validator('key', mode='before')
    @classmethod
    def convert_key_to_string(cls, v):
        """Convert any key type to string."""
        return str(v) if v is not None else "unknown"
    
    model_config = ConfigDict(extra="ignore")


class StatsAggregation(BaseModel):
    """Statistical aggregation result."""
    count: int = Field(..., ge=0, description="Document count")
    min: Optional[float] = Field(None, description="Minimum value")
    max: Optional[float] = Field(None, description="Maximum value")
    avg: Optional[float] = Field(None, description="Average value")
    sum: Optional[float] = Field(None, description="Sum of values")
    std_deviation: Optional[float] = Field(None, description="Standard deviation")
    variance: Optional[float] = Field(None, description="Variance")
    
    model_config = ConfigDict(extra="ignore")
    
    @computed_field
    @property
    def range(self) -> Optional[float]:
        """Calculate range (max - min)."""
        if self.max is not None and self.min is not None:
            return self.max - self.min
        return None


class AggregationResult(BaseModel):
    """Container for aggregation results."""
    name: str = Field(..., description="Aggregation name")
    type: AggregationType = Field(..., description="Type of aggregation")
    buckets: Optional[List[BucketAggregation]] = Field(None, description="Bucket results")
    stats: Optional[StatsAggregation] = Field(None, description="Statistical results")
    value: Optional[float] = Field(None, description="Single value result")
    
    @field_validator('value', mode='before')
    @classmethod
    def convert_value_to_float(cls, v):
        """Convert numeric value to float."""
        if v is not None:
            try:
                return float(v)
            except ValueError:
                # Cannot convert to float
                return None
        return v
    
    model_config = ConfigDict(extra="ignore", use_enum_values=True)


class AggregationClause(BaseModel):
    """Aggregation definition for Elasticsearch."""
    name: str = Field(..., description="Aggregation name")
    type: AggregationType = Field(..., description="Type of aggregation")
    field: Optional[str] = Field(None, description="Field to aggregate")
    params: dict = Field(default_factory=dict, description="Additional parameters")
    sub_aggs: Optional[dict[str, "AggregationClause"]] = Field(None, description="Nested aggregations")
    
    model_config = ConfigDict(extra="ignore", use_enum_values=True)
    
    def to_dict(self) -> dict:
        """Convert to Elasticsearch aggregation format."""
        agg_def: dict = {}
        
        if self.type == AggregationType.TERMS:
            agg_def["terms"] = {"field": self.field, **self.params}
        elif self.type == AggregationType.STATS:
            agg_def["stats"] = {"field": self.field, **self.params}
        elif self.type == AggregationType.EXTENDED_STATS:
            agg_def["extended_stats"] = {"field": self.field, **self.params}
        elif self.type == AggregationType.HISTOGRAM:
            agg_def["histogram"] = {"field": self.field, **self.params}
        elif self.type == AggregationType.DATE_HISTOGRAM:
            agg_def["date_histogram"] = {"field": self.field, **self.params}
        elif self.type == AggregationType.RANGE:
            agg_def["range"] = {"field": self.field, **self.params}
        elif self.type in [AggregationType.AVG, AggregationType.SUM, 
                          AggregationType.MIN, AggregationType.MAX]:
            agg_def[self.type.value] = {"field": self.field, **self.params}
        else:
            agg_def[self.type.value] = self.params
        
        if self.sub_aggs:
            agg_def["aggs"] = {
                sub_name: sub_agg.to_dict() 
                for sub_name, sub_agg in self.sub_aggs.items()
            }
        
        return agg_def


class FilterClause(BaseModel):
    """Filter clause for Elasticsearch queries."""
    field: str = Field(..., description="Field to filter")
    value: str = Field(..., description="Filter value")
    type: str = Field("term", description="Filter type (term, range, exists, etc.)")
    params: dict = Field(default_factory=dict, description="Additional parameters")
    
    model_config = ConfigDict(extra="ignore")
    
    def to_dict(self) -> dict:
        """Convert to Elasticsearch filter format."""
        if self.type == "term":
            return {"term": {self.field: self.value}}
        elif self.type == "terms":
            return {"terms": {self.field: self.value}}
        elif self.type == "range":
            return {"range": {self.field: self.value}}
        elif self.type == "exists":
            return {"exists": {"field": self.field}}
        elif self.type == "prefix":
            return {"prefix": {self.field: self.value}}
        elif self.type == "wildcard":
            return {"wildcard": {self.field: self.value}}
        else:
            return {self.type: {self.field: self.value, **self.params}}


class SortClause(BaseModel):
    """Sort clause for Elasticsearch queries."""
    field: str = Field(..., description="Field to sort by")
    order: str = Field("asc", description="Sort order (asc/desc)")
    mode: Optional[str] = Field(None, description="Sort mode for arrays")
    missing: Optional[str] = Field(None, description="How to handle missing values")
    
    model_config = ConfigDict(extra="ignore")
    
    def to_dict(self) -> dict:
        """Convert to Elasticsearch sort format."""
        sort_def: dict = {"order": self.order}
        if self.mode:
            sort_def["mode"] = self.mode
        if self.missing:
            sort_def["missing"] = self.missing
        return {self.field: sort_def}