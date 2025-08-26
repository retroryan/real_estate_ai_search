"""
Custom exceptions for the data pipeline.

This module defines a hierarchy of exceptions for better error handling
and debugging throughout the pipeline execution.
"""


class PipelineException(Exception):
    """Base exception for all pipeline-related errors."""
    pass


class ConfigurationError(PipelineException):
    """Raised when configuration is invalid or missing."""
    pass


class DataLoadingError(PipelineException):
    """Raised when data loading fails."""
    pass


class EntityExtractionError(PipelineException):
    """Raised when entity extraction fails."""
    pass


class RelationshipBuildingError(PipelineException):
    """Raised when relationship building fails."""
    pass


class EmbeddingGenerationError(PipelineException):
    """Raised when embedding generation fails."""
    pass


class WriterError(PipelineException):
    """Base exception for writer-related errors."""
    pass


class ParquetWriterError(WriterError):
    """Raised when Parquet writing fails."""
    pass


class Neo4jWriterError(WriterError):
    """Raised when Neo4j writing fails."""
    pass


class ValidationError(PipelineException):
    """Raised when data validation fails."""
    pass


class SchemaError(PipelineException):
    """Raised when schema validation or operations fail."""
    pass