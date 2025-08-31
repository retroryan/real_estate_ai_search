"""State standardization utilities for Silver layer transformations."""

from typing import Dict


class StateStandardizer:
    """Utility class for standardizing state names to abbreviations."""
    
    # State name to abbreviation mapping
    STATE_MAPPING: Dict[str, str] = {
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
        'Wyoming': 'WY',
        'District of Columbia': 'DC',
        'Washington D.C.': 'DC',
        # Common variations
        'D.C.': 'DC',
        'Washington DC': 'DC',
    }
    
    @classmethod
    def get_sql_case_statement(cls, field_name: str = 'best_state', alias: str = 'state') -> str:
        """Generate SQL CASE statement for state transformation.
        
        Args:
            field_name: The source field name containing full state names
            alias: The output field name for abbreviated states
            
        Returns:
            SQL CASE statement string
        """
        case_parts = [f"CASE {field_name}"]
        
        for full_name, abbr in cls.STATE_MAPPING.items():
            case_parts.append(f"    WHEN '{full_name}' THEN '{abbr}'")
        
        # Fallback for unknown values - take first 2 characters uppercase
        case_parts.append(f"    ELSE UPPER(LEFT({field_name}, 2))")
        case_parts.append(f"END as {alias}")
        
        return '\n'.join(case_parts)
    
    @classmethod
    def standardize_state(cls, state_name: str) -> str:
        """Convert state name to abbreviation.
        
        Args:
            state_name: Full state name or abbreviation
            
        Returns:
            Two-letter state abbreviation
        """
        if not state_name:
            return ''
        
        # Already an abbreviation
        if len(state_name) == 2:
            return state_name.upper()
        
        # Look up in mapping
        standardized = cls.STATE_MAPPING.get(state_name)
        if standardized:
            return standardized
        
        # Fallback - take first 2 characters
        return state_name[:2].upper() if len(state_name) >= 2 else state_name.upper()