"""Search pipeline DataFrame transformers module.

This module provides DataFrame transformers that replace the anti-pattern
field mapper with Spark-native transformations. Each transformer converts
input DataFrames to the target document schema using explicit, type-safe
transformations.

Transformers follow Spark best practices:
- Use DataFrame API for all transformations
- No collect() operations (stay distributed)
- Explicit column mapping and type casting
- Schema validation using Pydantic models
"""

from .base_transformer import BaseDataFrameTransformer, TransformationResult
from .property_transformer import PropertyDataFrameTransformer
from .neighborhood_transformer import NeighborhoodDataFrameTransformer  
from .wikipedia_transformer import WikipediaDataFrameTransformer

__all__ = [
    "BaseDataFrameTransformer",
    "TransformationResult",
    "PropertyDataFrameTransformer",
    "NeighborhoodDataFrameTransformer",
    "WikipediaDataFrameTransformer",
]