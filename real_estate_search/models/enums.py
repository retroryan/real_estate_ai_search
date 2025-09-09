"""
Enumerations for property models.

Consolidated enums used across all property-related models.
"""

from enum import Enum


class PropertyType(str, Enum):
    """Types of real estate properties."""
    SINGLE_FAMILY = "single-family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    MULTI_FAMILY = "multi-family"
    APARTMENT = "apartment"
    LAND = "land"
    OTHER = "other"
    
    @classmethod
    def _missing_(cls, value):
        """Handle case variations and unknown values."""
        if value:
            # Try case-insensitive match with hyphen variations
            value_lower = str(value).lower().replace("_", "-").replace(" ", "-")
            for member in cls:
                if member.value.lower() == value_lower:
                    return member
            # Handle common aliases
            aliases = {
                "single family": cls.SINGLE_FAMILY,
                "single_family": cls.SINGLE_FAMILY,
                "town-house": cls.TOWNHOUSE,
                "town_house": cls.TOWNHOUSE,
                "townhome": cls.TOWNHOUSE,
                "multi family": cls.MULTI_FAMILY,
                "multi_family": cls.MULTI_FAMILY,
                "multifamily": cls.MULTI_FAMILY,
            }
            if value_lower in aliases:
                return aliases[value_lower]
        # Default to OTHER for unknown types
        return cls.OTHER


class PropertyStatus(str, Enum):
    """Property listing status."""
    ACTIVE = "active"
    PENDING = "pending"
    SOLD = "sold"
    OFF_MARKET = "off_market"
    COMING_SOON = "coming_soon"


class ParkingType(str, Enum):
    """Types of parking."""
    GARAGE = "garage"
    CARPORT = "carport"
    DRIVEWAY = "driveway"
    STREET = "street"
    COVERED = "covered"
    UNCOVERED = "uncovered"
    NONE = "none"