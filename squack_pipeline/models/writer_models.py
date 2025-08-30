"""Pydantic models for writer operations."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from squack_pipeline.writers.elasticsearch.models import WriteResult
from squack_pipeline.models.data_types import OutputDestination


class WriteDestinationResults(BaseModel):
    """Results for a specific write destination (Parquet, Elasticsearch, etc)."""
    destination: OutputDestination = Field(description="Output destination enum")
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
    """Complete result from a write operation to all destinations.
    
    This model is extensible - new destinations can be added without changing the model.
    Results are stored in a dictionary keyed by OutputDestination enum values.
    """
    destinations: Dict[OutputDestination, WriteDestinationResults] = Field(
        default_factory=dict,
        description="Results by destination"
    )
    embeddings_count: int = Field(default=0, ge=0, description="Number of records with embeddings")
    
    def get_total_records(self) -> int:
        """Get total records written across all destinations."""
        if not self.destinations:
            return 0
        # Return the maximum count since all destinations should have same number of records
        return max(dest_result.total_records for dest_result in self.destinations.values())
    
    def is_successful(self) -> bool:
        """Check if all writes were successful."""
        if not self.destinations:
            return False
        return all(dest_result.is_successful() for dest_result in self.destinations.values())
    
    def get_errors(self) -> List[str]:
        """Get all error messages."""
        errors = []
        for destination, dest_result in self.destinations.items():
            for result in dest_result.results:
                if result.error:
                    errors.append(f"{destination.value}: {result.error}")
        return errors
    
    def add_destination_result(self, destination: OutputDestination, result: WriteDestinationResults) -> None:
        """Add results for a destination."""
        self.destinations[destination] = result