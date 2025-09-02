"""Core infrastructure for SQUACK Pipeline V2."""

from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import PipelineLogger
from squack_pipeline_v2.core.settings import PipelineSettings

__all__ = [
    "DuckDBConnectionManager",
    "PipelineLogger", 
    "PipelineSettings",
]