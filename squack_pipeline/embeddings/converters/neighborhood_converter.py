"""Neighborhood-specific document converter."""

from typing import List, Dict, Any, Optional

from llama_index.core import Document
from squack_pipeline.embeddings.converters.base_converter import (
    BaseDocumentConverter, ConversionConfig
)
from squack_pipeline.models import EntityType


class NeighborhoodDocumentConverter(BaseDocumentConverter):
    """Convert neighborhood data to LlamaIndex Documents.
    
    This converter handles the transformation of Gold tier neighborhood data
    into Documents optimized for embedding generation, preserving location
    context and demographic information.
    """
    
    def __init__(self, config: Optional[ConversionConfig] = None):
        """Initialize neighborhood document converter.
        
        Args:
            config: Optional conversion configuration
        """
        if config is None:
            config = ConversionConfig(
                entity_type=EntityType.NEIGHBORHOOD,
                embedding_fields=[
                    "name",
                    "description",
                    "characteristics",
                    "demographics",
                    "amenities",
                    "city",
                    "state"
                ]
            )
        super().__init__(config)
    
    def convert_to_documents(self, data: List[Dict[str, Any]]) -> List[Document]:
        """Convert neighborhood data to LlamaIndex Documents.
        
        Args:
            data: List of neighborhood records from Gold tier
            
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
                
                # Create document with neighborhood ID as doc_id
                doc = self.create_document(
                    text=text,
                    metadata=metadata,
                    doc_id=record.get("neighborhood_id")
                )
                
                documents.append(doc)
                
            except Exception as e:
                self.logger.error(
                    f"Error converting neighborhood {record.get('neighborhood_id', 'unknown')}: {e}"
                )
                continue
        
        self.logger.info(f"Converted {len(documents)} neighborhoods to documents")
        return documents
    
    def create_text_content(self, record: Dict[str, Any]) -> str:
        """Create rich text content from neighborhood data.
        
        Args:
            record: Neighborhood record from Gold tier
            
        Returns:
            Text content for embedding
        """
        text_parts = []
        
        # Neighborhood header
        name = record.get("name")
        if name:
            text_parts.append(f"Neighborhood: {name}")
        
        neighborhood_id = record.get("neighborhood_id")
        if neighborhood_id:
            text_parts.append(f"ID: {neighborhood_id}")
        
        # Location information
        city = record.get("city")
        state = record.get("state")
        county = record.get("county")
        
        if city and state:
            location_parts = [city, state]
            if county:
                location_parts.append(f"{county} County")
            text_parts.append(f"Location: {', '.join(location_parts)}")
        
        # Description
        description = record.get("description")
        if description:
            text_parts.append(f"\nDescription:\n{description}")
        
        # Characteristics (array field)
        characteristics = record.get("characteristics")
        if characteristics and isinstance(characteristics, list):
            text_parts.append(f"\nCharacteristics:\n- " + "\n- ".join(characteristics))
        
        # Demographics (nested structure)
        demographics = record.get("demographics", {})
        if demographics:
            demo_parts = []
            
            population = demographics.get("population")
            if population:
                demo_parts.append(f"Population: {population:,}")
            
            median_age = demographics.get("median_age")
            if median_age:
                demo_parts.append(f"Median Age: {median_age}")
            
            median_income = demographics.get("median_income")
            if median_income:
                demo_parts.append(f"Median Income: ${median_income:,.0f}")
            
            households = demographics.get("households")
            if households:
                demo_parts.append(f"Households: {households:,}")
            
            if demo_parts:
                text_parts.append(f"\nDemographics:\n" + ", ".join(demo_parts))
        
        # Statistics (nested structure)
        statistics = record.get("statistics", {})
        if statistics:
            stat_parts = []
            
            avg_home_value = statistics.get("avg_home_value")
            if avg_home_value:
                stat_parts.append(f"Avg Home Value: ${avg_home_value:,.0f}")
            
            avg_rent = statistics.get("avg_rent")
            if avg_rent:
                stat_parts.append(f"Avg Rent: ${avg_rent:,.0f}")
            
            crime_rate = statistics.get("crime_rate")
            if crime_rate:
                stat_parts.append(f"Crime Rate: {crime_rate}")
            
            walkability_score = statistics.get("walkability_score")
            if walkability_score:
                stat_parts.append(f"Walkability: {walkability_score}/100")
            
            if stat_parts:
                text_parts.append(f"\nStatistics:\n" + ", ".join(stat_parts))
        
        # Amenities (array field)
        amenities = record.get("amenities")
        if amenities and isinstance(amenities, list):
            text_parts.append(f"\nAmenities:\n- " + "\n- ".join(amenities))
        
        # Schools (array of nested structures)
        schools = record.get("schools")
        if schools and isinstance(schools, list):
            school_parts = []
            for school in schools:
                name = school.get("name")
                rating = school.get("rating")
                if name:
                    school_text = name
                    if rating:
                        school_text += f" (Rating: {rating}/10)"
                    school_parts.append(school_text)
            
            if school_parts:
                text_parts.append(f"\nSchools:\n- " + "\n- ".join(school_parts))
        
        # Join all parts
        return "\n".join(text_parts)
    
    def create_metadata(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata from neighborhood record.
        
        Args:
            record: Neighborhood record from Gold tier
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            "entity_type": "neighborhood",
            "neighborhood_id": record.get("neighborhood_id"),
            "name": record.get("name"),
        }
        
        # Add location metadata
        metadata["city"] = record.get("city")
        metadata["state"] = record.get("state")
        metadata["county"] = record.get("county")
        metadata["zip_codes"] = record.get("zip_codes")
        
        # Add demographic metadata from nested structure
        demographics = record.get("demographics", {})
        if demographics:
            metadata["population"] = demographics.get("population")
            metadata["median_age"] = demographics.get("median_age")
            metadata["median_income"] = demographics.get("median_income")
            metadata["households"] = demographics.get("households")
        
        # Add statistics metadata from nested structure
        statistics = record.get("statistics", {})
        if statistics:
            metadata["avg_home_value"] = statistics.get("avg_home_value")
            metadata["avg_rent"] = statistics.get("avg_rent")
            metadata["crime_rate"] = statistics.get("crime_rate")
            metadata["walkability_score"] = statistics.get("walkability_score")
        
        # Add coordinates if available
        coordinates = record.get("coordinates", {})
        if coordinates:
            metadata["latitude"] = coordinates.get("latitude")
            metadata["longitude"] = coordinates.get("longitude")
        
        # Add location array if available (for geo queries)
        location = record.get("location")
        if location:
            metadata["location"] = location
        
        # Add boundaries if available
        boundaries = record.get("boundaries")
        if boundaries:
            metadata["boundaries"] = boundaries
        
        # Add property count
        metadata["property_count"] = record.get("property_count")
        
        # Add processing metadata
        metadata["gold_processed_at"] = record.get("gold_processed_at")
        metadata["processing_version"] = record.get("processing_version")
        
        return metadata