"""
Unified property listing model.

This is the single, authoritative PropertyListing model that serves as the 
sole source of truth for property data throughout the application.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator, computed_field, field_serializer

from .address import Address
from .enums import PropertyType, PropertyStatus, ParkingType

logger = logging.getLogger(__name__)


class Parking(BaseModel):
    """Parking information for a property."""
    spaces: int = Field(default=0, ge=0, description="Number of parking spaces")
    type: ParkingType = Field(default=ParkingType.NONE, description="Type of parking")
    
    model_config = ConfigDict(extra="ignore", use_enum_values=True)


class PropertyListing(BaseModel):
    """
    Unified property listing model.
    
    This model consolidates all property-related fields from various models
    throughout the codebase into a single, comprehensive structure.
    """
    
    # === Core Identification ===
    listing_id: str = Field(..., description="Unique listing identifier")
    neighborhood_id: Optional[str] = Field(default="", description="Associated neighborhood ID")
    
    # === Property Classification ===
    property_type: PropertyType = Field(..., description="Type of property")
    status: PropertyStatus = Field(default=PropertyStatus.ACTIVE, description="Listing status")
    
    # === Location ===
    address: Address = Field(..., description="Property address")
    school_district: Optional[str] = Field(default=None, description="School district")
    
    # === Pricing ===
    price: float = Field(..., ge=0, description="Listing price")
    price_per_sqft: Optional[float] = Field(default=0.0, ge=0, description="Price per square foot")
    hoa_fee: Optional[float] = Field(default=None, ge=0, description="HOA monthly fee")
    tax_annual: Optional[float] = Field(default=None, ge=0, description="Annual property tax")
    last_sold_price: Optional[float] = Field(default=None, ge=0, description="Last sale price")
    
    # === Physical Attributes ===
    bedrooms: int = Field(default=0, ge=0, le=50, description="Number of bedrooms")
    bathrooms: float = Field(default=0.0, ge=0, le=50, description="Number of bathrooms")
    square_feet: int = Field(default=0, ge=0, le=100000, description="Square footage")
    lot_size: int = Field(default=0, ge=0, description="Lot size in square feet")
    year_built: Optional[int] = Field(default=0, ge=1600, le=2100, description="Year built")
    stories: Optional[int] = Field(default=None, ge=1, le=10, description="Number of stories")
    
    # === Parking ===
    parking: Optional[Parking] = Field(default_factory=Parking, description="Parking information")
    
    # === Descriptions and Features ===
    title: Optional[str] = Field(default=None, max_length=200, description="Listing title")
    description: str = Field(default="", description="Full property description")
    features: List[str] = Field(default_factory=list, description="Property features/amenities")
    highlights: List[str] = Field(default_factory=list, description="Key highlights")
    
    # === Dates and Timeline ===
    listing_date: Optional[str] = Field(default="", description="Date listed (string for ES compatibility)")
    list_date: Optional[datetime] = Field(default=None, description="Date listed (datetime)")
    last_sold_date: Optional[datetime] = Field(default=None, description="Last sale date")
    days_on_market: int = Field(default=0, ge=0, description="Days on market")
    
    # === Media ===
    images: List[str] = Field(default_factory=list, description="Image URLs")
    photo_count: Optional[int] = Field(default=None, ge=0, description="Number of photos")
    virtual_tour_url: Optional[str] = Field(default="", description="Virtual tour URL")
    
    # === Embeddings and Search Metadata ===
    embedding: List[float] = Field(default_factory=list, description="Vector embedding")
    embedding_model: str = Field(default="", description="Embedding model used")
    embedding_dimension: int = Field(default=0, description="Embedding dimension")
    embedded_at: Optional[datetime] = Field(default=None, description="When embedded")
    
    # === Search Result Metadata ===
    score: Optional[float] = Field(default=None, alias="_score", description="Search relevance score")
    distance_km: Optional[float] = Field(default=None, description="Distance from search center")
    search_highlights: Optional[Dict[str, List[str]]] = Field(
        default=None, 
        alias="highlights",
        description="Search result highlights"
    )
    
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        extra="allow",  # Allow extra fields from Elasticsearch
    )
    
    @field_serializer('list_date', 'last_sold_date', 'embedded_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime fields to ISO format."""
        return dt.isoformat() if dt else None
    
    # === Validators ===
    
    @model_validator(mode='before')
    @classmethod
    def calculate_price_per_sqft_if_missing(cls, data):
        """Calculate price per sqft if not provided."""
        if isinstance(data, dict):
            price_per_sqft = data.get('price_per_sqft')
            if price_per_sqft is None or price_per_sqft == 0:
                price = data.get('price', 0)
                sqft = data.get('square_feet', 0)
                if price > 0 and sqft > 0:
                    data['price_per_sqft'] = price / sqft
                else:
                    data['price_per_sqft'] = 0.0
        return data
    
    @field_validator('listing_date', mode='before')
    @classmethod
    def convert_listing_date(cls, v):
        """Ensure listing_date is a string for ES compatibility."""
        # Try to call isoformat if it exists (datetime object)
        try:
            return v.isoformat()
        except (AttributeError, TypeError):
            # Not a datetime, return as string
            return v or ""
    
    # === Display Properties ===
    
    @computed_field
    @property
    def display_price(self) -> str:
        """Format price for display with appropriate scale."""
        if self.price >= 1000000:
            return f"${self.price/1000000:.1f}M"
        elif self.price >= 1000:
            return f"${self.price/1000:.0f}K"
        else:
            return f"${self.price:,.0f}"
    
    @computed_field
    @property
    def display_property_type(self) -> str:
        """Format property type for display."""
        # Map internal values to display values
        display_map = {
            "single-family": "Single Family",
            "condo": "Condo",
            "townhouse": "Townhouse",
            "multi-family": "Multi-Family",
            "apartment": "Apartment",
            "land": "Land",
            "other": "Other"
        }
        return display_map.get(self.property_type, self.property_type.replace("-", " ").title())
    
    @computed_field
    @property
    def summary(self) -> str:
        """Generate property summary line."""
        parts = []
        
        # Bedrooms/Bathrooms
        if self.bedrooms or self.bathrooms:
            bed_bath = []
            if self.bedrooms:
                bed_bath.append(f"{self.bedrooms}bd")
            if self.bathrooms:
                bath_int = int(self.bathrooms)
                if self.bathrooms % 1 == 0.5:
                    bed_bath.append(f"{bath_int}.5ba")
                else:
                    bed_bath.append(f"{bath_int}ba")
            parts.append("/".join(bed_bath))
        
        # Square feet
        if self.square_feet:
            parts.append(f"{self.square_feet:,} sqft")
        
        # Property type
        parts.append(self.display_property_type)
        
        return " | ".join(parts) if parts else "Property details not available"
    
    @computed_field
    @property
    def has_score(self) -> bool:
        """Check if this property has a relevance score from search."""
        return self.score is not None and self.score > 0
    
    @computed_field
    @property
    def rooms_total(self) -> Optional[int]:
        """Calculate total rooms."""
        if self.bedrooms is not None and self.bathrooms is not None:
            return self.bedrooms + int(self.bathrooms)
        return None
    
    @computed_field
    @property
    def parking_display(self) -> str:
        """Format parking information for display."""
        if self.parking and self.parking.spaces > 0:
            return f"{self.parking.spaces} {self.parking.type} space{'s' if self.parking.spaces > 1 else ''}"
        return "No parking"
    
    @computed_field
    @property
    def listing_date_display(self) -> str:
        """Format listing date for display."""
        if self.list_date:
            return self.list_date.strftime("%B %d, %Y")
        elif self.listing_date:
            try:
                dt = datetime.fromisoformat(self.listing_date.replace('Z', '+00:00'))
                return dt.strftime("%B %d, %Y")
            except (ValueError, AttributeError):
                return self.listing_date
        return "N/A"
    
    # === Elasticsearch Compatibility Methods ===
    
    def to_elasticsearch(self) -> Dict[str, Any]:
        """Convert to Elasticsearch document format."""
        doc = self.model_dump(
            exclude={'score', 'distance_km', 'search_highlights', 'list_date', 'last_sold_date'},
            exclude_none=True,
            by_alias=False
        )
        
        # Ensure dates are strings for ES
        if self.list_date:
            doc['listing_date'] = self.list_date.isoformat()
        if self.last_sold_date:
            doc['last_sold_date'] = self.last_sold_date.isoformat()
        if self.embedded_at:
            doc['embedded_at'] = self.embedded_at.isoformat()
            
        return doc
    
    @classmethod
    def from_elasticsearch(cls, data: Dict[str, Any]) -> "PropertyListing":
        """
        Create PropertyListing from single Elasticsearch document.
        
        This method handles ONLY single documents, not full ES responses.
        For full responses, use from_elasticsearch_response().
        
        Args:
            data: Single document dict from Elasticsearch _source or hit
            
        Returns:
            PropertyListing instance
        """
        # Single document - normalize and return PropertyListing
        source = data.copy()
        
        # Apply all transformations
        source = cls._convert_nested_objects(source)
        source = cls._normalize_enums(source)
        source = cls._handle_search_metadata(source)
        source = cls._convert_dates(source)
        
        return cls(**source)
    
    @classmethod
    def from_elasticsearch_response(cls, response: Dict[str, Any]) -> List["PropertyListing"]:
        """
        Extract and convert properties from full Elasticsearch response.
        
        Args:
            response: Full Elasticsearch response with hits
            
        Returns:
            List of PropertyListing instances
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
                    source['_sort'] = hit['sort']
                    if len(hit['sort']) > 0:
                        try:
                            # Try to use as numeric value for distance
                            source['distance_km'] = float(hit['sort'][0])
                        except (TypeError, ValueError):
                            pass
                
                # Convert to PropertyListing
                try:
                    property_model = cls.from_elasticsearch(source)
                    properties.append(property_model)
                except Exception as e:
                    # Log error but continue processing other results
                    logger.warning(f"Failed to convert property: {e}")
                    continue
        
        return properties
    
    @staticmethod
    def _convert_nested_objects(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert nested objects from Elasticsearch to their Pydantic models.
        
        Elasticsearch always returns dicts for nested objects, not Pydantic models.
        """
        # Convert address - ES returns dict or None
        if 'address' in data and data['address']:
            data['address'] = Address(**data['address'])
        else:
            # Provide default address if missing or None
            data['address'] = Address()
        
        # Convert parking - ES returns dict or None
        if 'parking' in data and data['parking']:
            parking_data = data['parking'].copy()
            # Normalize parking type if present
            if 'type' in parking_data and parking_data['type']:
                parking_type_str = str(parking_data['type']).lower()
                try:
                    parking_data['type'] = ParkingType(parking_type_str)
                except ValueError:
                    # If not a valid enum value, default to NONE
                    parking_data['type'] = ParkingType.NONE
            data['parking'] = Parking(**parking_data)
        else:
            # Provide default parking if missing
            data['parking'] = Parking()
        
        return data
    
    @staticmethod
    def _normalize_enums(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize enum fields to their proper types."""
        # Convert property_type
        if 'property_type' in data:
            data['property_type'] = PropertyListing._normalize_property_type(data['property_type'])
        
        # Convert status
        if 'status' in data:
            data['status'] = PropertyListing._normalize_status(data['status'])
        else:
            data['status'] = PropertyStatus.ACTIVE
        
        return data
    
    @staticmethod
    def _handle_search_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search-related metadata fields."""
        # Handle highlights field - map to search_highlights
        if 'highlights' in data:
            data['search_highlights'] = data.pop('highlights')
        
        # Other metadata fields (_id, _score, _sort, distance_km) are preserved as-is
        return data
    
    @staticmethod
    def _convert_dates(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert date strings from Elasticsearch to datetime objects.
        
        Args:
            data: Dictionary with potential date fields
            
        Returns:
            Dictionary with converted date fields
        """
        date_fields = ['list_date', 'last_sold_date', 'embedded_at']
        
        for field in date_fields:
            if field in data and data[field]:
                try:
                    # Parse ISO format string from Elasticsearch
                    data[field] = datetime.fromisoformat(
                        str(data[field]).replace('Z', '+00:00')
                    )
                except (ValueError, AttributeError, TypeError):
                    # Keep original value if not parseable
                    pass
        
        return data
    
    @staticmethod
    def _normalize_property_type(type_value: str) -> PropertyType:
        """
        Normalize property type string from Elasticsearch to PropertyType enum.
        
        Args:
            type_value: String value from Elasticsearch
            
        Returns:
            PropertyType enum value
        """
        if not type_value:
            return PropertyType.OTHER
            
        # Normalize string: lowercase, replace separators with underscore
        normalized = str(type_value).lower().replace('-', '_').replace(' ', '_')
        
        # Comprehensive mapping of variations
        type_mapping = {
            'single_family': PropertyType.SINGLE_FAMILY,
            'singlefamily': PropertyType.SINGLE_FAMILY,
            'single': PropertyType.SINGLE_FAMILY,
            'condo': PropertyType.CONDO,
            'condominium': PropertyType.CONDO,
            'townhome': PropertyType.TOWNHOUSE,
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
        
        return type_mapping.get(normalized, PropertyType.OTHER)
    
    @staticmethod
    def _normalize_status(status_value: str) -> PropertyStatus:
        """
        Normalize status string from Elasticsearch to PropertyStatus enum.
        
        Args:
            status_value: String value from Elasticsearch
            
        Returns:
            PropertyStatus enum value
        """
        if not status_value:
            return PropertyStatus.ACTIVE
            
        # Normalize string: lowercase, replace separators with underscore
        normalized = str(status_value).lower().replace('-', '_').replace(' ', '_')
        
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
        
        return status_mapping.get(normalized, PropertyStatus.ACTIVE)