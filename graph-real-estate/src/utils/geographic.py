"""Geographic utility functions"""
from typing import Optional, Dict, Tuple
import re


class GeographicUtils:
    """Utility functions for geographic data processing"""
    
    # State name to code mapping
    STATE_CODES: Dict[str, str] = {
        'Alabama': 'AL',
        'Alaska': 'AK',
        'Arizona': 'AZ',
        'Arkansas': 'AR',
        'California': 'CA',
        'Colorado': 'CO',
        'Connecticut': 'CT',
        'Delaware': 'DE',
        'Florida': 'FL',
        'Georgia': 'GA',
        'Hawaii': 'HI',
        'Idaho': 'ID',
        'Illinois': 'IL',
        'Indiana': 'IN',
        'Iowa': 'IA',
        'Kansas': 'KS',
        'Kentucky': 'KY',
        'Louisiana': 'LA',
        'Maine': 'ME',
        'Maryland': 'MD',
        'Massachusetts': 'MA',
        'Michigan': 'MI',
        'Minnesota': 'MN',
        'Mississippi': 'MS',
        'Missouri': 'MO',
        'Montana': 'MT',
        'Nebraska': 'NE',
        'Nevada': 'NV',
        'New Hampshire': 'NH',
        'New Jersey': 'NJ',
        'New Mexico': 'NM',
        'New York': 'NY',
        'North Carolina': 'NC',
        'North Dakota': 'ND',
        'Ohio': 'OH',
        'Oklahoma': 'OK',
        'Oregon': 'OR',
        'Pennsylvania': 'PA',
        'Rhode Island': 'RI',
        'South Carolina': 'SC',
        'South Dakota': 'SD',
        'Tennessee': 'TN',
        'Texas': 'TX',
        'Utah': 'UT',
        'Vermont': 'VT',
        'Virginia': 'VA',
        'Washington': 'WA',
        'West Virginia': 'WV',
        'Wisconsin': 'WI',
        'Wyoming': 'WY'
    }
    
    @classmethod
    def get_state_code(cls, state_name: Optional[str]) -> Optional[str]:
        """Convert state name to two-letter code"""
        if not state_name:
            return None
        
        # Check if already a code
        if len(state_name) == 2 and state_name.upper() in cls.STATE_CODES.values():
            return state_name.upper()
        
        # Look up the code
        return cls.STATE_CODES.get(state_name, None)
    
    @classmethod
    def normalize_county_id(cls, county_name: str, state_code: str) -> str:
        """Create normalized county ID from county name and state code"""
        if not county_name or not state_code:
            raise ValueError("County name and state code are required")
        
        # Remove 'County' suffix for ID
        county_base = county_name.replace(' County', '').replace(' county', '')
        
        # Create ID: lowercase, replace spaces with underscores
        county_id = f"{county_base}_{state_code}".lower().replace(' ', '_')
        
        # Remove any special characters
        county_id = re.sub(r'[^a-z0-9_]', '', county_id)
        
        return county_id
    
    @classmethod
    def normalize_city_id(cls, city_name: str, state_code: str) -> str:
        """Create normalized city ID from city name and state code"""
        if not city_name or not state_code:
            raise ValueError("City name and state code are required")
        
        # Create ID: lowercase, replace spaces with underscores
        city_id = f"{city_name}_{state_code}".lower().replace(' ', '_')
        
        # Remove any special characters except underscores
        city_id = re.sub(r'[^a-z0-9_]', '', city_id)
        
        return city_id
    
    @classmethod
    def parse_county_variations(cls, county_name: str) -> Tuple[str, bool]:
        """
        Parse county name and detect if it has 'County' suffix
        Returns: (base_name, has_suffix)
        """
        if not county_name:
            return ("", False)
        
        has_suffix = bool(re.search(r'\bCounty\b', county_name, re.IGNORECASE))
        base_name = re.sub(r'\s+County\s*$', '', county_name, flags=re.IGNORECASE).strip()
        
        return (base_name, has_suffix)
    
    @classmethod
    def standardize_county_name(cls, county_name: str) -> str:
        """
        Standardize county name to official format
        Always returns with 'County' suffix for consistency
        """
        base_name, has_suffix = cls.parse_county_variations(county_name)
        
        if not base_name:
            return county_name
        
        # Special cases where 'County' is part of the name
        special_cases = {
            'san francisco': 'San Francisco County',  # City and County of San Francisco
        }
        
        base_lower = base_name.lower()
        if base_lower in special_cases:
            return special_cases[base_lower]
        
        # Standard format: "Name County"
        if not has_suffix:
            return f"{base_name} County"
        
        return county_name
    
    @classmethod
    def validate_coordinates(cls, lat: Optional[float], lng: Optional[float]) -> bool:
        """Validate geographic coordinates"""
        if lat is None or lng is None:
            return False
        
        return -90 <= lat <= 90 and -180 <= lng <= 180