"""
Data Pipeline Module for Property Finder.

A Spark-based data processing pipeline for real estate and Wikipedia data
with support for embeddings and graph database output.

This module can be run as:
    python -m data_pipeline (from parent directory)
    python data_pipeline/__main__.py (from parent directory)
"""

__version__ = "2.0.0"

# Export main components for easier imports
from .core.pipeline_runner import DataPipelineRunner
from .config.loader import load_configuration
from .config.models import PipelineConfig

__all__ = [
    "DataPipelineRunner",
    "load_configuration",
    "PipelineConfig",
]