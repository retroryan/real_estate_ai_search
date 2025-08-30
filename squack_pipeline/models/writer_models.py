"""Pydantic models for writer operations."""

from typing import List, Optional
from pydantic import BaseModel, Field

from squack_pipeline.writers.elasticsearch.models import WriteResult


class WriteDestinationResults(BaseModel):
    """Results for a specific write destination (Parquet, Elasticsearch, etc)."""
    destination: str = Field(description="Name of the destination (parquet, elasticsearch)")
    results: List[WriteResult] = Field(default_factory=list, description="List of write results")
    total_records: int = Field(default=0, description="Total records written across all results")
    total_failed: int = Field(default=0, description="Total records failed across all results")
    
    def model_post_init(self, __context) -> None:
        """Calculate totals after initialization."""
        self.total_records = sum(r.record_count for r in self.results)
        self.total_failed = sum(r.failed_count for r in self.results)
    
    def is_successful(self) -> bool:
        """Check if all writes to this destination were successful."""
        return all(r.is_successful() for r in self.results) if self.results else False


class WriteOperationResult(BaseModel):
    """Complete result from a write operation to all destinations."""
    parquet: Optional[WriteDestinationResults] = Field(default=None, description="Parquet write results")
    elasticsearch: Optional[WriteDestinationResults] = Field(default=None, description="Elasticsearch write results")
    embeddings_count: int = Field(default=0, ge=0, description="Number of records with embeddings")
    
    def get_total_records(self) -> int:
        """Get total records written across all destinations."""
        total = 0
        if self.parquet:
            total = max(total, self.parquet.total_records)
        if self.elasticsearch:
            total = max(total, self.elasticsearch.total_records)
        return total
    
    def is_successful(self) -> bool:
        """Check if all writes were successful."""
        results = []
        if self.parquet:
            results.append(self.parquet.is_successful())
        if self.elasticsearch:
            results.append(self.elasticsearch.is_successful())
        return all(results) if results else False
    
    def get_errors(self) -> List[str]:
        """Get all error messages."""
        errors = []
        if self.parquet:
            for result in self.parquet.results:
                if result.error:
                    errors.append(f"Parquet: {result.error}")
        if self.elasticsearch:
            for result in self.elasticsearch.results:
                if result.error:
                    errors.append(f"Elasticsearch: {result.error}")
        return errors