"""Neighborhood document builder for search pipeline.

Transforms neighborhood DataFrames into NeighborhoodDocument models for Elasticsearch indexing.
Creates properly nested documents matching the Elasticsearch mappings exactly.
"""

import logging
from typing import List, Dict, Any, Optional
from pyspark.sql import DataFrame

from search_pipeline.builders.base import BaseDocumentBuilder
from search_pipeline.models.documents import (
    NeighborhoodDocument,
    AddressModel,
    LocationContextModel,
    NeighborhoodContextModel,
    NearbyPOIModel,
    LocationScoresModel,
    LandmarkModel
)

logger = logging.getLogger(__name__)


class NeighborhoodDocumentBuilder(BaseDocumentBuilder):
    """
    Builder for transforming neighborhood DataFrames into NeighborhoodDocument models.
    
    Creates properly nested documents matching Elasticsearch mappings exactly.
    Note: Property statistics will be calculated using Elasticsearch aggregations
    at query time, not pre-calculated during indexing.
    """
    
    def transform(self, df: DataFrame) -> List[NeighborhoodDocument]:
        """
        Transform neighborhood DataFrame into NeighborhoodDocument models.
        
        Args:
            df: Spark DataFrame containing neighborhood data
            
        Returns:
            List of NeighborhoodDocument models
            
        Raises:
            ValueError: If required fields are missing
        """
        # Validate field mapping requirements first
        self.validate_field_mapping_requirements(df, "neighborhood")
        
        # Apply field name standardization
        df = self.apply_field_mapping(df, "neighborhood")
        
        # Validate required fields after mapping
        required_fields = ["neighborhood_id", "name"]
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
                    self.logger.error(f"Error processing neighborhood row: {e}")
                    continue
            
            self.logger.info(f"Transformed {len(documents)} neighborhood documents")
            
        except Exception as e:
            self.logger.error(f"Error transforming neighborhood DataFrame: {e}")
            raise ValueError(f"Failed to transform neighborhoods: {e}")
        
        return documents
    
    def _build_document(self, row: Dict[str, Any]) -> NeighborhoodDocument:
        """
        Build a NeighborhoodDocument from a DataFrame row.
        
        Args:
            row: Dictionary representing a neighborhood row
            
        Returns:
            NeighborhoodDocument model with nested structure
        """
        # Extract required fields
        neighborhood_id = str(self.extract_field(row, "neighborhood_id"))
        name = self.clean_text(self.extract_field(row, "name", ""))
        
        # Use neighborhood_id as listing_id for base document
        listing_id = neighborhood_id
        
        # Build nested address object
        address = self._build_address(row)
        
        # Extract boundaries (could be JSON string or dict)
        boundaries = self._extract_boundaries(row)
        
        # Extract scores if available
        walkability_score = self._extract_score(row, "walkability_score")
        transit_score = self._extract_score(row, "transit_score")
        school_rating = self.extract_field(row, "school_rating")
        
        # Extract description
        description = self.clean_text(self.extract_field(row, "description"))
        
        # Build Wikipedia enrichment fields
        location_context = self._build_location_context(row)
        neighborhood_context = self._build_neighborhood_context(row)
        nearby_poi = self._build_nearby_poi(row)
        location_scores = self._build_location_scores(row)
        
        # Generate enriched search text
        enriched_search_text = self._generate_enriched_search_text(
            name=name,
            description=description,
            address=address,
            location_context=location_context,
            neighborhood_context=neighborhood_context,
            nearby_poi=nearby_poi,
        )
        
        # Extract embedding fields
        embedding = self.extract_field(row, "embedding")
        embedding_model = self.extract_field(row, "embedding_model")
        embedding_dimension = self.extract_field(row, "embedding_dimension")
        embedded_at = self._parse_date(self.extract_field(row, "embedded_at"))
        
        # Create document
        return NeighborhoodDocument(
            listing_id=listing_id,
            neighborhood_id=neighborhood_id,
            name=name,
            address=address,
            boundaries=boundaries,
            walkability_score=walkability_score,
            transit_score=transit_score,
            school_rating=school_rating,
            description=description,
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
        """Build nested address object for neighborhood location."""
        # Extract location fields
        city = self.clean_text(self.extract_field(row, "city"))
        state = self.clean_text(self.extract_field(row, "state"))
        
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
        if any([city, state, location]):
            return AddressModel(
                street=None,  # Neighborhoods don't have street addresses
                city=city,
                state=state,
                zip_code=None,
                location=location
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
        name: str,
        description: Optional[str] = None,
        address: Optional[AddressModel] = None,
        location_context: Optional[LocationContextModel] = None,
        neighborhood_context: Optional[NeighborhoodContextModel] = None,
        nearby_poi: List[NearbyPOIModel] = None,
    ) -> Optional[str]:
        """
        Generate enriched search text combining neighborhood and Wikipedia data.
        
        Args:
            name: Neighborhood name
            description: Neighborhood description
            address: Address object
            location_context: Location context from Wikipedia
            neighborhood_context: Neighborhood context from Wikipedia
            nearby_poi: Nearby points of interest
            
        Returns:
            Combined enriched search text
        """
        text_parts = []
        
        # Add basic neighborhood info
        text_parts.append(name)
        if description:
            text_parts.append(description)
        
        # Add address info
        if address:
            if address.city:
                text_parts.append(address.city)
            if address.state:
                text_parts.append(address.state)
        
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
            if neighborhood_context.notable_residents:
                text_parts.extend(neighborhood_context.notable_residents)
            if neighborhood_context.architectural_style:
                text_parts.extend(neighborhood_context.architectural_style)
        
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
    
    def _extract_score(self, row: Dict[str, Any], field_name: str) -> Optional[int]:
        """
        Extract and validate a score field.
        
        Args:
            row: Row dictionary
            field_name: Name of the score field
            
        Returns:
            Score value or None
        """
        score = self.extract_field(row, field_name)
        
        if score is None:
            return None
        
        try:
            score_int = int(score)
            # Ensure score is in valid range
            if 0 <= score_int <= 100:
                return score_int
            else:
                self.logger.warning(f"Score {field_name} out of range: {score_int}")
                return None
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid score value for {field_name}: {score}")
            return None
    
    def _extract_boundaries(self, row: Dict[str, Any]) -> Optional[str]:
        """
        Extract boundaries field as JSON string.
        
        Args:
            row: Row dictionary
            
        Returns:
            Boundaries as JSON string or None
        """
        boundaries = self.extract_field(row, "boundaries")
        
        if boundaries is None:
            return None
        
        # If it's already a string, return it
        if isinstance(boundaries, str):
            return boundaries
        
        # If it's a dict or list, convert to JSON string
        try:
            import json
            return json.dumps(boundaries)
        except Exception as e:
            self.logger.warning(f"Could not serialize boundaries: {e}")
            return None