"""
Elasticsearch aggregation builder for faceted search.
All aggregations use typed enums and models.
"""

from typing import Dict, Any, List, Optional
import structlog

from real_estate_search.indexer.enums import FieldName
from .enums import AggregationName, PriceRange


logger = structlog.get_logger(__name__)


class AggregationBuilder:
    """
    Builds Elasticsearch aggregations for faceted search.
    Uses enums for all aggregation names and field references.
    """
    
    def __init__(self):
        """Initialize the aggregation builder."""
        self.logger = logger.bind(component="AggregationBuilder")
    
    def build_standard_aggregations(self) -> Dict[str, Any]:
        """
        Build standard set of aggregations for property search.
        
        Returns:
            Dictionary of aggregation definitions
        """
        aggregations = {}
        
        # Price range aggregation
        aggregations[AggregationName.PRICE_RANGES] = self._build_price_ranges()
        
        # Price histogram for dynamic ranges
        aggregations[AggregationName.PRICE_HISTOGRAM] = self._build_price_histogram()
        
        # Property type distribution
        aggregations[AggregationName.PROPERTY_TYPES] = self._build_terms_aggregation(
            FieldName.PROPERTY_TYPE,
            size=20
        )
        
        # Location aggregations
        aggregations[AggregationName.CITIES] = self._build_terms_aggregation(
            FieldName.ADDRESS_CITY,
            size=30
        )
        
        aggregations[AggregationName.NEIGHBORHOODS] = self._build_terms_aggregation(
            f"{FieldName.NEIGHBORHOOD_NAME}.keyword",
            size=50
        )
        
        # Bedroom and bathroom counts
        aggregations[AggregationName.BEDROOM_COUNTS] = self._build_terms_aggregation(
            FieldName.BEDROOMS,
            size=10
        )
        
        aggregations[AggregationName.BATHROOM_COUNTS] = self._build_terms_aggregation(
            FieldName.BATHROOMS,
            size=10
        )
        
        # Features and amenities
        aggregations[AggregationName.FEATURES_FACET] = self._build_terms_aggregation(
            FieldName.FEATURES,
            size=30
        )
        
        aggregations[AggregationName.AMENITIES_FACET] = self._build_terms_aggregation(
            FieldName.AMENITIES,
            size=30
        )
        
        # Status distribution
        aggregations[AggregationName.STATUS_DISTRIBUTION] = self._build_terms_aggregation(
            FieldName.STATUS,
            size=10
        )
        
        # Statistical aggregations
        aggregations[AggregationName.PRICE_STATS] = self._build_stats_aggregation(
            FieldName.PRICE
        )
        
        aggregations[AggregationName.SQFT_STATS] = self._build_stats_aggregation(
            FieldName.SQUARE_FEET
        )
        
        # Year built ranges
        aggregations[AggregationName.YEAR_BUILT_RANGES] = self._build_year_built_ranges()
        
        return aggregations
    
    def build_custom_aggregations(
        self,
        requested_aggregations: List[AggregationName]
    ) -> Dict[str, Any]:
        """
        Build only requested aggregations.
        
        Args:
            requested_aggregations: List of aggregation names to build
            
        Returns:
            Dictionary of requested aggregation definitions
        """
        all_aggregations = self.build_standard_aggregations()
        
        return {
            name: definition
            for name, definition in all_aggregations.items()
            if name in requested_aggregations
        }
    
    def _build_price_ranges(self) -> Dict[str, Any]:
        """
        Build price range aggregation with predefined buckets.
        
        Returns:
            Range aggregation definition
        """
        return {
            "range": {
                "field": FieldName.PRICE,
                "ranges": [
                    {"to": 300000, "key": PriceRange.UNDER_300K},
                    {"from": 300000, "to": 500000, "key": PriceRange.RANGE_300K_500K},
                    {"from": 500000, "to": 750000, "key": PriceRange.RANGE_500K_750K},
                    {"from": 750000, "to": 1000000, "key": PriceRange.RANGE_750K_1M},
                    {"from": 1000000, "key": PriceRange.OVER_1M}
                ]
            }
        }
    
    def _build_price_histogram(self, interval: int = 50000) -> Dict[str, Any]:
        """
        Build price histogram for dynamic price distribution.
        
        Args:
            interval: Price interval for histogram buckets
            
        Returns:
            Histogram aggregation definition
        """
        return {
            "histogram": {
                "field": FieldName.PRICE,
                "interval": interval,
                "min_doc_count": 1
            }
        }
    
    def _build_year_built_ranges(self) -> Dict[str, Any]:
        """
        Build year built range aggregation.
        
        Returns:
            Range aggregation for year built
        """
        return {
            "range": {
                "field": FieldName.YEAR_BUILT,
                "ranges": [
                    {"to": 1950, "key": "Pre-1950"},
                    {"from": 1950, "to": 1980, "key": "1950-1980"},
                    {"from": 1980, "to": 2000, "key": "1980-2000"},
                    {"from": 2000, "to": 2010, "key": "2000-2010"},
                    {"from": 2010, "to": 2020, "key": "2010-2020"},
                    {"from": 2020, "key": "2020+"}
                ]
            }
        }
    
    def _build_terms_aggregation(
        self,
        field: str,
        size: int = 10,
        order_by_count: bool = True
    ) -> Dict[str, Any]:
        """
        Build a terms aggregation for categorical data.
        
        Args:
            field: Field name to aggregate on
            size: Maximum number of buckets to return
            order_by_count: Whether to order by document count
            
        Returns:
            Terms aggregation definition
        """
        aggregation = {
            "terms": {
                "field": field,
                "size": size,
                "min_doc_count": 1
            }
        }
        
        if order_by_count:
            aggregation["terms"]["order"] = {"_count": "desc"}
        
        return aggregation
    
    def _build_stats_aggregation(self, field: str) -> Dict[str, Any]:
        """
        Build a statistical aggregation for numeric fields.
        
        Args:
            field: Numeric field to calculate stats for
            
        Returns:
            Stats aggregation definition
        """
        return {
            "stats": {
                "field": field
            }
        }
    
    def build_composite_aggregation(
        self,
        sources: List[Dict[str, str]],
        size: int = 100
    ) -> Dict[str, Any]:
        """
        Build a composite aggregation for pagination through buckets.
        
        Args:
            sources: List of source field definitions
            size: Number of buckets per page
            
        Returns:
            Composite aggregation definition
        """
        return {
            "composite": {
                "size": size,
                "sources": sources
            }
        }
    
    def build_nested_aggregation(
        self,
        parent_field: str,
        child_aggregations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build nested aggregations for hierarchical data.
        
        Args:
            parent_field: Parent field to aggregate on
            child_aggregations: Child aggregations to nest
            
        Returns:
            Nested aggregation definition
        """
        return {
            "terms": {
                "field": parent_field,
                "size": 20
            },
            "aggs": child_aggregations
        }