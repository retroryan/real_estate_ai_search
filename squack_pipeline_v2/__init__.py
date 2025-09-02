"""SQUACK Pipeline V2 - Clean, stage-based data processing pipeline."""

__version__ = "2.0.0"

from squack_pipeline_v2.core import (
    DuckDBConnectionManager,
    PipelineLogger,
    PipelineSettings,
)

__all__ = [
    "DuckDBConnectionManager",
    "PipelineLogger",
    "PipelineSettings",
]