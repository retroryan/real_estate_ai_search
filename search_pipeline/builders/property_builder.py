"""Property document builder for search pipeline.

Transforms property DataFrames into PropertyDocument models for Elasticsearch indexing.
Creates properly nested documents matching the Elasticsearch mappings exactly.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pyspark.sql import DataFrame

from search_pipeline.builders.base import BaseDocumentBuilder
from search_pipeline.models.documents import (
    PropertyDocument,
    AddressModel,
    NeighborhoodModel,
    ParkingModel,
    LocationContextModel,
    NeighborhoodContextModel,
    NearbyPOIModel,
    LocationScoresModel,
    LandmarkModel
)

logger = logging.getLogger(__name__)


class PropertyDocumentBuilder(BaseDocumentBuilder):
    """
    Builder for transforming property DataFrames into PropertyDocument models.
    
    This builder maps DataFrame fields to nested document structure and creates
    Wikipedia-enriched search documents matching Elasticsearch mappings exactly.
    """
    
    def transform(self, df: DataFrame) -> List[PropertyDocument]:
        """
        Transform property DataFrame into PropertyDocument models.
        
        Args:
            df: Spark DataFrame containing property data
            
        Returns:
            List of PropertyDocument models
            
        Raises:
            ValueError: If required fields are missing
        """
        # Validate field mapping requirements first
        self.validate_field_mapping_requirements(df, "property")
        
        # Apply field name standardization
        df = self.apply_field_mapping(df, "property")
        
        # Validate required fields after mapping
        required_fields = ["listing_id"]
        self.validate_dataframe(df, required_fields)
        
        documents = []
        
        try:
            # Collect DataFrame rows
            rows = df.collect()
            
            for row in rows:
                try:
                    # Convert row to dictionary
                    try:
                        row_dict = row.asDict()
                    except AttributeError:
                        row_dict = dict(row)
                    
                    # Build document
                    doc = self._build_document(row_dict)
                    documents.append(doc)
                    
                except Exception as e:
                    self.logger.error(f"Error processing property row: {e}")
                    continue
            
            self.logger.info(f"Transformed {len(documents)} property documents")
            
        except Exception as e:
            self.logger.error(f"Error transforming property DataFrame: {e}")
            raise ValueError(f"Failed to transform properties: {e}")
        
        return documents
    
    def _build_document(self, row: Dict[str, Any]) -> PropertyDocument:
        """
        Build a PropertyDocument from a DataFrame row.
        
        Args:
            row: Dictionary representing a property row
            
        Returns:
            PropertyDocument model with nested structure
        """
        # Extract basic fields
        listing_id = str(self.extract_field(row, "listing_id"))
        
        # Extract property details
        property_type = self.extract_field(row, "property_type")
        price = self.extract_field(row, "price")
        bedrooms = self.extract_field(row, "bedrooms")
        bathrooms = self.extract_field(row, "bathrooms")
        square_feet = self.extract_field(row, "square_feet")
        lot_size = self.extract_field(row, "lot_size")
        year_built = self.extract_field(row, "year_built")
        
        # Build nested address object
        address = self._build_address(row)
        
        # Build nested neighborhood object
        neighborhood = self._build_neighborhood(row)
        
        # Extract description and features
        description = self.clean_text(self.extract_field(row, "description"))
        features = self.parse_list_field(self.extract_field(row, "features"))
        amenities = self.parse_list_field(self.extract_field(row, "amenities"))
        
        # Parse dates
        listing_date = self._parse_date(self.extract_field(row, "listing_date"))
        last_updated = self._parse_date(self.extract_field(row, "last_updated") or self.extract_field(row, "last_modified"))
        
        # Extract status and other fields
        status = self.extract_field(row, "status")
        days_on_market = self.extract_field(row, "days_on_market")
        
        # Financial fields
        price_per_sqft = self.extract_field(row, "price_per_sqft")
        hoa_fee = self.extract_field(row, "hoa_fee")
        tax_assessed_value = self.extract_field(row, "tax_assessed_value")
        annual_tax = self.extract_field(row, "annual_tax")
        
        # Build parking object
        parking = self._build_parking(row)
        
        # Media fields
        virtual_tour_url = self.extract_field(row, "virtual_tour_url")
        images = self.parse_list_field(self.extract_field(row, "images"))
        
        # Other fields
        mls_number = self.extract_field(row, "mls_number")
        search_tags = self.extract_field(row, "search_tags")
        
        # Build Wikipedia enrichment fields
        location_context = self._build_location_context(row)
        neighborhood_context = self._build_neighborhood_context(row)
        nearby_poi = self._build_nearby_poi(row)
        location_scores = self._build_location_scores(row)
        
        # Generate enriched search text
        enriched_search_text = self._generate_enriched_search_text(
            description=description,
            features=features,
            amenities=amenities,
            property_type=property_type,
            address=address,
            neighborhood=neighborhood,
            location_context=location_context,
            neighborhood_context=neighborhood_context,
            nearby_poi=nearby_poi,
        )
        
        # Extract embedding fields
        embedding = self.extract_field(row, "embedding")
        embedding_model = self.extract_field(row, "embedding_model")
        embedding_dimension = self.extract_field(row, "embedding_dimension")
        embedded_at = self._parse_date(self.extract_field(row, "embedded_at"))
        
        # Create document with new ID mapping
        return PropertyDocument(
            # Base document fields
            doc_id=listing_id,  # Use listing_id as doc_id for properties
            entity_id=listing_id,
            entity_type="property",
            # Property-specific fields
            listing_id=listing_id,  # Also preserve original listing_id
            property_type=property_type,
            price=price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            square_feet=square_feet,
            year_built=year_built,
            lot_size=lot_size,
            address=address,
            neighborhood=neighborhood,
            description=description,
            features=features,
            amenities=amenities,
            status=status,
            listing_date=listing_date,
            last_updated=last_updated,
            days_on_market=days_on_market,
            price_per_sqft=price_per_sqft,
            hoa_fee=hoa_fee,
            tax_assessed_value=tax_assessed_value,
            annual_tax=annual_tax,
            parking=parking,
            virtual_tour_url=virtual_tour_url,
            images=images,
            mls_number=mls_number,
            search_tags=search_tags,
            location_context=location_context,
            neighborhood_context=neighborhood_context,
            nearby_poi=nearby_poi,
            enriched_search_text=enriched_search_text,
            location_scores=location_scores,
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_dimension=embedding_dimension,
            embedded_at=embedded_at,
        )
    
    def _build_address(self, row: Dict[str, Any]) -> Optional[AddressModel]:
        """Build nested address object."""
        # Extract address fields
        street = self.clean_text(self.extract_field(row, "address") or self.extract_field(row, "street"))
        city = self.clean_text(self.extract_field(row, "city"))
        state = self.clean_text(self.extract_field(row, "state"))
        zip_code = self.extract_field(row, "zip_code")
        
        # Extract coordinates and create geo point
        latitude = self.extract_field(row, "latitude")
        longitude = self.extract_field(row, "longitude")
        location = None
        if latitude is not None and longitude is not None:
            try:
                location = [float(longitude), float(latitude)]  # [lon, lat] format for Elasticsearch
            except (ValueError, TypeError):
                location = None
        
        # Only create address object if we have some data
        if any([street, city, state, zip_code, location]):
            return AddressModel(
                street=street,
                city=city,
                state=state,
                zip_code=zip_code,
                location=location
            )
        return None
    
    def _build_neighborhood(self, row: Dict[str, Any]) -> Optional[NeighborhoodModel]:
        """Build nested neighborhood object."""
        neighborhood_id = self.extract_field(row, "neighborhood_id")
        neighborhood_name = self.clean_text(self.extract_field(row, "neighborhood_name") or self.extract_field(row, "neighborhood"))
        walkability_score = self.extract_field(row, "walkability_score")
        school_rating = self.extract_field(row, "school_rating")
        
        # Only create neighborhood object if we have some data
        if any([neighborhood_id, neighborhood_name, walkability_score, school_rating]):
            return NeighborhoodModel(
                id=neighborhood_id,
                name=neighborhood_name,
                walkability_score=walkability_score,
                school_rating=school_rating
            )
        return None
    
    def _build_parking(self, row: Dict[str, Any]) -> Optional[ParkingModel]:
        """Build nested parking object."""
        parking_spaces = self.extract_field(row, "parking_spaces")
        parking_type = self.extract_field(row, "parking_type")
        
        # Only create parking object if we have some data
        if any([parking_spaces, parking_type]):
            return ParkingModel(
                spaces=parking_spaces,
                type=parking_type
            )
        return None
    
    def _build_location_context(self, row: Dict[str, Any]) -> Optional[LocationContextModel]:
        """Build location context from Wikipedia data."""
        # Check if we have any location context data
        location_context_fields = [
            "location_wikipedia_page_id", "location_wikipedia_title", "location_summary",
            "historical_significance", "location_key_topics", "cultural_features",
            "recreational_features", "transportation_features", "location_type", "location_confidence"
        ]
        
        if not any(self.extract_field(row, field) for field in location_context_fields):
            return None
        
        # Extract fields
        wikipedia_page_id = self.extract_field(row, "location_wikipedia_page_id")
        wikipedia_title = self.clean_text(self.extract_field(row, "location_wikipedia_title"))
        location_summary = self.clean_text(self.extract_field(row, "location_summary"))
        historical_significance = self.clean_text(self.extract_field(row, "historical_significance"))
        key_topics = self.parse_list_field(self.extract_field(row, "location_key_topics"))
        cultural_features = self.parse_list_field(self.extract_field(row, "cultural_features"))
        recreational_features = self.parse_list_field(self.extract_field(row, "recreational_features"))
        transportation = self.parse_list_field(self.extract_field(row, "transportation_features"))
        location_type = self.extract_field(row, "location_type")
        confidence_score = self.extract_field(row, "location_confidence")
        
        # Build landmarks if available
        landmarks = self._build_landmarks(row)
        
        return LocationContextModel(
            wikipedia_page_id=wikipedia_page_id,
            wikipedia_title=wikipedia_title,
            location_summary=location_summary,
            historical_significance=historical_significance,
            key_topics=key_topics,
            landmarks=landmarks,
            cultural_features=cultural_features,
            recreational_features=recreational_features,
            transportation=transportation,
            location_type=location_type,
            confidence_score=confidence_score
        )
    
    def _build_neighborhood_context(self, row: Dict[str, Any]) -> Optional[NeighborhoodContextModel]:
        """Build neighborhood context from Wikipedia data."""
        # Check if we have any neighborhood context data
        neighborhood_context_fields = [
            "neighborhood_wikipedia_page_id", "neighborhood_wikipedia_title", "neighborhood_description",
            "neighborhood_history", "neighborhood_character", "notable_residents",
            "architectural_style", "establishment_year", "gentrification_index", "diversity_score"
        ]
        
        if not any(self.extract_field(row, field) for field in neighborhood_context_fields):
            return None
        
        # Extract fields
        wikipedia_page_id = self.extract_field(row, "neighborhood_wikipedia_page_id")
        wikipedia_title = self.clean_text(self.extract_field(row, "neighborhood_wikipedia_title"))
        description = self.clean_text(self.extract_field(row, "neighborhood_description"))
        history = self.clean_text(self.extract_field(row, "neighborhood_history"))
        character = self.clean_text(self.extract_field(row, "neighborhood_character"))
        notable_residents = self.parse_list_field(self.extract_field(row, "notable_residents"))
        architectural_style = self.parse_list_field(self.extract_field(row, "architectural_style"))
        establishment_year = self.extract_field(row, "establishment_year")
        gentrification_index = self.extract_field(row, "gentrification_index")
        diversity_score = self.extract_field(row, "diversity_score")
        key_topics = self.parse_list_field(self.extract_field(row, "neighborhood_key_topics"))
        
        return NeighborhoodContextModel(
            wikipedia_page_id=wikipedia_page_id,
            wikipedia_title=wikipedia_title,
            description=description,
            history=history,
            character=character,
            notable_residents=notable_residents,
            architectural_style=architectural_style,
            establishment_year=establishment_year,
            gentrification_index=gentrification_index,
            diversity_score=diversity_score,
            key_topics=key_topics
        )
    
    def _build_nearby_poi(self, row: Dict[str, Any]) -> List[NearbyPOIModel]:
        """Build nearby POI list from row data."""
        # This would typically come from a nested structure or array field
        # For now, return empty list - this will be populated by enrichment pipeline
        return []
    
    def _build_landmarks(self, row: Dict[str, Any]) -> List[LandmarkModel]:
        """Build landmarks list from row data."""
        # This would typically come from a nested structure or array field
        # For now, return empty list - this will be populated by enrichment pipeline
        return []
    
    def _build_location_scores(self, row: Dict[str, Any]) -> Optional[LocationScoresModel]:
        """Build location scores object."""
        # Extract score fields
        cultural_richness = self.extract_field(row, "cultural_richness")
        historical_importance = self.extract_field(row, "historical_importance")
        tourist_appeal = self.extract_field(row, "tourist_appeal")
        local_amenities = self.extract_field(row, "local_amenities")
        overall_desirability = self.extract_field(row, "overall_desirability")
        
        # Only create scores object if we have some data
        if any([cultural_richness, historical_importance, tourist_appeal, local_amenities, overall_desirability]):
            return LocationScoresModel(
                cultural_richness=cultural_richness,
                historical_importance=historical_importance,
                tourist_appeal=tourist_appeal,
                local_amenities=local_amenities,
                overall_desirability=overall_desirability
            )
        return None
    
    def _generate_enriched_search_text(
        self,
        description: Optional[str] = None,
        features: List[str] = None,
        amenities: List[str] = None,
        property_type: Optional[str] = None,
        address: Optional[AddressModel] = None,
        neighborhood: Optional[NeighborhoodModel] = None,
        location_context: Optional[LocationContextModel] = None,
        neighborhood_context: Optional[NeighborhoodContextModel] = None,
        nearby_poi: List[NearbyPOIModel] = None,
    ) -> Optional[str]:
        """
        Generate enriched search text combining property and Wikipedia data.
        
        Args:
            description: Property description
            features: Property features
            amenities: Property amenities
            property_type: Property type
            address: Address object
            neighborhood: Neighborhood object
            location_context: Location context from Wikipedia
            neighborhood_context: Neighborhood context from Wikipedia
            nearby_poi: Nearby points of interest
            
        Returns:
            Combined enriched search text
        """
        text_parts = []
        
        # Add basic property info
        if property_type:
            text_parts.append(property_type)
        if description:
            text_parts.append(description)
        
        # Add features and amenities
        if features:
            text_parts.extend(features)
        if amenities:
            text_parts.extend(amenities)
        
        # Add address info
        if address:
            if address.street:
                text_parts.append(address.street)
            if address.city:
                text_parts.append(address.city)
            if address.state:
                text_parts.append(address.state)
        
        # Add neighborhood info
        if neighborhood and neighborhood.name:
            text_parts.append(neighborhood.name)
        
        # Add Wikipedia location context
        if location_context:
            if location_context.wikipedia_title:
                text_parts.append(location_context.wikipedia_title)
            if location_context.location_summary:
                text_parts.append(location_context.location_summary)
            if location_context.historical_significance:
                text_parts.append(location_context.historical_significance)
            if location_context.key_topics:
                text_parts.extend(location_context.key_topics)
            if location_context.cultural_features:
                text_parts.extend(location_context.cultural_features)
            if location_context.recreational_features:
                text_parts.extend(location_context.recreational_features)
        
        # Add Wikipedia neighborhood context
        if neighborhood_context:
            if neighborhood_context.wikipedia_title:
                text_parts.append(neighborhood_context.wikipedia_title)
            if neighborhood_context.description:
                text_parts.append(neighborhood_context.description)
            if neighborhood_context.history:
                text_parts.append(neighborhood_context.history)
            if neighborhood_context.character:
                text_parts.append(neighborhood_context.character)
            if neighborhood_context.key_topics:
                text_parts.extend(neighborhood_context.key_topics)
        
        # Add nearby POI info
        if nearby_poi:
            for poi in nearby_poi:
                text_parts.append(poi.name)
                if poi.description:
                    text_parts.append(poi.description)
                if poi.key_topics:
                    text_parts.extend(poi.key_topics)
        
        # Clean and combine
        cleaned_parts = []
        for part in text_parts:
            if part:
                cleaned = self.clean_text(str(part))
                if cleaned:
                    cleaned_parts.append(cleaned)
        
        return " ".join(cleaned_parts) if cleaned_parts else None
    
    def _parse_date(self, value: Any) -> Optional[datetime]:
        """
        Parse date field from various formats.
        
        Args:
            value: Date value (could be datetime, string, or None)
            
        Returns:
            datetime object or None
        """
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return value
        
        # Try to parse string dates
        if isinstance(value, str):
            try:
                # Try ISO format first
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                pass
            
            # Try other common formats
            for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"]:
                try:
                    return datetime.strptime(value, fmt)
                except:
                    continue
        
        return None