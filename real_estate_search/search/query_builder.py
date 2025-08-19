"""
Elasticsearch query builder with type safety.
Constructs ES queries from typed models without magic strings.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from ..indexer.enums import FieldName, PropertyType, PropertyStatus
from .models import SearchFilters, GeoSearchParams
from .enums import (
    QueryOperator,
    TextQueryType,
    RangeOperator,
    SearchField,
    GeoDistanceUnit
)


logger = structlog.get_logger(__name__)


class QueryBuilder:
    """
    Builds Elasticsearch queries from typed inputs.
    All field names and operators use enums to avoid magic strings.
    """
    
    def __init__(self):
        """Initialize the query builder."""
        self.logger = logger.bind(component="QueryBuilder")
    
    def build_search_query(
        self,
        query_text: Optional[str] = None,
        filters: Optional[SearchFilters] = None,
        geo_params: Optional[GeoSearchParams] = None
    ) -> Dict[str, Any]:
        """
        Build a complete search query from parameters.
        
        Args:
            query_text: Free text search query
            filters: Structured search filters
            geo_params: Geographic search parameters
            
        Returns:
            Elasticsearch query DSL dictionary
        """
        # Start with bool query structure
        bool_query = {
            QueryOperator.MUST: [],
            QueryOperator.FILTER: []
        }
        
        # Add text search
        if query_text:
            text_query = self._build_text_query(query_text)
            bool_query[QueryOperator.MUST].append(text_query)
        
        # Add filters
        if filters:
            filter_queries = self._build_filter_queries(filters)
            bool_query[QueryOperator.FILTER].extend(filter_queries)
        
        # Add geo filter
        if geo_params:
            geo_query = self._build_geo_query(geo_params)
            bool_query[QueryOperator.FILTER].append(geo_query)
        
        # Clean up empty lists
        bool_query = {k: v for k, v in bool_query.items() if v}
        
        # Return appropriate query
        if not bool_query:
            return {TextQueryType.MATCH_ALL: {}}
        
        return {"bool": bool_query}
    
    def _build_text_query(self, query_text: str) -> Dict[str, Any]:
        """
        Build multi-match text query.
        
        Args:
            query_text: User's search text
            
        Returns:
            Multi-match query dictionary
        """
        return {
            TextQueryType.MULTI_MATCH: {
                "query": query_text,
                "fields": [
                    SearchField.DESCRIPTION_BOOSTED,
                    SearchField.SEARCH_TAGS_BOOSTED,
                    SearchField.ADDRESS_STREET,
                    SearchField.NEIGHBORHOOD_NAME,
                    SearchField.FEATURES,
                    SearchField.AMENITIES
                ],
                "type": "best_fields",
                "fuzziness": "AUTO",
                "prefix_length": 2
            }
        }
    
    def _build_filter_queries(self, filters: SearchFilters) -> List[Dict[str, Any]]:
        """
        Build filter queries from SearchFilters model.
        
        Args:
            filters: Validated search filters
            
        Returns:
            List of filter query dictionaries
        """
        queries = []
        
        # Price range
        price_range = self._build_range_query(
            FieldName.PRICE,
            filters.min_price,
            filters.max_price
        )
        if price_range:
            queries.append(price_range)
        
        # Bedrooms range
        bedroom_range = self._build_range_query(
            FieldName.BEDROOMS,
            filters.min_bedrooms,
            filters.max_bedrooms
        )
        if bedroom_range:
            queries.append(bedroom_range)
        
        # Bathrooms minimum
        if filters.min_bathrooms is not None:
            queries.append({
                "range": {
                    FieldName.BATHROOMS: {
                        RangeOperator.GTE: filters.min_bathrooms
                    }
                }
            })
        
        # Square feet range
        sqft_range = self._build_range_query(
            FieldName.SQUARE_FEET,
            filters.min_square_feet,
            filters.max_square_feet
        )
        if sqft_range:
            queries.append(sqft_range)
        
        # Property types
        if filters.property_types:
            queries.append({
                "terms": {
                    FieldName.PROPERTY_TYPE: [pt.value for pt in filters.property_types]
                }
            })
        
        # Status
        if filters.status:
            queries.append({
                "term": {
                    FieldName.STATUS: filters.status.value
                }
            })
        
        # Cities
        if filters.cities:
            queries.append({
                "terms": {
                    FieldName.ADDRESS_CITY: filters.cities
                }
            })
        
        # States
        if filters.states:
            queries.append({
                "terms": {
                    FieldName.ADDRESS_STATE: filters.states
                }
            })
        
        # Zip codes
        if filters.zip_codes:
            queries.append({
                "terms": {
                    FieldName.ADDRESS_ZIP: filters.zip_codes
                }
            })
        
        # Neighborhoods
        if filters.neighborhood_ids:
            queries.append({
                "terms": {
                    FieldName.NEIGHBORHOOD_ID: filters.neighborhood_ids
                }
            })
        
        # Features (must have all)
        for feature in filters.features or []:
            queries.append({
                "term": {
                    FieldName.FEATURES: feature
                }
            })
        
        # Amenities (must have all)
        for amenity in filters.amenities or []:
            queries.append({
                "term": {
                    FieldName.AMENITIES: amenity
                }
            })
        
        # Parking
        if filters.must_have_parking:
            queries.append({
                "range": {
                    FieldName.PARKING_SPACES: {
                        RangeOperator.GT: 0
                    }
                }
            })
        
        if filters.min_parking_spaces is not None:
            queries.append({
                "range": {
                    FieldName.PARKING_SPACES: {
                        RangeOperator.GTE: filters.min_parking_spaces
                    }
                }
            })
        
        # Days on market
        if filters.max_days_on_market is not None:
            queries.append({
                "range": {
                    FieldName.DAYS_ON_MARKET: {
                        RangeOperator.LTE: filters.max_days_on_market
                    }
                }
            })
        
        # Listing date range
        listing_date_range = self._build_date_range_query(
            FieldName.LISTING_DATE,
            filters.listed_after,
            filters.listed_before
        )
        if listing_date_range:
            queries.append(listing_date_range)
        
        # Year built range
        year_range = self._build_range_query(
            FieldName.YEAR_BUILT,
            filters.min_year_built,
            filters.max_year_built
        )
        if year_range:
            queries.append(year_range)
        
        # HOA fee maximum
        if filters.max_hoa_fee is not None:
            queries.append({
                "range": {
                    FieldName.HOA_FEE: {
                        RangeOperator.LTE: filters.max_hoa_fee
                    }
                }
            })
        
        return queries
    
    def _build_range_query(
        self,
        field: FieldName,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Build a range query for a field.
        
        Args:
            field: Field name from enum
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)
            
        Returns:
            Range query dictionary or None if no values provided
        """
        if min_value is None and max_value is None:
            return None
        
        range_conditions = {}
        if min_value is not None:
            range_conditions[RangeOperator.GTE] = min_value
        if max_value is not None:
            range_conditions[RangeOperator.LTE] = max_value
        
        return {"range": {field: range_conditions}}
    
    def _build_date_range_query(
        self,
        field: FieldName,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Build a date range query.
        
        Args:
            field: Date field name from enum
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Date range query dictionary or None
        """
        if start_date is None and end_date is None:
            return None
        
        range_conditions = {}
        if start_date:
            range_conditions[RangeOperator.GTE] = start_date.isoformat()
        if end_date:
            range_conditions[RangeOperator.LTE] = end_date.isoformat()
        
        return {"range": {field: range_conditions}}
    
    def _build_geo_query(self, geo_params: GeoSearchParams) -> Dict[str, Any]:
        """
        Build geographic distance query.
        
        Args:
            geo_params: Geographic search parameters
            
        Returns:
            Geo distance query dictionary
        """
        geo_query = {
            "geo_distance": {
                "distance": f"{geo_params.distance}{geo_params.unit.value}",
                FieldName.ADDRESS_LOCATION: {
                    "lat": geo_params.center.lat,
                    "lon": geo_params.center.lon
                }
            }
        }
        
        return geo_query
    
    def build_more_like_this_query(
        self,
        document_id: str,
        filters: Optional[SearchFilters] = None
    ) -> Dict[str, Any]:
        """
        Build a more_like_this query for finding similar properties.
        
        Args:
            document_id: Source document ID
            filters: Optional filters to apply
            
        Returns:
            More like this query dictionary
        """
        mlt_query = {
            TextQueryType.MORE_LIKE_THIS: {
                "fields": [
                    FieldName.DESCRIPTION,
                    FieldName.FEATURES,
                    FieldName.AMENITIES,
                    FieldName.NEIGHBORHOOD_NAME
                ],
                "like": [
                    {
                        "_index": "properties_alias",
                        "_id": document_id
                    }
                ],
                "min_term_freq": 1,
                "max_query_terms": 12,
                "min_doc_freq": 1,
                "minimum_should_match": "30%"
            }
        }
        
        # Add filters if provided
        if filters:
            filter_queries = self._build_filter_queries(filters)
            if filter_queries:
                return {
                    "bool": {
                        QueryOperator.MUST: [mlt_query],
                        QueryOperator.FILTER: filter_queries
                    }
                }
        
        return mlt_query