"""
Pydantic models for CLI management operations.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


class CommandType(str, Enum):
    """Available management commands."""
    SETUP_INDICES = "setup-indices"
    VALIDATE_INDICES = "validate-indices"
    VALIDATE_EMBEDDINGS = "validate-embeddings"
    LIST_INDICES = "list-indices"
    DELETE_TEST_INDICES = "delete-test-indices"
    DEMO = "demo"


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class IndexOperationResult(BaseModel):
    """Result of an index operation."""
    index_name: str
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


class ValidationStatus(BaseModel):
    """Status of index validation."""
    index_name: str
    exists: bool
    health: Optional[str] = None
    docs_count: Optional[int] = None
    store_size_bytes: Optional[int] = None
    mapping_valid: bool
    error_message: Optional[str] = None


class EmbeddingValidationResult(BaseModel):
    """Result of embedding validation for an entity type."""
    entity_type: str
    index_name: str
    total_docs: int
    docs_with_embeddings: int
    percentage: float
    embedding_dimension: Optional[int] = None
    embedding_model: Optional[str] = None
    status: str = Field(description="Status indicator: ✓, ⚠, or ✗")

    @field_validator('percentage')
    @classmethod
    def validate_percentage(cls, v: float) -> float:
        """Ensure percentage is between 0 and 100."""
        return min(max(v, 0.0), 100.0)


class ClusterHealthInfo(BaseModel):
    """Elasticsearch cluster health information."""
    status: str
    number_of_nodes: int
    active_primary_shards: int
    active_shards: int
    unassigned_shards: Optional[int] = None


class DemoQuery(BaseModel):
    """Information about a demo query."""
    number: int
    name: str
    description: str
    query_function: Optional[str] = None


class DemoExecutionResult(BaseModel):
    """Result of executing a demo query."""
    demo_number: int
    demo_name: str
    success: bool
    execution_time_ms: Optional[float] = None
    total_hits: Optional[int] = None
    returned_hits: Optional[int] = None
    error: Optional[str] = None
    query_dsl: Optional[Dict[str, Any]] = None


class CLIArguments(BaseModel):
    """Parsed CLI arguments."""
    command: CommandType
    demo_number: Optional[int] = Field(default=None, ge=1, le=11)
    clear: bool = False
    list: bool = False
    verbose: bool = False
    config_path: str = "config.yaml"
    log_level: LogLevel = LogLevel.INFO


class OperationStatus(BaseModel):
    """Overall operation status."""
    operation: str
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None