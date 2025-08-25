"""
Utility functions and helpers for the common embeddings module.

Enhanced with correlation validation and chunk reconstruction capabilities.
"""

from .logging import get_logger, setup_logging
from .hashing import hash_text
from .validation import validate_metadata_fields
from .progress import create_progress_indicator, ProgressIndicator
from .correlation import CorrelationValidator, ChunkReconstructor, create_correlation_mappings

__all__ = [
    "get_logger",
    "setup_logging",
    "hash_text",
    "validate_metadata_fields",
    "create_progress_indicator",
    "ProgressIndicator",
    "CorrelationValidator",
    "ChunkReconstructor",
    "create_correlation_mappings",
]