"""
Property data loader implementation with integrated enrichment.

Loads property data from JSON files and returns enriched Pydantic models.
"""

import json
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base import BaseLoader, log_operation
from property_finder_models import (
    EnrichedProperty,
    EnrichedAddress,
    PropertyType,
    PropertyStatus,
    GeoLocation
)
from ..enrichers.address_utils import normalize_address, validate_coordinates
from ..enrichers.feature_utils import normalize_feature_list
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class PropertyLoader(BaseLoader[EnrichedProperty]):
    """
    Loader for property data from JSON files.
    
    Loads properties from properties_sf.json and properties_pc.json files,
    applies enrichment, and returns EnrichedProperty Pydantic models.
    """
    
    def __init__(self, data_path: Path):
        """
        Initialize property loader with data path.
        
        Args:
            data_path: Path to directory containing property JSON files
        """
        super().__init__(data_path)
        
        # Define expected property files
        self.sf_properties_file = data_path / "properties_sf.json"
        self.pc_properties_file = data_path / "properties_pc.json"
        
        # Validate that at least one property file exists
        if not self.sf_properties_file.exists() and not self.pc_properties_file.exists():
            logger.warning(f"No property files found in {data_path}")
    
    @log_operation("load_all_properties")
    def load_all(self) -> List[EnrichedProperty]:
        """
        Load all properties from all available JSON files.
        
        Returns:
            List of EnrichedProperty models
        """
        all_properties = []
        
        # Load San Francisco properties
        if self.sf_properties_file.exists():
            sf_properties = self._load_properties_from_file(
                self.sf_properties_file, 
                default_city="San Francisco",
                default_state="CA"
            )
            all_properties.extend(sf_properties)
            logger.info(f"Loaded {len(sf_properties)} properties from San Francisco")
        
        # Load Park City properties
        if self.pc_properties_file.exists():
            pc_properties = self._load_properties_from_file(
                self.pc_properties_file,
                default_city="Park City",
                default_state="UT"
            )
            all_properties.extend(pc_properties)
            logger.info(f"Loaded {len(pc_properties)} properties from Park City")
        
        return all_properties
    
    @log_operation("load_properties_by_city")
    def load_by_filter(self, city: Optional[str] = None, **filters) -> List[EnrichedProperty]:
        """
        Load properties filtered by city.
        
        Args:
            city: City name to filter by ("San Francisco" or "Park City")
            **filters: Additional filters (for future extension)
            
        Returns:
            List of EnrichedProperty models matching the filter
        """
        if city is None:
            # No filter, load all
            return self.load_all()
        
        properties = []
        
        # Normalize city name for matching
        city_lower = city.lower()
        
        # Load all properties first, then filter by city
        all_properties = self.load_all()
        
        # Filter properties by city (case-insensitive)
        filtered_properties = [
            prop for prop in all_properties
            if prop.address.city.lower() == city_lower
        ]
        
        logger.info(f"Filtered {len(filtered_properties)} properties for city '{city}' from total {len(all_properties)}")
        
        return filtered_properties
    
    def _load_properties_from_file(
        self, 
        file_path: Path, 
        default_city: str,
        default_state: str
    ) -> List[EnrichedProperty]:
        """
        Load properties from a specific JSON file and convert to EnrichedProperty models.
        
        Args:
            file_path: Path to the JSON file
            default_city: Default city name if not present in data
            default_state: Default state code if not present in data
            
        Returns:
            List of EnrichedProperty models
        """
        enriched_properties = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_properties = json.load(f)
            
            # Convert each raw property to EnrichedProperty
            for raw_prop in raw_properties:
                try:
                    enriched_prop = self._convert_to_enriched_property(
                        raw_prop, 
                        default_city, 
                        default_state
                    )
                    enriched_properties.append(enriched_prop)
                except Exception as e:
                    logger.warning(f"Failed to convert property {raw_prop.get('listing_id', 'unknown')}: {e}")
            
            return enriched_properties
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {file_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to load properties from {file_path}: {e}")
            return []
    
    def _convert_to_enriched_property(
        self, 
        raw_data: Dict[str, Any], 
        default_city: str,
        default_state: str
    ) -> EnrichedProperty:
        """
        Convert raw property data to EnrichedProperty model with enrichment.
        
        Args:
            raw_data: Raw property dictionary
            default_city: Default city if not present
            default_state: Default state if not present
            
        Returns:
            EnrichedProperty model
        """
        # Extract and normalize address
        address_data = raw_data.get('address', {})
        
        # Add defaults if missing
        if not address_data.get('city'):
            address_data['city'] = default_city
        if not address_data.get('state'):
            address_data['state'] = default_state
        
        # Apply address enrichment
        address_data = normalize_address(address_data)
        
        # Extract coordinates
        coordinates = None
        coord_data = raw_data.get('coordinates') or address_data.get('coordinates')
        if coord_data:
            lat = coord_data.get('latitude') or coord_data.get('lat')
            lon = coord_data.get('longitude') or coord_data.get('lon') or coord_data.get('lng')
            if validate_coordinates(lat, lon):
                coordinates = GeoLocation(lat=float(lat), lon=float(lon))
        
        # Create EnrichedAddress
        enriched_address = EnrichedAddress(
            street=address_data.get('street', 'Unknown Street'),
            city=address_data.get('city', default_city),
            state=address_data.get('state', default_state),
            zip_code=address_data.get('zip_code', address_data.get('zip', '00000')),
            coordinates=coordinates
        )
        
        # Extract property details
        property_details = raw_data.get('property_details', {})
        
        # Determine property type
        prop_type_str = (
            property_details.get('property_type') or 
            raw_data.get('property_type', 'other')
        ).lower().replace('-', '_')
        
        # Map common aliases to enum values
        type_mapping = {
            'single_family': 'house',
            'single_family_home': 'house',
            'sfh': 'house',
            'home': 'house',
            'condominium': 'condo',
            'apt': 'apartment',
            'town_house': 'townhouse',
            'town_home': 'townhouse',
        }
        
        # Apply mapping if exists
        prop_type_str = type_mapping.get(prop_type_str, prop_type_str)
        
        try:
            property_type = PropertyType(prop_type_str)
        except ValueError:
            property_type = PropertyType.OTHER
        
        # Determine status
        status_str = raw_data.get('status', 'active').lower()
        try:
            status = PropertyStatus(status_str)
        except ValueError:
            status = PropertyStatus.ACTIVE
        
        # Extract and normalize features
        features = normalize_feature_list(raw_data.get('features', []))
        amenities = normalize_feature_list(raw_data.get('amenities', []))
        
        # Extract price
        price = (
            raw_data.get('listing_price') or
            raw_data.get('price') or
            property_details.get('price', 100000)
        )
        
        # Create EnrichedProperty
        enriched_property = EnrichedProperty(
            listing_id=raw_data.get('listing_id', f"prop_{id(raw_data)}"),
            property_type=property_type,
            price=Decimal(str(price)),
            bedrooms=int(property_details.get('bedrooms') or raw_data.get('bedrooms', 0)),
            bathrooms=float(property_details.get('bathrooms') or raw_data.get('bathrooms', 0)),
            square_feet=property_details.get('square_feet') or raw_data.get('square_feet'),
            year_built=property_details.get('year_built') or raw_data.get('year_built'),
            lot_size=property_details.get('lot_size') or raw_data.get('lot_size'),
            address=enriched_address,
            features=features,
            amenities=amenities,
            description=raw_data.get('description'),
            status=status,
            images=raw_data.get('images', []),
            virtual_tour_url=raw_data.get('virtual_tour_url'),
            mls_number=raw_data.get('mls_number'),
            hoa_fee=Decimal(str(raw_data.get('hoa_fee'))) if raw_data.get('hoa_fee') else None
        )
        
        return enriched_property
    
    def load_properties_by_city(self, city: str) -> List[EnrichedProperty]:
        """
        Convenience method to load properties by city.
        
        Args:
            city: City name
            
        Returns:
            List of EnrichedProperty models
        """
        return self.load_by_filter(city=city)