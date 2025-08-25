"""
Service for enriching properties with Wikipedia data using constructor injection.
All enrichment business logic lives here.
"""

from typing import Dict, Any, List, Optional
import logging

from repositories.wikipedia_repository import WikipediaRepository
from wikipedia.models import WikipediaArticle, WikipediaPOI

logger = logging.getLogger(__name__)


class EnrichmentService:
    """
    Service for enriching property data with Wikipedia context.
    All dependencies injected through constructor.
    """
    
    def __init__(self, wikipedia_repository: WikipediaRepository):
        """
        Initialize service with Wikipedia repository.
        
        Args:
            wikipedia_repository: Repository for Wikipedia data access
        """
        self.wikipedia_repository = wikipedia_repository
        logger.info("Enrichment service initialized")
    
    def enrich_property(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a single property with Wikipedia data.
        
        Args:
            property_data: Property document to enrich
            
        Returns:
            Enriched property document
        """
        # Start with original data
        enriched = property_data.copy()
        
        # Extract location information
        address = property_data.get('address', {})
        city = address.get('city')
        state = address.get('state')
        
        if not city or not state:
            logger.debug(f"No city/state for property {property_data.get('listing_id')}")
            return enriched
        
        # Get Wikipedia data for the location
        wiki_data = self._get_location_wikipedia_data(city, state)
        
        if wiki_data:
            # Add location context
            enriched['location_context'] = {
                'wikipedia_page_id': str(wiki_data['page_id']),
                'wikipedia_title': wiki_data['title'],
                'location_summary': wiki_data['summary'],
                'key_topics': wiki_data['key_topics']
            }
            
            # Add POIs as nested documents
            if wiki_data.get('pois'):
                enriched['nearby_poi'] = [
                    self._format_poi_for_index(poi)
                    for poi in wiki_data['pois'][:10]  # Limit to 10 POIs
                ]
        
        # Try to get neighborhood-specific Wikipedia data
        neighborhood = property_data.get('neighborhood', {})
        neighborhood_name = neighborhood.get('name') if isinstance(neighborhood, dict) else None
        
        if neighborhood_name:
            neighborhood_wiki_data = self._get_neighborhood_wikipedia_data(
                neighborhood_name, city, state
            )
            
            if neighborhood_wiki_data:
                enriched['neighborhood_context'] = {
                    'wikipedia_page_id': str(neighborhood_wiki_data['page_id']),
                    'wikipedia_title': neighborhood_wiki_data['title'],
                    'description': neighborhood_wiki_data['summary'],
                    'key_topics': neighborhood_wiki_data['key_topics']
                }
        
        # Create enriched search text
        enriched['enriched_search_text'] = self._create_search_text(
            property_data,
            wiki_data,
            neighborhood_wiki_data if neighborhood_name else None
        )
        
        logger.debug(f"Enriched property {property_data.get('listing_id')}")
        return enriched
    
    def enrich_properties(self, properties: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Batch enrich multiple properties.
        
        Args:
            properties: List of property documents
            
        Returns:
            List of enriched property documents
        """
        enriched_properties = []
        stats = {
            'total': len(properties),
            'with_location': 0,
            'with_neighborhood': 0,
            'with_pois': 0
        }
        
        for prop in properties:
            enriched = self.enrich_property(prop)
            enriched_properties.append(enriched)
            
            # Track enrichment statistics
            if 'location_context' in enriched:
                stats['with_location'] += 1
            if 'neighborhood_context' in enriched:
                stats['with_neighborhood'] += 1
            if 'nearby_poi' in enriched:
                stats['with_pois'] += 1
        
        logger.info(
            f"Enriched {stats['total']} properties: "
            f"{stats['with_location']} with location, "
            f"{stats['with_neighborhood']} with neighborhood, "
            f"{stats['with_pois']} with POIs"
        )
        
        return enriched_properties
    
    def _get_location_wikipedia_data(self, city: str, state: str) -> Optional[Dict[str, Any]]:
        """
        Get Wikipedia data for a location.
        
        Args:
            city: City name
            state: State name or code
            
        Returns:
            Wikipedia data dictionary or None
        """
        # Get articles for the location
        articles = self.wikipedia_repository.get_articles_for_location(city, state, limit=5)
        
        if not articles:
            logger.debug(f"No Wikipedia articles found for {city}, {state}")
            return None
        
        # Use the most relevant article
        article = articles[0]
        
        # Extract POIs from articles
        pois = self.wikipedia_repository.extract_pois_from_articles(articles)
        
        return {
            'page_id': article.page_id,
            'title': article.title,
            'summary': article.short_summary or '',
            'long_summary': article.long_summary or '',
            'key_topics': article.key_topics or [],
            'pois': pois
        }
    
    def _get_neighborhood_wikipedia_data(
        self,
        neighborhood: str,
        city: str,
        state: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get Wikipedia data for a specific neighborhood.
        
        Args:
            neighborhood: Neighborhood name
            city: City name
            state: State name or code
            
        Returns:
            Wikipedia data dictionary or None
        """
        # Search for neighborhood-specific articles
        articles = self.wikipedia_repository.get_articles_by_title_pattern(
            pattern=neighborhood,
            city=city,
            state=state,
            limit=1
        )
        
        if not articles:
            return None
        
        article = articles[0]
        
        return {
            'page_id': article.page_id,
            'title': article.title,
            'summary': article.short_summary or '',
            'key_topics': article.key_topics or []
        }
    
    def _format_poi_for_index(self, poi: WikipediaPOI) -> Dict[str, Any]:
        """
        Format a POI for Elasticsearch indexing.
        
        Args:
            poi: WikipediaPOI object
            
        Returns:
            Formatted POI dictionary
        """
        return {
            'name': poi.name,
            'wikipedia_page_id': str(poi.wikipedia_page_id) if poi.wikipedia_page_id else None,
            'category': poi.category.value if hasattr(poi.category, 'value') else str(poi.category),
            'significance_score': poi.significance_score,
            'description': poi.description,
            'key_topics': poi.key_topics or []
        }
    
    def _create_search_text(
        self,
        property_data: Dict[str, Any],
        location_wiki_data: Optional[Dict[str, Any]],
        neighborhood_wiki_data: Optional[Dict[str, Any]]
    ) -> str:
        """
        Create enriched search text combining all sources.
        
        Args:
            property_data: Original property data
            location_wiki_data: Wikipedia data for location
            neighborhood_wiki_data: Wikipedia data for neighborhood
            
        Returns:
            Combined search text
        """
        parts = []
        
        # Add property description
        if property_data.get('description'):
            parts.append(property_data['description'])
        
        # Add location Wikipedia data
        if location_wiki_data:
            if location_wiki_data.get('summary'):
                parts.append(location_wiki_data['summary'])
            if location_wiki_data.get('key_topics'):
                parts.append(' '.join(location_wiki_data['key_topics']))
            if location_wiki_data.get('pois'):
                # POIs are WikipediaPOI objects
                poi_names = [poi.name if hasattr(poi, 'name') else str(poi) 
                            for poi in location_wiki_data['pois'][:5]]
                parts.append(' '.join(poi_names))
        
        # Add neighborhood Wikipedia data
        if neighborhood_wiki_data:
            if neighborhood_wiki_data.get('summary'):
                parts.append(neighborhood_wiki_data['summary'])
            if neighborhood_wiki_data.get('key_topics'):
                parts.append(' '.join(neighborhood_wiki_data['key_topics']))
        
        # Combine and normalize
        return ' '.join(filter(None, parts)).lower()