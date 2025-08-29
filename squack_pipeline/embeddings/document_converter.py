"""Document conversion from Pydantic models to LlamaIndex Documents."""

from typing import List, Dict, Any
from pathlib import Path

from llama_index.core import Document
from llama_index.core.schema import MetadataMode

from squack_pipeline.utils.logging import PipelineLogger


class DocumentConverter:
    """Convert Pydantic models to LlamaIndex Documents following common_embeddings patterns."""
    
    def __init__(self):
        """Initialize document converter."""
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
    
    def convert_gold_properties_to_documents(self, properties_data: List[Dict[str, Any]]) -> List[Document]:
        """Convert Gold tier property records to LlamaIndex Documents.
        
        Args:
            properties_data: List of property records from Gold tier
            
        Returns:
            List of LlamaIndex Documents
        """
        documents = []
        
        for prop in properties_data:
            try:
                # Create rich text content from property data
                text_content = self._create_property_text(prop)
                
                # Create comprehensive metadata
                metadata = self._create_property_metadata(prop)
                
                # Create document
                doc = Document(
                    text=text_content,
                    metadata=metadata,
                    excluded_embed_metadata_keys=[
                        "property_id", "chunk_index", "chunk_total", 
                        "processing_version", "created_at"
                    ],
                    excluded_llm_metadata_keys=[
                        "embedding_dimension", "text_hash"
                    ]
                )
                
                documents.append(doc)
                
            except Exception as e:
                self.logger.error(f"Error converting property {prop.get('listing_id', 'unknown')}: {e}")
                continue
        
        self.logger.info(f"Converted {len(documents)} properties to documents")
        return documents
    
    def _create_property_text(self, prop: Dict[str, Any]) -> str:
        """Create rich text content from property data for optimal embeddings."""
        
        # Basic property information
        address = prop.get('address', {})
        details = prop.get('property_details', {})
        
        # Build structured text content
        text_parts = []
        
        # Property header
        if prop.get('listing_id'):
            text_parts.append(f"Property Listing: {prop['listing_id']}")
        
        # Location information
        if address:
            location_text = []
            if address.get('street'):
                location_text.append(address['street'])
            if address.get('city'):
                location_text.append(address['city'])
            if address.get('state'):
                location_text.append(address['state'])
            if address.get('zip'):
                location_text.append(address['zip'])
            
            if location_text:
                text_parts.append(f"Location: {', '.join(location_text)}")
        
        # Property details
        if details:
            detail_parts = []
            if details.get('bedrooms'):
                detail_parts.append(f"{details['bedrooms']} bedrooms")
            if details.get('bathrooms'):
                detail_parts.append(f"{details['bathrooms']} bathrooms")
            if details.get('square_feet'):
                detail_parts.append(f"{details['square_feet']} square feet")
            if details.get('property_type'):
                detail_parts.append(f"Property type: {details['property_type']}")
            if details.get('year_built'):
                detail_parts.append(f"Built in {details['year_built']}")
            
            if detail_parts:
                text_parts.append("Property Details: " + ", ".join(detail_parts))
        
        # Price information
        if prop.get('listing_price'):
            text_parts.append(f"Price: ${prop['listing_price']:,.2f}")
            
        if prop.get('price_per_sqft'):
            text_parts.append(f"Price per square foot: ${prop['price_per_sqft']:.2f}")
        
        # Gold tier enrichments
        if prop.get('value_category'):
            text_parts.append(f"Value Category: {prop['value_category']}")
            
        if prop.get('size_category'):
            text_parts.append(f"Size Category: {prop['size_category']}")
            
        if prop.get('age_category'):
            text_parts.append(f"Age Category: {prop['age_category']}")
            
        if prop.get('market_status'):
            text_parts.append(f"Market Status: {prop['market_status']}")
        
        # Geographic enrichments
        if prop.get('geographic_region'):
            text_parts.append(f"Geographic Region: {prop['geographic_region']}")
            
        if prop.get('closest_major_city'):
            text_parts.append(f"Closest Major City: {prop['closest_major_city']}")
        
        # Property description
        if prop.get('description') and len(prop['description'].strip()) > 0:
            text_parts.append(f"Description: {prop['description'].strip()}")
        
        # Features
        if prop.get('features') and len(prop['features']) > 0:
            features_text = ", ".join(prop['features'])
            text_parts.append(f"Features: {features_text}")
        
        # Join all parts
        return "\n".join(text_parts)
    
    def _create_property_metadata(self, prop: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive metadata for property document."""
        metadata = {
            # Entity identification
            "entity_type": "property",
            "property_id": prop.get('listing_id', 'unknown'),
            "neighborhood_id": prop.get('neighborhood_id'),
            
            # Geographic information
            "city": prop.get('address', {}).get('city'),
            "state": prop.get('address', {}).get('state'),
            "zip_code": prop.get('address', {}).get('zip'),
            "geographic_region": prop.get('geographic_region'),
            "closest_major_city": prop.get('closest_major_city'),
            
            # Property characteristics
            "bedrooms": prop.get('property_details', {}).get('bedrooms'),
            "bathrooms": prop.get('property_details', {}).get('bathrooms'),
            "square_feet": prop.get('property_details', {}).get('square_feet'),
            "property_type": prop.get('property_details', {}).get('property_type'),
            "year_built": prop.get('property_details', {}).get('year_built'),
            
            # Price information
            "listing_price": prop.get('listing_price'),
            "price_per_sqft": prop.get('price_per_sqft'),
            
            # Gold tier categories
            "value_category": prop.get('value_category'),
            "size_category": prop.get('size_category'),
            "age_category": prop.get('age_category'),
            "market_status": prop.get('market_status'),
            
            # Scoring
            "desirability_score": prop.get('desirability_score'),
            "description_quality_score": prop.get('description_quality_score'),
            
            # Coordinate data
            "has_valid_coordinates": prop.get('has_valid_coordinates', False),
            
            # Processing metadata
            "processing_tier": "gold_enriched",
            "processing_version": prop.get('gold_processing_version', 'unknown'),
        }
        
        # Add coordinates if available
        coordinates = prop.get('coordinates', {})
        if coordinates.get('latitude') is not None and coordinates.get('longitude') is not None:
            metadata["latitude"] = coordinates['latitude']
            metadata["longitude"] = coordinates['longitude']
        
        # Add distance calculations if available
        for key, value in prop.items():
            if key.startswith('distance_to_') and key.endswith('_km') and value is not None:
                metadata[key] = value
        
        # Add urban accessibility score
        if prop.get('urban_accessibility_score') is not None:
            metadata["urban_accessibility_score"] = prop['urban_accessibility_score']
        
        # Filter out None values
        return {k: v for k, v in metadata.items() if v is not None}
    
    def convert_neighborhoods_to_documents(self, neighborhoods_data: List[Dict[str, Any]]) -> List[Document]:
        """Convert neighborhood records to LlamaIndex Documents.
        
        Args:
            neighborhoods_data: List of neighborhood records
            
        Returns:
            List of LlamaIndex Documents
        """
        documents = []
        
        for hood in neighborhoods_data:
            try:
                # Create rich text content from neighborhood data
                text_content = self._create_neighborhood_text(hood)
                
                # Create comprehensive metadata
                metadata = self._create_neighborhood_metadata(hood)
                
                # Create document
                doc = Document(
                    text=text_content,
                    metadata=metadata,
                    excluded_embed_metadata_keys=[
                        "neighborhood_id", "chunk_index", "chunk_total", 
                        "processing_version", "created_at"
                    ],
                    excluded_llm_metadata_keys=[
                        "embedding_dimension", "text_hash"
                    ]
                )
                
                documents.append(doc)
                
            except Exception as e:
                self.logger.error(f"Error converting neighborhood {hood.get('neighborhood_id', 'unknown')}: {e}")
                continue
        
        self.logger.info(f"Converted {len(documents)} neighborhoods to documents")
        return documents
    
    def _create_neighborhood_text(self, hood: Dict[str, Any]) -> str:
        """Create rich text content from neighborhood data for optimal embeddings."""
        text_parts = []
        
        # Neighborhood header
        if hood.get('name'):
            text_parts.append(f"Neighborhood: {hood['name']}")
        
        # Location
        location_parts = []
        if hood.get('city'):
            location_parts.append(hood['city'])
        if hood.get('state'):
            location_parts.append(hood['state'])
        if location_parts:
            text_parts.append(f"Location: {', '.join(location_parts)}")
        
        # Demographics
        if hood.get('population'):
            text_parts.append(f"Population: {hood['population']:,}")
        if hood.get('median_income'):
            text_parts.append(f"Median Income: ${hood['median_income']:,.0f}")
        if hood.get('median_age'):
            text_parts.append(f"Median Age: {hood['median_age']:.1f}")
        
        # Scores and ratings
        if hood.get('walkability_score'):
            text_parts.append(f"Walkability Score: {hood['walkability_score']}")
        if hood.get('transit_score'):
            text_parts.append(f"Transit Score: {hood['transit_score']}")
        if hood.get('school_rating'):
            text_parts.append(f"School Rating: {hood['school_rating']:.1f}")
        
        # Categories (from Gold tier)
        if hood.get('income_category'):
            text_parts.append(f"Income Category: {hood['income_category']}")
        if hood.get('walkability_category'):
            text_parts.append(f"Walkability: {hood['walkability_category']}")
        if hood.get('school_category'):
            text_parts.append(f"Schools: {hood['school_category']}")
        
        # Description
        if hood.get('description'):
            text_parts.append(f"Description: {hood['description'].strip()}")
        
        # Amenities
        if hood.get('amenities') and len(hood['amenities']) > 0:
            amenities_text = ", ".join(hood['amenities'])
            text_parts.append(f"Amenities: {amenities_text}")
        
        return "\n".join(text_parts)
    
    def _create_neighborhood_metadata(self, hood: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive metadata for neighborhood document."""
        metadata = {
            "entity_type": "neighborhood",
            "neighborhood_id": hood.get('neighborhood_id', 'unknown'),
            "name": hood.get('name', ''),
            "city": hood.get('city', ''),
            "state": hood.get('state', ''),
            "walkability_score": hood.get('walkability_score', 0),
            "transit_score": hood.get('transit_score', 0),
            "school_rating": hood.get('school_rating', 0.0),
            "population": hood.get('population', 0),
            "median_income": hood.get('median_income', 0.0)
        }
        
        # Add coordinates if available
        if hood.get('latitude') and hood.get('longitude'):
            metadata['latitude'] = hood['latitude']
            metadata['longitude'] = hood['longitude']
        
        return metadata
    
    def convert_wikipedia_to_documents(self, wikipedia_data: List[Dict[str, Any]]) -> List[Document]:
        """Convert Wikipedia articles to LlamaIndex Documents.
        
        Args:
            wikipedia_data: List of Wikipedia article records
            
        Returns:
            List of LlamaIndex Documents
        """
        documents = []
        
        for article in wikipedia_data:
            try:
                # Create text content from Wikipedia data (use summary, not full content for efficiency)
                text_content = self._create_wikipedia_text(article)
                
                # Create metadata
                metadata = self._create_wikipedia_metadata(article)
                
                # Create document
                doc = Document(
                    text=text_content,
                    metadata=metadata,
                    excluded_embed_metadata_keys=[
                        "page_id", "chunk_index", "chunk_total", 
                        "processing_version", "created_at", "url"
                    ],
                    excluded_llm_metadata_keys=[
                        "embedding_dimension", "text_hash", "word_count"
                    ]
                )
                
                documents.append(doc)
                
            except Exception as e:
                self.logger.error(f"Error converting Wikipedia article {article.get('page_id', 'unknown')}: {e}")
                continue
        
        self.logger.info(f"Converted {len(documents)} Wikipedia articles to documents")
        return documents
    
    def _create_wikipedia_text(self, article: Dict[str, Any]) -> str:
        """Create text content from Wikipedia article for optimal embeddings."""
        text_parts = []
        
        # Article header
        if article.get('title'):
            text_parts.append(f"Wikipedia Article: {article['title']}")
        
        # Relevance and category
        if article.get('relevance_score'):
            text_parts.append(f"Relevance Score: {article['relevance_score']:.2f}")
        if article.get('relevance_category'):
            text_parts.append(f"Relevance: {article['relevance_category']}")
        
        # Use summary if available, otherwise use display_summary
        summary_text = article.get('summary', '') or article.get('display_summary', '')
        if summary_text and len(summary_text.strip()) > 0:
            text_parts.append(f"Summary: {summary_text.strip()}")
        
        # Categories
        if article.get('categories') and len(article['categories']) > 0:
            categories_text = ", ".join(article['categories'][:5])  # Limit to first 5 categories
            text_parts.append(f"Categories: {categories_text}")
        
        return "\n".join(text_parts)
    
    def _create_wikipedia_metadata(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata for Wikipedia document."""
        metadata = {
            "entity_type": "wikipedia",
            "page_id": article.get('page_id', 'unknown'),
            "title": article.get('title', ''),
            "relevance_score": article.get('relevance_score', 0.0),
            "word_count": article.get('word_count', 0),
            "article_length": article.get('article_length', 'unknown')
        }
        
        # Add coordinates if available
        if article.get('latitude') and article.get('longitude'):
            metadata['latitude'] = article['latitude']
            metadata['longitude'] = article['longitude']
        
        return metadata
    
    def validate_documents(self, documents: List[Document]) -> bool:
        """Validate converted documents for all entity types."""
        if not documents:
            self.logger.error("No documents to validate")
            return False
        
        # Check document structure
        for i, doc in enumerate(documents):
            if not doc.text or len(doc.text.strip()) == 0:
                self.logger.error(f"Document {i} has empty text content")
                return False
            
            if not doc.metadata:
                self.logger.error(f"Document {i} has no metadata")
                return False
            
            # Check for entity type
            if "entity_type" not in doc.metadata:
                self.logger.error(f"Document {i} missing entity_type in metadata")
                return False
            
            # Check entity-specific required fields
            entity_type = doc.metadata["entity_type"]
            if entity_type == "property":
                if "property_id" not in doc.metadata:
                    self.logger.error(f"Property document {i} missing property_id")
                    return False
            elif entity_type == "neighborhood":
                if "neighborhood_id" not in doc.metadata:
                    self.logger.error(f"Neighborhood document {i} missing neighborhood_id")
                    return False
            elif entity_type == "wikipedia":
                if "page_id" not in doc.metadata:
                    self.logger.error(f"Wikipedia document {i} missing page_id")
                    return False
        
        self.logger.info(f"Validated {len(documents)} documents successfully")
        return True