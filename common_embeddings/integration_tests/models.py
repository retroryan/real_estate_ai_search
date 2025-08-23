"""
Pydantic models for ChromaDB integration testing.

Defines data structures for test configuration, results, performance metrics,
and test data management with comprehensive validation.
"""

from typing import Dict, Any, List, Optional, Set, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator

from ..models.enums import EntityType, SourceType


class TestStatus(str, Enum):
    """Status of a test execution."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TestCategory(str, Enum):
    """Categories of ChromaDB tests."""
    BASIC_OPERATIONS = "basic_operations"
    SEARCH_QUERIES = "search_queries"
    ADVANCED_FEATURES = "advanced_features"


class DataSample(BaseModel):
    """
    A sample of test data from real datasets.
    
    Represents a single entity (property, neighborhood, or Wikipedia article)
    used for testing with associated metadata.
    """
    
    entity_id: str = Field(description="Primary identifier for the entity")
    entity_type: EntityType = Field(description="Type of entity")
    source_type: SourceType = Field(description="Type of source data")
    
    # Test data content
    text_content: str = Field(description="Text content for embedding generation")
    metadata: Dict[str, Any] = Field(description="Entity metadata for correlation")
    
    # Test configuration
    expected_chunks: int = Field(default=1, ge=1, description="Expected number of chunks")
    is_edge_case: bool = Field(default=False, description="Whether this is an edge case for testing")
    
    # Validation flags
    has_coordinates: bool = Field(default=False, description="Whether entity has geographic coordinates")
    has_rich_metadata: bool = Field(default=False, description="Whether entity has comprehensive metadata")
    
    @validator('text_content')
    def validate_text_content(cls, v):
        """Ensure text content is not empty."""
        if not v.strip():
            raise ValueError("Text content cannot be empty")
        return v
    
    @validator('metadata')
    def validate_required_metadata(cls, v, values):
        """Validate required metadata fields based on entity type."""
        entity_type = values.get('entity_type')
        
        required_fields = ['source_file', 'embedding_id']
        
        if entity_type == EntityType.PROPERTY:
            required_fields.append('listing_id')
        elif entity_type == EntityType.NEIGHBORHOOD:
            required_fields.extend(['neighborhood_id', 'neighborhood_name'])
        elif entity_type in [EntityType.WIKIPEDIA_ARTICLE, EntityType.WIKIPEDIA_SUMMARY]:
            required_fields.append('page_id')
        
        missing_fields = [field for field in required_fields if field not in v]
        if missing_fields:
            raise ValueError(f"Missing required metadata fields: {missing_fields}")
        
        return v


class EmbeddingFixture(BaseModel):
    """
    Pre-generated embedding data for testing.
    
    Avoids expensive embedding generation during test execution.
    """
    
    embedding_id: str = Field(description="Unique embedding identifier")
    vector: List[float] = Field(description="Pre-generated embedding vector")
    entity_id: str = Field(description="Associated entity identifier")
    entity_type: EntityType = Field(description="Type of entity")
    
    # Generation metadata
    model_name: str = Field(description="Model used to generate embedding")
    generated_at: datetime = Field(default_factory=datetime.now, description="Generation timestamp")
    text_hash: str = Field(description="Hash of source text")
    
    @validator('vector')
    def validate_vector_dimensions(cls, v):
        """Validate embedding vector has reasonable dimensions."""
        if len(v) < 100 or len(v) > 2000:
            raise ValueError(f"Embedding vector must have 100-2000 dimensions, got {len(v)}")
        return v


class CollectionTestState(BaseModel):
    """
    State of a ChromaDB collection during testing.
    
    Tracks collection health, content, and test-specific information.
    """
    
    collection_name: str = Field(description="Name of the ChromaDB collection")
    entity_type: EntityType = Field(description="Primary entity type in collection")
    
    # Collection statistics
    total_embeddings: int = Field(ge=0, description="Number of embeddings in collection")
    unique_entities: int = Field(ge=0, description="Number of unique entities")
    chunk_groups: int = Field(ge=0, description="Number of multi-chunk documents")
    
    # Test-specific tracking
    test_embeddings_added: int = Field(default=0, ge=0, description="Embeddings added during tests")
    test_queries_executed: int = Field(default=0, ge=0, description="Queries executed during tests")
    
    # Health indicators
    has_duplicates: bool = Field(default=False, description="Collection has duplicate content")
    has_orphaned_chunks: bool = Field(default=False, description="Collection has orphaned chunks")
    has_missing_metadata: bool = Field(default=False, description="Collection has incomplete metadata")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now, description="Collection creation time")
    last_modified: datetime = Field(default_factory=datetime.now, description="Last modification time")
    
    @property
    def health_score(self) -> float:
        """Calculate collection health score (0.0-1.0)."""
        issues = sum([self.has_duplicates, self.has_orphaned_chunks, self.has_missing_metadata])
        return max(0.0, 1.0 - (issues * 0.33))
    
    @property
    def is_healthy(self) -> bool:
        """Check if collection is in healthy state."""
        return self.health_score >= 0.8


class PerformanceMetrics(BaseModel):
    """
    Performance measurement results for ChromaDB operations.
    
    Comprehensive metrics for latency, throughput, and resource usage.
    """
    
    operation_name: str = Field(description="Name of the operation measured")
    operation_type: str = Field(description="Type of operation (storage, query, etc.)")
    
    # Timing metrics
    total_duration_seconds: float = Field(ge=0.0, description="Total operation duration")
    average_item_duration_ms: float = Field(ge=0.0, description="Average time per item processed")
    
    # Throughput metrics
    items_processed: int = Field(ge=0, description="Number of items processed")
    items_per_second: float = Field(ge=0.0, description="Processing throughput")
    
    # Latency distribution
    p50_latency_ms: float = Field(ge=0.0, description="50th percentile latency")
    p95_latency_ms: float = Field(ge=0.0, description="95th percentile latency")
    p99_latency_ms: float = Field(ge=0.0, description="99th percentile latency")
    
    # Resource usage
    peak_memory_mb: Optional[float] = Field(None, ge=0.0, description="Peak memory usage in MB")
    avg_cpu_percent: Optional[float] = Field(None, ge=0.0, le=100.0, description="Average CPU usage percentage")
    
    # Success metrics
    success_count: int = Field(ge=0, description="Number of successful operations")
    error_count: int = Field(ge=0, description="Number of failed operations")
    
    # Metadata
    measured_at: datetime = Field(default_factory=datetime.now, description="Measurement timestamp")
    
    @property
    def success_rate(self) -> float:
        """Calculate operation success rate."""
        total_ops = self.success_count + self.error_count
        return self.success_count / total_ops if total_ops > 0 else 0.0
    
    @validator('items_per_second')
    def calculate_throughput(cls, v, values):
        """Calculate throughput if not provided."""
        if v == 0.0:
            duration = values.get('total_duration_seconds', 0.0)
            items = values.get('items_processed', 0)
            return items / duration if duration > 0 else 0.0
        return v


class TestResult(BaseModel):
    """
    Result of a single integration test execution.
    
    Comprehensive test outcome with performance data and validation results.
    """
    
    test_name: str = Field(description="Name of the test")
    test_category: TestCategory = Field(description="Category of the test")
    status: TestStatus = Field(description="Test execution status")
    
    # Test execution details
    started_at: datetime = Field(default_factory=datetime.now, description="Test start time")
    completed_at: Optional[datetime] = Field(None, description="Test completion time")
    duration_seconds: Optional[float] = Field(None, ge=0.0, description="Test duration")
    
    # Test results
    assertions_passed: int = Field(default=0, ge=0, description="Number of passed assertions")
    assertions_failed: int = Field(default=0, ge=0, description="Number of failed assertions")
    error_message: Optional[str] = Field(None, description="Error message if test failed")
    
    # Performance data
    performance_metrics: Optional[PerformanceMetrics] = Field(None, description="Performance measurements")
    
    # Test-specific data
    collections_used: List[str] = Field(default_factory=list, description="ChromaDB collections used")
    data_samples_processed: int = Field(default=0, ge=0, description="Number of data samples processed")
    
    # Validation results
    data_integrity_verified: bool = Field(default=False, description="Data integrity validation passed")
    metadata_consistency_verified: bool = Field(default=False, description="Metadata consistency verified")
    
    # Additional context
    test_environment: Dict[str, Any] = Field(default_factory=dict, description="Test environment information")
    notes: List[str] = Field(default_factory=list, description="Additional test notes")
    
    def mark_completed(self, status: TestStatus = TestStatus.PASSED) -> None:
        """Mark test as completed with given status."""
        self.completed_at = datetime.now()
        self.status = status
        if self.started_at and self.completed_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
    
    def add_note(self, note: str) -> None:
        """Add a note to the test result."""
        self.notes.append(f"{datetime.now().isoformat()}: {note}")
    
    @property
    def total_assertions(self) -> int:
        """Get total number of assertions."""
        return self.assertions_passed + self.assertions_failed
    
    @property
    def assertion_success_rate(self) -> float:
        """Calculate assertion success rate."""
        total = self.total_assertions
        return self.assertions_passed / total if total > 0 else 0.0


class TestConfiguration(BaseModel):
    """
    Configuration for ChromaDB integration tests.
    
    Defines test execution parameters, data sources, and validation criteria.
    """
    
    # Test execution configuration
    test_categories: List[TestCategory] = Field(default_factory=lambda: list(TestCategory), description="Categories to run")
    parallel_execution: bool = Field(default=False, description="Enable parallel test execution")
    max_workers: int = Field(default=4, ge=1, le=16, description="Maximum parallel workers")
    
    # Data configuration
    use_real_data: bool = Field(default=True, description="Use real production data for testing")
    max_properties: int = Field(default=50, ge=1, description="Maximum number of properties to test")
    max_neighborhoods: int = Field(default=10, ge=1, description="Maximum number of neighborhoods to test")
    max_wikipedia_articles: int = Field(default=25, ge=1, description="Maximum number of Wikipedia articles to test")
    
    # ChromaDB configuration
    test_collection_prefix: str = Field(default="test_", description="Prefix for test collections")
    cleanup_collections: bool = Field(default=True, description="Clean up test collections after tests")
    chromadb_path: str = Field(default="./test_chromadb", description="Path to test ChromaDB instance")
    
    # Performance testing configuration
    enable_performance_testing: bool = Field(default=True, description="Enable performance measurements")
    performance_iterations: int = Field(default=3, ge=1, description="Number of iterations for performance tests")
    memory_profiling: bool = Field(default=False, description="Enable memory profiling")
    
    # Validation configuration
    strict_validation: bool = Field(default=True, description="Enable strict data validation")
    validate_embedding_precision: bool = Field(default=True, description="Validate embedding vector precision")
    check_metadata_consistency: bool = Field(default=True, description="Check metadata consistency")
    
    # Timeout configuration
    test_timeout_seconds: int = Field(default=300, ge=30, description="Individual test timeout")
    query_timeout_seconds: int = Field(default=30, ge=1, description="ChromaDB query timeout")
    
    @validator('chromadb_path')
    def validate_chromadb_path(cls, v):
        """Ensure ChromaDB path is valid for testing."""
        if 'test' not in v.lower():
            raise ValueError("ChromaDB path must contain 'test' to prevent accidental data overwrite")
        return v


class TestSuite(BaseModel):
    """
    Complete test suite execution results.
    
    Aggregates results from all integration tests with summary statistics.
    """
    
    suite_name: str = Field(description="Name of the test suite")
    configuration: TestConfiguration = Field(description="Test configuration used")
    
    # Execution metadata
    started_at: datetime = Field(default_factory=datetime.now, description="Suite start time")
    completed_at: Optional[datetime] = Field(None, description="Suite completion time")
    total_duration_seconds: Optional[float] = Field(None, description="Total execution time")
    
    # Test results
    test_results: List[TestResult] = Field(default_factory=list, description="Individual test results")
    
    # Summary statistics
    total_tests: int = Field(default=0, ge=0, description="Total number of tests")
    passed_tests: int = Field(default=0, ge=0, description="Number of passed tests")
    failed_tests: int = Field(default=0, ge=0, description="Number of failed tests")
    skipped_tests: int = Field(default=0, ge=0, description="Number of skipped tests")
    
    # Performance summary
    overall_performance: Optional[PerformanceMetrics] = Field(None, description="Aggregated performance metrics")
    
    # Environment information
    test_environment: Dict[str, Any] = Field(default_factory=dict, description="Test execution environment")
    
    def add_test_result(self, result: TestResult) -> None:
        """Add a test result and update statistics."""
        self.test_results.append(result)
        self.total_tests = len(self.test_results)
        
        # Update status counts
        status_counts = {}
        for test_result in self.test_results:
            status_counts[test_result.status] = status_counts.get(test_result.status, 0) + 1
        
        self.passed_tests = status_counts.get(TestStatus.PASSED, 0)
        self.failed_tests = status_counts.get(TestStatus.FAILED, 0)
        self.skipped_tests = status_counts.get(TestStatus.SKIPPED, 0)
    
    def mark_completed(self) -> None:
        """Mark test suite as completed."""
        self.completed_at = datetime.now()
        if self.started_at and self.completed_at:
            self.total_duration_seconds = (self.completed_at - self.started_at).total_seconds()
    
    @property
    def success_rate(self) -> float:
        """Calculate test suite success rate."""
        return self.passed_tests / self.total_tests if self.total_tests > 0 else 0.0
    
    @property
    def is_successful(self) -> bool:
        """Check if test suite passed (all tests passed)."""
        return self.failed_tests == 0 and self.total_tests > 0
    
    def get_summary(self) -> str:
        """Get human-readable test suite summary."""
        status = "✅ PASSED" if self.is_successful else "❌ FAILED" if self.failed_tests > 0 else "⚠️ INCOMPLETE"
        
        return (f"{status} - {self.total_tests} tests, "
                f"{self.passed_tests} passed, {self.failed_tests} failed, {self.skipped_tests} skipped, "
                f"completed in {self.total_duration_seconds:.1f}s" if self.total_duration_seconds else "in progress")


class ValidationError(BaseModel):
    """
    Data validation error found during testing.
    
    Represents issues with test data, ChromaDB state, or assertion failures.
    """
    
    error_type: str = Field(description="Type of validation error")
    error_message: str = Field(description="Detailed error message")
    context: Dict[str, Any] = Field(default_factory=dict, description="Error context information")
    
    # Location information
    test_name: Optional[str] = Field(None, description="Test where error occurred")
    collection_name: Optional[str] = Field(None, description="ChromaDB collection involved")
    entity_id: Optional[str] = Field(None, description="Entity identifier involved")
    
    # Severity
    is_critical: bool = Field(default=False, description="Whether this is a critical error")
    
    # Timestamp
    detected_at: datetime = Field(default_factory=datetime.now, description="When error was detected")
    
    def __str__(self) -> str:
        """String representation of validation error."""
        severity = "CRITICAL" if self.is_critical else "WARNING"
        location = f" in {self.test_name}" if self.test_name else ""
        return f"[{severity}] {self.error_type}: {self.error_message}{location}"