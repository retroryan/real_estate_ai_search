"""
Result models for search pipeline operations.

Provides Pydantic models for tracking results and statistics
from search pipeline operations.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class SearchIndexResult(BaseModel):
    """Result from indexing documents to Elasticsearch."""
    
    entity_type: str = Field(
        description="Type of entity indexed"
    )
    index_name: str = Field(
        description="Name of the Elasticsearch index"
    )
    documents_indexed: int = Field(
        default=0,
        ge=0,
        description="Number of documents successfully indexed"
    )
    documents_failed: int = Field(
        default=0,
        ge=0,
        description="Number of documents that failed to index"
    )
    duration_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Time taken to index documents"
    )
    error_messages: List[str] = Field(
        default_factory=list,
        description="Any error messages encountered"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the indexing completed"
    )
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate of indexing."""
        total = self.documents_indexed + self.documents_failed
        if total == 0:
            return 0.0
        return (self.documents_indexed / total) * 100.0
    
    @property
    def documents_per_second(self) -> float:
        """Calculate indexing throughput."""
        if self.duration_seconds == 0:
            return 0.0
        return self.documents_indexed / self.duration_seconds


class SearchPipelineResult(BaseModel):
    """Overall result from search pipeline execution."""
    
    pipeline_id: str = Field(
        description="Unique identifier for this pipeline run"
    )
    start_time: datetime = Field(
        description="When the pipeline started"
    )
    end_time: Optional[datetime] = Field(
        default=None,
        description="When the pipeline completed"
    )
    entity_results: Dict[str, SearchIndexResult] = Field(
        default_factory=dict,
        description="Results for each entity type processed"
    )
    total_documents_indexed: int = Field(
        default=0,
        ge=0,
        description="Total documents indexed across all entities"
    )
    total_documents_failed: int = Field(
        default=0,
        ge=0,
        description="Total documents that failed to index"
    )
    success: bool = Field(
        default=False,
        description="Whether the pipeline completed successfully"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Overall error message if pipeline failed"
    )
    
    def add_entity_result(self, result: SearchIndexResult) -> None:
        """
        Add an entity indexing result.
        
        Args:
            result: Result from indexing an entity type
        """
        self.entity_results[result.entity_type] = result
        self.total_documents_indexed += result.documents_indexed
        self.total_documents_failed += result.documents_failed
    
    def complete(self, success: bool = True, error: Optional[str] = None) -> None:
        """
        Mark the pipeline as complete.
        
        Args:
            success: Whether the pipeline completed successfully
            error: Error message if pipeline failed
        """
        self.end_time = datetime.now()
        self.success = success
        self.error_message = error
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate total pipeline duration."""
        if not self.end_time:
            return None
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def overall_success_rate(self) -> float:
        """Calculate overall success rate across all entities."""
        total = self.total_documents_indexed + self.total_documents_failed
        if total == 0:
            return 0.0
        return (self.total_documents_indexed / total) * 100.0
    
    def get_summary(self) -> str:
        """
        Get a human-readable summary of the pipeline results.
        
        Returns:
            Summary string
        """
        lines = [
            f"Search Pipeline Result (ID: {self.pipeline_id})",
            f"Status: {'Success' if self.success else 'Failed'}",
        ]
        
        if self.duration_seconds:
            lines.append(f"Duration: {self.duration_seconds:.2f} seconds")
        
        lines.extend([
            f"Documents Indexed: {self.total_documents_indexed:,}",
            f"Documents Failed: {self.total_documents_failed:,}",
            f"Success Rate: {self.overall_success_rate:.1f}%",
        ])
        
        if self.entity_results:
            lines.append("\nEntity Results:")
            for entity_type, result in self.entity_results.items():
                lines.append(
                    f"  {entity_type}: {result.documents_indexed:,} indexed, "
                    f"{result.documents_failed:,} failed "
                    f"({result.success_rate:.1f}% success)"
                )
        
        if self.error_message:
            lines.append(f"\nError: {self.error_message}")
        
        return "\n".join(lines)