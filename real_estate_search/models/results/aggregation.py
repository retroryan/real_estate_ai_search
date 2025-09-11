"""
Aggregation result models.

Models for aggregation search results.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from .base import BaseQueryResult


class AggregationBucket(BaseModel):
    """Individual bucket in aggregation results."""
    key: str = Field(..., description="Bucket key")
    doc_count: int = Field(..., description="Number of documents in bucket")
    stats: Optional[dict[str, float]] = Field(None, description="Statistical values if requested")
    sub_buckets: Optional[List["AggregationBucket"]] = Field(None, description="Nested buckets")


class AggregationSearchResult(BaseQueryResult):
    """
    Result for aggregation queries.
    
    Contains aggregation results.
    """
    aggregation_name: str = Field("Aggregation", description="Name of the aggregation")
    aggregation_type: str = Field("terms", description="Type of aggregation performed")
    buckets: List[AggregationBucket] = Field(default_factory=list, description="Aggregation buckets")
    stats: Optional[dict[str, float]] = Field(None, description="Statistical aggregation results")
    value: Optional[float] = Field(None, description="Single value result (for metrics aggregations)")
    
    # Additional fields for compatibility with existing demos
    aggregations: Optional[dict] = Field(None, description="Raw aggregation results from Elasticsearch")
    top_properties: Optional[List] = Field(None, description="Top properties from the aggregation")
    already_displayed: bool = Field(False, description="Whether results have already been displayed")
    
    def display(self, verbose: bool = False) -> str:
        """Display aggregation results."""
        output = []
        output.append(f"\n{self.query_name}")
        output.append("=" * 60)
        if self.query_description:
            output.append(f"Description: {self.query_description}")
        output.append(f"Aggregation: {self.aggregation_name} ({self.aggregation_type})")
        output.append(f"Execution time: {self.execution_time_ms}ms")
        
        if self.buckets:
            output.append("\nAggregation buckets:")
            for bucket in self.buckets[:20]:
                output.append(f"  {bucket.key}: {bucket.doc_count} documents")
                if bucket.stats:
                    for stat_name, stat_value in bucket.stats.items():
                        output.append(f"    {stat_name}: {stat_value:.2f}")
        
        if self.stats:
            output.append("\nStatistics:")
            for stat_name, stat_value in self.stats.items():
                output.append(f"  {stat_name}: {stat_value:.2f}")
        
        if self.value is not None:
            output.append(f"\nValue: {self.value:.2f}")
        
        if verbose and self.es_features:
            output.append("\nElasticsearch Features:")
            for feature in self.es_features:
                output.append(f"  - {feature}")
        
        return "\n".join(output)