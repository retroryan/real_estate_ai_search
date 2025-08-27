"""
Search pipeline module for Elasticsearch document processing.

This module provides a dedicated pipeline for transforming and indexing
data to Elasticsearch, separate from the graph processing pipeline.
It receives DataFrames from the pipeline fork and processes them for search.
"""

from data_pipeline.search_pipeline.core.search_runner import SearchPipelineRunner
from data_pipeline.search_pipeline.models.config import SearchPipelineConfig, ElasticsearchConfig

__all__ = [
    "SearchPipelineRunner",
    "SearchPipelineConfig", 
    "ElasticsearchConfig",
]

__version__ = "1.0.0"