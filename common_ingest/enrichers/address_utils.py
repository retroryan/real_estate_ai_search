"""
Address enrichment utilities.

Provides functions for normalizing and enriching address data.
"""

from typing import Dict, Optional

from ..utils.logger import setup_logger
from ..utils.config import get_settings

logger = setup_logger(__name__)


def expand_city_name(city: str) -> str:
    """
    Expand city abbreviations to full names.
    
    Args:
        city: City name or abbreviation
        
    Returns:
        Full city name
    """
    if not city:
        return city
    
    settings = get_settings()
    city_upper = city.upper().strip()
    
    # Check if it's an abbreviation
    if city_upper in settings.enrichment.city_abbreviations:
        expanded = settings.enrichment.city_abbreviations[city_upper]
        logger.debug(f"Expanded city '{city}' to '{expanded}'")
        return expanded
    
    return city.strip()


def expand_state_code(state: str) -> str:
    """
    Expand state codes to full state names.
    
    Args:
        state: State code or name
        
    Returns:
        Full state name
    """
    if not state:
        return state
    
    settings = get_settings()
    state_upper = state.upper().strip()
    
    # Check if it's a 2-letter state code
    if len(state_upper) == 2 and state_upper in settings.enrichment.state_codes:
        expanded = settings.enrichment.state_codes[state_upper]
        logger.debug(f"Expanded state '{state}' to '{expanded}'")
        return expanded
    
    return state.strip()


def normalize_address(address_dict: Dict[str, any]) -> Dict[str, any]:
    """
    Normalize address data by expanding abbreviations.
    
    Args:
        address_dict: Raw address dictionary
        
    Returns:
        Normalized address dictionary
    """
    if not address_dict:
        return address_dict
    
    # Create a copy to avoid modifying the original
    normalized = address_dict.copy()
    
    # Expand city name
    if 'city' in normalized:
        normalized['city'] = expand_city_name(normalized['city'])
    
    # Expand state code
    if 'state' in normalized:
        normalized['state'] = expand_state_code(normalized['state'])
    
    # Ensure zip_code is string
    if 'zip_code' in normalized and normalized['zip_code']:
        normalized['zip_code'] = str(normalized['zip_code'])
    elif 'zip' in normalized and normalized['zip']:
        normalized['zip_code'] = str(normalized['zip'])
        if 'zip' in normalized:
            del normalized['zip']
    
    return normalized


def validate_coordinates(lat: Optional[float], lon: Optional[float]) -> bool:
    """
    Validate that coordinates are within valid ranges.
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        True if coordinates are valid, False otherwise
    """
    if lat is None or lon is None:
        return False
    
    try:
        lat_float = float(lat)
        lon_float = float(lon)
        return -90 <= lat_float <= 90 and -180 <= lon_float <= 180
    except (TypeError, ValueError):
        return False