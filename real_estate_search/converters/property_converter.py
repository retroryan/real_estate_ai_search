"""
Property converter for transforming Elasticsearch data to Pydantic models.

This module provides clean conversion functions to transform raw Elasticsearch
property data into properly typed PropertyListing Pydantic models.
"""

from typing import Dict, Any, List, Optional
from ..models.property import PropertyListing, Parking
from ..models.address import Address
from ..models.enums import PropertyType, PropertyStatus, ParkingType


class PropertyConverter:
    """Converter for transforming Elasticsearch property data to Pydantic models."""
    
    @staticmethod
    def from_elasticsearch(data: Dict[str, Any]) -> PropertyListing:
        """
        Convert Elasticsearch document to PropertyListing model.
        
        Args:
            data: Raw property data from Elasticsearch
            
        Returns:
            PropertyListing: Properly typed Pydantic model
        """
        # Create a copy to avoid modifying the original
        property_data = data.copy()
        
        # Convert nested objects
        property_data = PropertyConverter._convert_nested_objects(property_data)
        
        # Convert enums
        property_data = PropertyConverter._convert_enums(property_data)
        
        # Handle search metadata
        property_data = PropertyConverter._add_search_metadata(property_data)
        
        # Create and return the PropertyListing
        return PropertyListing(**property_data)
    
    @staticmethod
    def from_elasticsearch_batch(data_list: List[Dict[str, Any]]) -> List[PropertyListing]:
        """
        Convert a list of Elasticsearch documents to PropertyListing models.
        
        Args:
            data_list: List of raw property data from Elasticsearch
            
        Returns:
            List[PropertyListing]: List of properly typed Pydantic models
        """
        return [PropertyConverter.from_elasticsearch(data) for data in data_list]
    
    @staticmethod
    def from_elasticsearch_response(response: Dict[str, Any]) -> List[PropertyListing]:
        """
        Extract and convert properties from full Elasticsearch response.
        
        Args:
            response: Full Elasticsearch response with hits
            
        Returns:
            List[PropertyListing]: List of property models
        """
        properties = []
        
        if 'hits' in response and 'hits' in response['hits']:
            for hit in response['hits']['hits']:
                source = hit.get('_source', {})
                
                # Add Elasticsearch metadata
                source['_id'] = hit.get('_id')
                source['_score'] = hit.get('_score')
                
                # Add highlights if present
                if 'highlight' in hit:
                    source['highlights'] = hit['highlight']
                
                # Add sort values if present (for geo queries)
                if 'sort' in hit:
                    # Often the first sort value is distance for geo queries
                    source['_sort'] = hit['sort']
                    if len(hit['sort']) > 0 and isinstance(hit['sort'][0], (int, float)):
                        source['distance_km'] = hit['sort'][0]
                
                # Convert to PropertyListing
                try:
                    property_model = PropertyConverter.from_elasticsearch(source)
                    properties.append(property_model)
                except Exception as e:
                    # Log error but continue processing other results
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to convert property: {e}")
                    continue
        
        return properties
    
    @staticmethod
    def _convert_nested_objects(data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert nested objects to their Pydantic models."""
        # Convert address
        if 'address' in data and isinstance(data['address'], dict):
            data['address'] = Address(**data['address'])
        elif 'address' not in data:
            # Provide default address if missing
            data['address'] = Address()
        
        # Convert parking
        if 'parking' in data and isinstance(data['parking'], dict):
            parking_data = data['parking'].copy()
            # Handle parking type enum
            if 'type' in parking_data and isinstance(parking_data['type'], str):
                try:
                    parking_data['type'] = ParkingType(parking_data['type'].lower())
                except (ValueError, KeyError):
                    parking_data['type'] = ParkingType.NONE
            data['parking'] = Parking(**parking_data)
        elif 'parking' not in data:
            # Provide default parking if missing
            data['parking'] = Parking()
        
        return data
    
    @staticmethod
    def _convert_enums(data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert enum fields to their proper types."""
        # Convert property_type
        if 'property_type' in data:
            data['property_type'] = PropertyConverter._normalize_property_type(
                data['property_type']
            )
        
        # Convert status
        if 'status' in data:
            data['status'] = PropertyConverter._normalize_status(data['status'])
        else:
            data['status'] = PropertyStatus.ACTIVE
        
        return data
    
    @staticmethod
    def _add_search_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
        """Add search-related metadata fields."""
        # These fields might come from Elasticsearch but aren't in the source document
        # We preserve them if they exist
        metadata_fields = ['_id', '_score', '_sort', 'distance_km', 'highlights']
        
        for field in metadata_fields:
            if field in data and field not in ['highlights']:
                # Most metadata fields map directly
                pass
            elif field == 'highlights' and field in data:
                # Highlights need special handling - map to search_highlights
                data['search_highlights'] = data.pop('highlights')
        
        return data
    
    @staticmethod
    def _normalize_property_type(type_value: Any) -> PropertyType:
        """
        Normalize property type string to PropertyType enum.
        
        Args:
            type_value: Raw property type value
            
        Returns:
            PropertyType: Typed enum value
        """
        if isinstance(type_value, PropertyType):
            return type_value
        
        if not isinstance(type_value, str):
            return PropertyType.OTHER
        
        # Normalize string: lowercase, replace separators with underscore
        type_str = type_value.lower().replace('-', '_').replace(' ', '_')
        
        # Comprehensive mapping of variations
        type_mapping = {
            'single_family': PropertyType.SINGLE_FAMILY,
            'singlefamily': PropertyType.SINGLE_FAMILY,
            'single': PropertyType.SINGLE_FAMILY,
            'condo': PropertyType.CONDO,
            'condominium': PropertyType.CONDO,
            'townhome': PropertyType.TOWNHOUSE,  # Map to TOWNHOUSE
            'townhouse': PropertyType.TOWNHOUSE,
            'town_home': PropertyType.TOWNHOUSE,
            'town_house': PropertyType.TOWNHOUSE,
            'multi_family': PropertyType.MULTI_FAMILY,
            'multifamily': PropertyType.MULTI_FAMILY,
            'multi': PropertyType.MULTI_FAMILY,
            'apartment': PropertyType.APARTMENT,
            'apt': PropertyType.APARTMENT,
            'land': PropertyType.LAND,
            'lot': PropertyType.LAND,
            'other': PropertyType.OTHER,
        }
        
        return type_mapping.get(type_str, PropertyType.OTHER)
    
    @staticmethod
    def _normalize_status(status_value: Any) -> PropertyStatus:
        """
        Normalize status string to PropertyStatus enum.
        
        Args:
            status_value: Raw status value
            
        Returns:
            PropertyStatus: Typed enum value
        """
        if isinstance(status_value, PropertyStatus):
            return status_value
        
        if not isinstance(status_value, str):
            return PropertyStatus.ACTIVE
        
        status_str = status_value.lower().replace('-', '_').replace(' ', '_')
        
        # Comprehensive mapping of variations
        status_mapping = {
            'active': PropertyStatus.ACTIVE,
            'for_sale': PropertyStatus.ACTIVE,
            'available': PropertyStatus.ACTIVE,
            'pending': PropertyStatus.PENDING,
            'under_contract': PropertyStatus.PENDING,
            'sold': PropertyStatus.SOLD,
            'closed': PropertyStatus.SOLD,
            'off_market': PropertyStatus.OFF_MARKET,
            'offmarket': PropertyStatus.OFF_MARKET,
            'withdrawn': PropertyStatus.OFF_MARKET,
            'expired': PropertyStatus.OFF_MARKET,
        }
        
        return status_mapping.get(status_str, PropertyStatus.ACTIVE)