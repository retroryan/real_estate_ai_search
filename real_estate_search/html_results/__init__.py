"""HTML Results module for generating formatted output pages."""

from .generator import HTMLResultsGenerator
from .models import (
    HTMLSearchResult,
    HTMLQueryResult,
    HTMLDocument,
    HTMLHighlight
)

__all__ = [
    'HTMLResultsGenerator',
    'HTMLSearchResult',
    'HTMLQueryResult',
    'HTMLDocument',
    'HTMLHighlight'
]