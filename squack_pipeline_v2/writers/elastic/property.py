"""Property writer for Elasticsearch."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator, model_validator

from squack_pipeline_v2.writers.elastic.base import ElasticsearchWriterBase
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import log_stage
from squack_pipeline_v2.core.settings import PipelineSettings

logger = logging.getLogger(__name__)


# ============================================================================
# NESTED MODELS FOR ELASTICSEARCH STRUCTURE
# ============================================================================

class GeoPoint(BaseModel):
    """Elasticsearch geo_point structure."""
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class ParkingInfo(BaseModel):
    """Parking information structure."""
    spaces: int = Field(ge=0, default=0)
    type: str = Field(default="none")


class AddressInfo(BaseModel):
    """Address information structure matching ES template."""
    street: str = ""
    city: str
    state: str
    zip_code: str = ""
    location: GeoPoint


# ============================================================================
# PROPERTY DOCUMENT MODEL
# ============================================================================

class PropertyDocument(BaseModel):
    """Property document for Elasticsearch - single model for transformation."""
    
    # Core fields
    listing_id: str
    neighborhood_id: str = ""
    price: float
    bedrooms: int
    bathrooms: float
    square_feet: int
    property_type: str
    year_built: int = 0
    lot_size: int = 0
    
    # Nested structures
    address: AddressInfo
    price_per_sqft: float = 0.0
    parking: ParkingInfo
    
    # Text and list fields
    description: str = ""
    features: List[str] = Field(default_factory=list)
    amenities: List[str] = Field(default_factory=list)
    status: str = "active"
    search_tags: List[str] = Field(default_factory=list)
    
    # Date fields
    listing_date: str = ""
    days_on_market: int = 0
    
    # Media fields
    virtual_tour_url: str = ""
    images: List[str] = Field(default_factory=list)
    
    # Embedding fields
    embedding: List[float] = Field(default_factory=list)
    embedding_model: str = ""
    embedding_dimension: int = 0
    embedded_at: datetime = Field(default_factory=datetime.now)
    indexed_at: datetime = Field(default_factory=datetime.now)


# ============================================================================
# TRANSFORMATION FUNCTION
# ============================================================================

def transform_property(record: Dict[str, Any], embedding_model: str) -> PropertyDocument:
    """Transform DuckDB property record to Elasticsearch document.
    
    Args:
        record: Raw dictionary from DuckDB query
        embedding_model: Name of the embedding model used
        
    Returns:
        PropertyDocument ready for Elasticsearch
    """
    # Extract and transform address data
    address_data = record.get('address', {})
    location_array = address_data.get('location', [0, 0])
    
    # Build GeoPoint from location array [lon, lat]
    geo_point = GeoPoint(
        lat=float(location_array[1]) if len(location_array) > 1 else 0.0,
        lon=float(location_array[0]) if len(location_array) > 0 else 0.0
    )
    
    # Build AddressInfo
    address = AddressInfo(
        street=address_data.get('street', ''),
        city=address_data.get('city', ''),
        state=address_data.get('state', ''),
        zip_code=address_data.get('zip_code', ''),
        location=geo_point
    )
    
    # Build ParkingInfo
    parking_data = record.get('parking', {})
    parking = ParkingInfo(
        spaces=parking_data.get('spaces', 0),
        type=parking_data.get('type', 'none')
    )
    
    # Convert date to ISO string if present
    listing_date_str = ""
    listing_date_raw = record.get('listing_date')
    if listing_date_raw:
        # DuckDB returns date objects which have isoformat
        try:
            listing_date_str = listing_date_raw.isoformat()
        except AttributeError:
            listing_date_str = str(listing_date_raw)
    
    # Convert tuple embedding to list
    embedding_vector = record.get('embedding_vector', tuple())
    embedding_list = list(embedding_vector) if embedding_vector else []
    
    # Get embedding timestamp
    embedded_at = record.get('embedding_generated_at')
    if not embedded_at:
        embedded_at = datetime.now()
    
    # Create PropertyDocument with all transformations
    return PropertyDocument(
        listing_id=record['listing_id'],
        neighborhood_id=record.get('neighborhood_id', ''),
        price=float(record['price']),
        bedrooms=int(record['bedrooms']),
        bathrooms=float(record['bathrooms']),
        square_feet=int(record['square_feet']),
        property_type=record['property_type'],
        year_built=int(record.get('year_built', 0)),
        lot_size=int(record.get('lot_size', 0)),
        address=address,
        price_per_sqft=float(record.get('price_per_sqft', 0.0)),
        parking=parking,
        description=record.get('description', ''),
        features=record.get('features', []),
        amenities=record.get('amenities', []),
        status=record.get('status', 'active'),
        search_tags=record.get('search_tags', []),
        listing_date=listing_date_str,
        days_on_market=int(record.get('days_on_market', 0)),
        virtual_tour_url=record.get('virtual_tour_url', ''),
        images=record.get('images', []),
        embedding=embedding_list,
        embedding_model=embedding_model,
        embedding_dimension=len(embedding_list),
        embedded_at=embedded_at
    )


# ============================================================================
# PROPERTY WRITER CLASS
# ============================================================================

class PropertyWriter(ElasticsearchWriterBase):
    """Writer for indexing properties to Elasticsearch."""
    
    @log_stage("Elasticsearch: Index properties")
    def index_properties(
        self,
        table_name: str = "gold_properties",
        index_name: str = "properties",
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """Index properties to Elasticsearch.
        
        Args:
            table_name: DuckDB table containing properties
            index_name: Target Elasticsearch index
            batch_size: Number of documents per batch
            
        Returns:
            Indexing statistics
        """
        query = f"SELECT * FROM {DuckDBConnectionManager.safe_identifier(table_name)}"
        
        # Create transform function with embedded model name
        def transform(record: Dict[str, Any]) -> PropertyDocument:
            return transform_property(record, self.embedding_model)
        
        return self._index_documents(
            query=query,
            index_name=index_name,
            transform=transform,
            id_field="listing_id",
            batch_size=batch_size
        )