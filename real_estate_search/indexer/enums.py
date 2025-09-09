"""
Enums for type safety and avoiding magic strings.
All constants used in the system should be defined here.
"""

from enum import Enum

# For Python 3.10 compatibility
try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum):
        """Backport of StrEnum for Python < 3.11"""
        pass


class PropertyType(StrEnum):
    """Property type enumeration."""
    SINGLE_FAMILY = "single_family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    MULTI_FAMILY = "multi_family"
    LAND = "land"
    APARTMENT = "apartment"
    MOBILE_HOME = "mobile_home"
    COOP = "coop"
    OTHER = "other"


class PropertyStatus(StrEnum):
    """Property listing status."""
    ACTIVE = "active"
    PENDING = "pending"
    SOLD = "sold"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    HOLD = "hold"


class ParkingType(StrEnum):
    """Parking type options."""
    GARAGE = "garage"
    DRIVEWAY = "driveway"
    STREET = "street"
    COVERED = "covered"
    UNCOVERED = "uncovered"
    VALET = "valet"
    NONE = "none"


class SortOrder(StrEnum):
    """Search result sort orders."""
    RELEVANCE = "relevance"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    DATE_DESC = "date_desc"
    SIZE_DESC = "size_desc"
    BEDROOMS_DESC = "bedrooms_desc"


class FieldName(StrEnum):
    """Elasticsearch field names - Single source of truth for all field references."""
    # Core fields
    LISTING_ID = "listing_id"
    PROPERTY_TYPE = "property_type"
    PRICE = "price"
    BEDROOMS = "bedrooms"
    BATHROOMS = "bathrooms"
    SQUARE_FEET = "square_feet"
    YEAR_BUILT = "year_built"
    LOT_SIZE = "lot_size"
    
    # Address fields
    ADDRESS = "address"
    ADDRESS_STREET = "address.street"
    ADDRESS_CITY = "address.city"
    ADDRESS_STATE = "address.state"
    ADDRESS_ZIP = "address.zip_code"
    ADDRESS_LOCATION = "address.location"
    
    # Neighborhood fields
    NEIGHBORHOOD = "neighborhood"
    NEIGHBORHOOD_ID = "neighborhood.neighborhood_id"
    NEIGHBORHOOD_NAME = "neighborhood.name"
    NEIGHBORHOOD_WALKABILITY = "neighborhood.walkability_score"
    NEIGHBORHOOD_SCHOOL_RATING = "neighborhood.school_rating"
    
    # Description and features
    DESCRIPTION = "description"
    FEATURES = "features"
    
    # Status and dates
    STATUS = "status"
    LISTING_DATE = "listing_date"
    LAST_UPDATED = "last_updated"
    DAYS_ON_MARKET = "days_on_market"
    
    # Financial
    PRICE_PER_SQFT = "price_per_sqft"
    HOA_FEE = "hoa_fee"
    TAX_ASSESSED_VALUE = "tax_assessed_value"
    ANNUAL_TAX = "annual_tax"
    
    # Parking
    PARKING_SPACES = "parking.spaces"
    PARKING_TYPE = "parking.type"
    
    # Media
    VIRTUAL_TOUR_URL = "virtual_tour_url"
    IMAGES = "images"
    
    # Other
    MLS_NUMBER = "mls_number"
    SEARCH_TAGS = "search_tags"


class IndexName(StrEnum):
    """Index naming constants."""
    PROPERTIES = "properties"
    PROPERTIES_ALIAS = "properties_alias"
    TEST_PROPERTIES = "test_properties"
    TEST_PROPERTIES_ALIAS = "test_properties_alias"
    NEIGHBORHOODS = "neighborhoods"
    TEST_NEIGHBORHOODS = "test_neighborhoods"
    WIKIPEDIA = "wikipedia"
    TEST_WIKIPEDIA = "test_wikipedia"
    PROPERTY_RELATIONSHIPS = "property_relationships"
    TEST_PROPERTY_RELATIONSHIPS = "test_property_relationships"


class AggregationType(StrEnum):
    """Aggregation type names for faceted search."""
    PRICE_RANGES = "price_ranges"
    PROPERTY_TYPES = "property_types"
    CITIES = "cities"
    NEIGHBORHOODS = "neighborhoods"
    BEDROOM_COUNTS = "bedroom_counts"
    BATHROOM_COUNTS = "bathroom_counts"
    FEATURES = "features"
    PRICE_STATS = "price_stats"
    SQFT_STATS = "sqft_stats"
    STATUS_DISTRIBUTION = "status_distribution"


class AnalyzerName(StrEnum):
    """Custom analyzer names."""
    PROPERTY_ANALYZER = "property_analyzer"
    ADDRESS_ANALYZER = "address_analyzer"
    FEATURE_ANALYZER = "feature_analyzer"


class ErrorCode(StrEnum):
    """Error codes for exception handling."""
    INDEX_NOT_FOUND = "INDEX_NOT_FOUND"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    BULK_INDEX_ERROR = "BULK_INDEX_ERROR"
    QUERY_ERROR = "QUERY_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"