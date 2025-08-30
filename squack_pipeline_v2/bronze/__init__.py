"""Bronze layer - Raw data ingestion."""

from squack_pipeline_v2.bronze.base import BronzeIngester, BronzeMetadata
from squack_pipeline_v2.bronze.property import PropertyBronzeIngester
from squack_pipeline_v2.bronze.neighborhood import NeighborhoodBronzeIngester
from squack_pipeline_v2.bronze.wikipedia import WikipediaBronzeIngester
from squack_pipeline_v2.bronze.validation import BronzeValidator, BronzeValidationResult

__all__ = [
    "BronzeIngester",
    "BronzeMetadata",
    "PropertyBronzeIngester",
    "NeighborhoodBronzeIngester",
    "WikipediaBronzeIngester",
    "BronzeValidator",
    "BronzeValidationResult",
]