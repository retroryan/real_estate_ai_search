"""Property-specific document converter."""

from typing import List, Dict, Any, Optional

from llama_index.core import Document
from squack_pipeline.embeddings.converters.base_converter import (
    BaseDocumentConverter, ConversionConfig
)
from squack_pipeline.models import EntityType


class PropertyDocumentConverter(BaseDocumentConverter):
    """Convert property data to LlamaIndex Documents.
    
    This converter handles the transformation of Gold tier property data
    into Documents optimized for embedding generation, preserving nested
    structures and creating rich text representations.
    """
    
    def __init__(self, config: Optional[ConversionConfig] = None):
        """Initialize property document converter.
        
        Args:
            config: Optional conversion configuration
        """
        if config is None:
            config = ConversionConfig(
                entity_type=EntityType.PROPERTY,
                embedding_fields=[
                    "description",
                    "amenities",
                    "features",
                    "address",
                    "property_details",
                    "neighborhood_name"
                ]
            )
        super().__init__(config)
    
    def convert_to_documents(self, data: List[Dict[str, Any]]) -> List[Document]:
        """Convert property data to LlamaIndex Documents.
        
        Args:
            data: List of property records from Gold tier
            
        Returns:
            List of LlamaIndex Documents
        """
        documents = []
        
        for record in data:
            try:
                # Create text content
                text = self.create_text_content(record)
                
                # Create metadata
                metadata = self.create_metadata(record)
                
                # Create document with property ID as doc_id
                doc = self.create_document(
                    text=text,
                    metadata=metadata,
                    doc_id=record.get("listing_id")
                )
                
                documents.append(doc)
                
            except Exception as e:
                self.logger.error(
                    f"Error converting property {record.get('listing_id', 'unknown')}: {e}"
                )
                continue
        
        self.logger.info(f"Converted {len(documents)} properties to documents")
        return documents
    
    def create_text_content(self, record: Dict[str, Any]) -> str:
        """Create rich text content from property data.
        
        Args:
            record: Property record from Gold tier
            
        Returns:
            Text content for embedding
        """
        text_parts = []
        
        # Property header
        listing_id = record.get("listing_id")
        if listing_id:
            text_parts.append(f"Property Listing: {listing_id}")
        
        # Location information from nested address
        address = record.get("address", {})
        if address:
            location_parts = []
            if address.get("street"):
                location_parts.append(address["street"])
            if address.get("city"):
                location_parts.append(address["city"])
            if address.get("state"):
                location_parts.append(address["state"])
            if address.get("zip"):
                location_parts.append(str(address["zip"]))
            
            if location_parts:
                text_parts.append(f"Location: {', '.join(location_parts)}")
        
        # Property details from nested structure
        details = record.get("property_details", {})
        if details:
            detail_parts = []
            
            bedrooms = details.get("bedrooms")
            if bedrooms:
                detail_parts.append(f"{bedrooms} bedrooms")
            
            bathrooms = details.get("bathrooms")
            if bathrooms:
                detail_parts.append(f"{bathrooms} bathrooms")
            
            square_feet = details.get("square_feet")
            if square_feet:
                detail_parts.append(f"{square_feet:,} square feet")
            
            property_type = details.get("property_type")
            if property_type:
                detail_parts.append(f"Type: {property_type}")
            
            year_built = details.get("year_built")
            if year_built:
                detail_parts.append(f"Built: {year_built}")
            
            if detail_parts:
                text_parts.append(f"Details: {', '.join(detail_parts)}")
        
        # Price information
        price = record.get("price")
        if price:
            text_parts.append(f"Price: ${price:,.0f}")
            
            price_per_sqft = record.get("price_per_sqft")
            if price_per_sqft:
                text_parts.append(f"Price per sqft: ${price_per_sqft:,.2f}")
        
        # Description
        description = record.get("description")
        if description:
            text_parts.append(f"\nDescription:\n{description}")
        
        # Features (array field)
        features = record.get("features")
        if features and isinstance(features, list):
            text_parts.append(f"\nFeatures:\n- " + "\n- ".join(features))
        
        # Amenities
        amenities = record.get("amenities")
        if amenities:
            if isinstance(amenities, list):
                text_parts.append(f"\nAmenities:\n- " + "\n- ".join(amenities))
            elif isinstance(amenities, str):
                text_parts.append(f"\nAmenities:\n{amenities}")
        
        # Neighborhood information (from denormalized fields)
        neighborhood_name = record.get("neighborhood_name")
        if neighborhood_name:
            text_parts.append(f"\nNeighborhood: {neighborhood_name}")
        
        # Join all parts
        return "\n".join(text_parts)
    
    def create_metadata(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata from property record.
        
        Args:
            record: Property record from Gold tier
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            "entity_type": "property",
            "listing_id": record.get("listing_id"),
            "neighborhood_id": record.get("neighborhood_id"),
        }
        
        # Add location metadata from nested address
        address = record.get("address", {})
        if address:
            metadata["city"] = address.get("city")
            metadata["state"] = address.get("state")
            metadata["zip"] = address.get("zip")
        
        # Add property characteristics from nested details
        details = record.get("property_details", {})
        if details:
            metadata["property_type"] = details.get("property_type")
            metadata["bedrooms"] = details.get("bedrooms")
            metadata["bathrooms"] = details.get("bathrooms")
            metadata["square_feet"] = details.get("square_feet")
            metadata["year_built"] = details.get("year_built")
        
        # Add price metadata
        metadata["price"] = record.get("price")
        metadata["price_per_sqft"] = record.get("price_per_sqft")
        
        # Add coordinates if available
        coordinates = record.get("coordinates", {})
        if coordinates:
            metadata["latitude"] = coordinates.get("latitude")
            metadata["longitude"] = coordinates.get("longitude")
        
        # Add location array if available (for geo queries)
        location = record.get("location")
        if location:
            metadata["location"] = location
        
        # Add parking information if available
        parking = record.get("parking", {})
        if parking:
            metadata["garage_spaces"] = parking.get("spaces")
            metadata["parking_available"] = parking.get("available")
        
        # Add computed fields
        metadata["days_on_market"] = record.get("days_on_market")
        metadata["listing_date"] = record.get("listing_date")
        
        # Add processing metadata
        metadata["gold_processed_at"] = record.get("gold_processed_at")
        metadata["processing_version"] = record.get("processing_version")
        
        return metadata