"""Wikipedia document builder for search pipeline.

Transforms Wikipedia DataFrames into WikipediaDocument models for Elasticsearch indexing.
Creates properly nested documents matching the Elasticsearch mappings exactly.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pyspark.sql import DataFrame

from search_pipeline.builders.base import BaseDocumentBuilder
from search_pipeline.models.documents import (
    WikipediaDocument,
    AddressModel,
    LocationContextModel,
    NeighborhoodContextModel,
    NearbyPOIModel,
    LocationScoresModel,
    LandmarkModel
)

logger = logging.getLogger(__name__)


class WikipediaDocumentBuilder(BaseDocumentBuilder):
    """
    Builder for transforming Wikipedia DataFrames into WikipediaDocument models.
    
    This builder maps Wikipedia article data to searchable documents with proper
    nested structure matching Elasticsearch mappings exactly.
    """
    
    def transform(self, df: DataFrame) -> List[WikipediaDocument]:
        """
        Transform Wikipedia DataFrame into WikipediaDocument models.
        
        Args:
            df: Spark DataFrame containing Wikipedia article data
            
        Returns:
            List of WikipediaDocument models
            
        Raises:
            ValueError: If required fields are missing
        """
        # Validate field mapping requirements first
        self.validate_field_mapping_requirements(df, "wikipedia")
        
        # Apply field name standardization
        df = self.apply_field_mapping(df, "wikipedia")
        
        # Validate required fields after mapping
        required_fields = ["page_id", "title"]
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
                    self.logger.error(f"Error processing Wikipedia row: {e}")
                    continue
            
            self.logger.info(f"Transformed {len(documents)} Wikipedia documents")
            
        except Exception as e:
            self.logger.error(f"Error transforming Wikipedia DataFrame: {e}")
            raise ValueError(f"Failed to transform Wikipedia articles: {e}")
        
        return documents
    
    def _build_document(self, row: Dict[str, Any]) -> WikipediaDocument:
        """
        Build a WikipediaDocument from a DataFrame row.
        
        Args:
            row: Dictionary representing a Wikipedia article row
            
        Returns:
            WikipediaDocument model with nested structure
        """
        # Extract required fields
        page_id = self._extract_page_id(row)
        title = self.clean_text(self.extract_field(row, "title", ""))
        
        # Use page_id as listing_id for base document
        listing_id = str(page_id)
        
        # Extract content fields
        url = self.extract_field(row, "url")
        summary = self.clean_text(self.extract_field(row, "summary"))
        content = self.clean_text(self.extract_field(row, "content") or self.extract_field(row, "full_text"))
        
        # Build nested address object for location
        address = self._build_address(row)
        
        # Extract topics
        topics = self._extract_topics(row)
        
        # Parse last modified date
        last_modified = self._parse_date(self.extract_field(row, "last_modified"))
        
        # Build Wikipedia enrichment fields (self-referential)
        location_context = self._build_location_context(row)
        neighborhood_context = self._build_neighborhood_context(row)
        nearby_poi = self._build_nearby_poi(row)
        location_scores = self._build_location_scores(row)
        
        # Generate enriched search text
        enriched_search_text = self._generate_enriched_search_text(
            title=title,
            summary=summary,
            content=content,
            topics=topics,
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
        return WikipediaDocument(
            listing_id=listing_id,
            page_id=page_id,
            title=title,
            url=url,
            summary=summary,
            content=content,
            address=address,
            topics=topics,
            last_modified=last_modified,
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
        """Build nested address object for Wikipedia article location."""
        # Extract location fields
        city = self.clean_text(self.extract_field(row, "city") or self.extract_field(row, "best_city"))
        state = self.clean_text(self.extract_field(row, "state") or self.extract_field(row, "best_state"))
        
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
                street=None,  # Wikipedia articles don't have street addresses
                city=city,
                state=state,
                zip_code=None,
                location=location
            )
        return None
    
    def _build_location_context(self, row: Dict[str, Any]) -> Optional[LocationContextModel]:
        """Build location context from Wikipedia data (self-referential)."""
        # For Wikipedia articles, they can provide their own context
        # Check if we have any location context data
        title = self.clean_text(self.extract_field(row, "title"))
        summary = self.clean_text(self.extract_field(row, "summary"))
        content = self.clean_text(self.extract_field(row, "content"))
        topics = self._extract_topics(row)
        
        if not any([title, summary, content, topics]):
            return None
        
        # Extract fields
        page_id = str(self.extract_field(row, "page_id"))
        
        # For Wikipedia articles, use their own content as location context
        # Limit content length to avoid huge context
        if content and len(content) > 2000:
            content = content[:2000] + "..."
        
        # Extract specific context fields if available
        historical_significance = self.clean_text(self.extract_field(row, "historical_significance"))
        location_type = self.extract_field(row, "location_type") or self._infer_location_type(title, topics)
        
        # Parse features from content or dedicated fields
        cultural_features = self.parse_list_field(self.extract_field(row, "cultural_features"))
        recreational_features = self.parse_list_field(self.extract_field(row, "recreational_features"))
        transportation = self.parse_list_field(self.extract_field(row, "transportation_features"))
        
        return LocationContextModel(
            wikipedia_page_id=page_id,
            wikipedia_title=title,
            location_summary=summary,
            historical_significance=historical_significance or content,
            key_topics=topics,
            landmarks=[],  # Will be populated by enrichment pipeline
            cultural_features=cultural_features,
            recreational_features=recreational_features,
            transportation=transportation,
            location_type=location_type,
            confidence_score=1.0  # Self-referential has high confidence
        )
    
    def _build_neighborhood_context(self, row: Dict[str, Any]) -> Optional[NeighborhoodContextModel]:
        """Build neighborhood context from Wikipedia data."""
        # Check if this is a neighborhood-related article
        title = self.clean_text(self.extract_field(row, "title"))
        topics = self._extract_topics(row)
        
        if not self._is_neighborhood_article(title, topics):
            return None
        
        # For neighborhood articles, use their content as neighborhood context
        page_id = str(self.extract_field(row, "page_id"))
        summary = self.clean_text(self.extract_field(row, "summary"))
        content = self.clean_text(self.extract_field(row, "content"))
        
        # Limit content length
        if content and len(content) > 2000:
            content = content[:2000] + "..."
        
        # Extract specific neighborhood fields if available
        history = self.clean_text(self.extract_field(row, "neighborhood_history")) or content
        character = self.clean_text(self.extract_field(row, "neighborhood_character"))
        notable_residents = self.parse_list_field(self.extract_field(row, "notable_residents"))
        architectural_style = self.parse_list_field(self.extract_field(row, "architectural_style"))
        establishment_year = self.extract_field(row, "establishment_year")
        
        return NeighborhoodContextModel(
            wikipedia_page_id=page_id,
            wikipedia_title=title,
            description=summary,
            history=history,
            character=character,
            notable_residents=notable_residents,
            architectural_style=architectural_style,
            establishment_year=establishment_year,
            gentrification_index=None,
            diversity_score=None,
            key_topics=topics
        )
    
    def _build_nearby_poi(self, row: Dict[str, Any]) -> List[NearbyPOIModel]:
        """Build nearby POI list from row data."""
        # This would typically come from a nested structure or array field
        # For now, return empty list - this will be populated by enrichment pipeline
        return []
    
    def _build_location_scores(self, row: Dict[str, Any]) -> Optional[LocationScoresModel]:
        """Build location scores object."""
        # Extract score fields if available
        cultural_richness = self.extract_field(row, "cultural_richness")
        historical_importance = self.extract_field(row, "historical_importance")
        tourist_appeal = self.extract_field(row, "tourist_appeal")
        
        # Infer scores from Wikipedia article characteristics
        if not any([cultural_richness, historical_importance, tourist_appeal]):
            topics = self._extract_topics(row)
            title = self.extract_field(row, "title", "")
            
            # Basic inference based on article type
            if any(keyword in title.lower() for keyword in ["museum", "theater", "gallery", "cultural"]):
                cultural_richness = 0.8
            if any(keyword in title.lower() for keyword in ["historic", "historical", "founded", "built"]):
                historical_importance = 0.7
            if any(keyword in title.lower() for keyword in ["park", "attraction", "landmark", "monument"]):
                tourist_appeal = 0.6
        
        # Only create scores object if we have some data
        local_amenities = self.extract_field(row, "local_amenities")
        overall_desirability = self.extract_field(row, "overall_desirability")
        
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
        title: str,
        summary: Optional[str] = None,
        content: Optional[str] = None,
        topics: List[str] = None,
        address: Optional[AddressModel] = None,
        location_context: Optional[LocationContextModel] = None,
        neighborhood_context: Optional[NeighborhoodContextModel] = None,
        nearby_poi: List[NearbyPOIModel] = None,
    ) -> Optional[str]:
        """
        Generate enriched search text combining Wikipedia article and context data.
        
        Args:
            title: Article title
            summary: Article summary
            content: Article content (limited length)
            topics: Article topics
            address: Address object
            location_context: Location context
            neighborhood_context: Neighborhood context
            nearby_poi: Nearby points of interest
            
        Returns:
            Combined enriched search text
        """
        text_parts = []
        
        # Add basic article info
        text_parts.append(title)
        if summary:
            text_parts.append(summary)
        
        # Add limited content
        if content:
            # Limit content length to avoid huge search text
            if len(content) > 3000:
                content = content[:3000] + "..."
            text_parts.append(content)
        
        # Add topics
        if topics:
            text_parts.extend(topics)
        
        # Add address info
        if address:
            if address.city:
                text_parts.append(address.city)
            if address.state:
                text_parts.append(address.state)
        
        # Add location context
        if location_context:
            if location_context.key_topics:
                text_parts.extend(location_context.key_topics)
            if location_context.cultural_features:
                text_parts.extend(location_context.cultural_features)
            if location_context.recreational_features:
                text_parts.extend(location_context.recreational_features)
        
        # Add neighborhood context
        if neighborhood_context:
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
    
    def _extract_page_id(self, row: Dict[str, Any]) -> int:
        """
        Extract and validate page ID.
        
        Args:
            row: Row dictionary
            
        Returns:
            Page ID as integer
            
        Raises:
            ValueError: If page_id is invalid
        """
        page_id = self.extract_field(row, "page_id")
        
        if page_id is None:
            raise ValueError("Missing required field: page_id")
        
        try:
            return int(page_id)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid page_id: {page_id}") from e
    
    def _extract_topics(self, row: Dict[str, Any]) -> List[str]:
        """
        Extract topics from various possible fields.
        
        Args:
            row: Row dictionary
            
        Returns:
            List of topics
        """
        # Try different field names for topics
        topics = (
            self.extract_field(row, "topics") or
            self.extract_field(row, "categories") or
            self.extract_field(row, "key_topics")
        )
        
        if topics is None:
            return []
        
        # Parse as list
        return self.parse_list_field(topics)
    
    def _infer_location_type(self, title: str, topics: List[str]) -> Optional[str]:
        """Infer location type from title and topics."""
        title_lower = title.lower()
        all_topics = " ".join(topics).lower() if topics else ""
        
        if any(keyword in title_lower for keyword in ["park", "garden", "reserve"]):
            return "park"
        elif any(keyword in title_lower for keyword in ["museum", "gallery"]):
            return "cultural"
        elif any(keyword in title_lower for keyword in ["school", "university", "college"]):
            return "educational"
        elif any(keyword in title_lower for keyword in ["church", "cathedral", "temple"]):
            return "religious"
        elif any(keyword in title_lower for keyword in ["neighborhood", "district"]):
            return "neighborhood"
        elif any(keyword in title_lower for keyword in ["building", "tower", "center"]):
            return "building"
        elif any(keyword in all_topics for keyword in ["geography", "places"]):
            return "geographic"
        else:
            return "general"
    
    def _is_neighborhood_article(self, title: str, topics: List[str]) -> bool:
        """Check if this is a neighborhood-related article."""
        title_lower = title.lower()
        all_topics = " ".join(topics).lower() if topics else ""
        
        neighborhood_keywords = [
            "neighborhood", "neighbourhood", "district", "area", "quarter",
            "community", "village", "suburb", "ward", "precinct"
        ]
        
        return any(keyword in title_lower for keyword in neighborhood_keywords) or \
               any(keyword in all_topics for keyword in neighborhood_keywords)
    
    def _parse_date(self, value: Any) -> Optional[datetime]:
        """
        Parse date field from various formats.
        
        Args:
            value: Date value
            
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