"""Elasticsearch writer for SQUACK pipeline."""

from squack_pipeline.writers.elasticsearch.models import (
    EntityType,
    WriteResult,
    BulkOperation,
    TransformationConfig,
)
from squack_pipeline.writers.elasticsearch.writer import ElasticsearchWriter

__all__ = [
    "EntityType",
    "WriteResult",
    "BulkOperation",
    "TransformationConfig",
    "ElasticsearchWriter",
]