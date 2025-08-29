"""Entity-specific writer strategies for output transformations."""

from squack_pipeline.writers.strategies.base_writer_strategy import (
    BaseWriterStrategy,
    WriterConfig
)
from squack_pipeline.writers.strategies.property_writer_strategy import (
    PropertyWriterStrategy
)
from squack_pipeline.writers.strategies.neighborhood_writer_strategy import (
    NeighborhoodWriterStrategy
)
from squack_pipeline.writers.strategies.wikipedia_writer_strategy import (
    WikipediaWriterStrategy
)

__all__ = [
    "BaseWriterStrategy",
    "WriterConfig",
    "PropertyWriterStrategy",
    "NeighborhoodWriterStrategy",
    "WikipediaWriterStrategy"
]