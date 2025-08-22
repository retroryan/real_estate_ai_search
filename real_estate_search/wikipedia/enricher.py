"""
Simple Wikipedia enrichment with proper data structure.
"""

from typing import Dict, List, Optional, Any
import logging

from .extractor import WikipediaExtractor

logger = logging.getLogger(__name__)


class PropertyEnricher:
    """Simple Wikipedia enrichment without caching."""
    
    def __init__(self):
        """Initialize the enricher."""
        self.extractor = WikipediaExtractor()
        self._location_cache = {}  # Cache for batch operations only
    
    def get_location_wikipedia_data(self, city: str, state: str) -> Optional[Dict[str, Any]]:
        """Get Wikipedia data for a location."""
        try:
            # Convert 2-letter state code to full name if needed
            state_map = {
                'CA': 'California', 'UT': 'Utah', 'NY': 'New York', 'TX': 'Texas',
                'FL': 'Florida', 'CO': 'Colorado', 'WA': 'Washington', 'OR': 'Oregon',
                'NV': 'Nevada', 'AZ': 'Arizona', 'IL': 'Illinois', 'MA': 'Massachusetts'
            }
            if len(state) == 2:
                state = state_map.get(state.upper(), state)
            
            # Query Wikipedia database once
            articles = self.extractor.get_articles_for_location(city, state)
            
            if not articles:
                logger.debug(f"No Wikipedia articles found for {city}, {state}")
                return None
            
            # Take the most relevant article
            article = articles[0]
            
            # Extract POIs from articles
            pois = self.extractor.extract_pois_from_articles([article])
            
            # Return formatted data matching mapping schema
            return {
                'page_id': article.page_id,
                'title': article.title,
                'summary': article.short_summary or '',
                'long_summary': article.long_summary or '',
                'key_topics': article.key_topics if article.key_topics else [],
                'pois': pois
            }
        except Exception as e:
            logger.error(f"Error getting Wikipedia data for {city}, {state}: {e}")
            return None
    
    def enrich_property(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a single property with Wikipedia data."""
        # Start with property data
        doc = property_data.copy()
        
        # Extract location
        address = property_data.get('address', {})
        city = address.get('city')
        state = address.get('state')
        neighborhood = property_data.get('neighborhood', {})
        neighborhood_name = neighborhood.get('name') if isinstance(neighborhood, dict) else None
        
        if not city or not state:
            return doc
        
        # Get Wikipedia data for location
        wiki_data = self.get_location_wikipedia_data(city, state)
        
        # Try to get neighborhood-specific Wikipedia data
        neighborhood_wiki_data = None
        if neighborhood_name:
            try:
                neighborhood_articles = self.extractor.get_articles_by_title_pattern(
                    pattern=neighborhood_name,
                    city=city,
                    state=state,
                    limit=1
                )
                if neighborhood_articles:
                    neighborhood_article = neighborhood_articles[0]
                    neighborhood_wiki_data = {
                        'page_id': neighborhood_article.page_id,
                        'title': neighborhood_article.title,
                        'summary': neighborhood_article.short_summary,
                        'key_topics': neighborhood_article.key_topics.split(',') if neighborhood_article.key_topics else []
                    }
                    logger.debug(f"Found neighborhood Wikipedia article: {neighborhood_article.title}")
            except Exception as e:
                logger.warning(f"Error getting neighborhood Wikipedia data for {neighborhood_name}: {e}")
        
        # Add Wikipedia fields matching the mapping schema
        if wiki_data:
            # Add location context
            doc['location_context'] = {
                'wikipedia_page_id': str(wiki_data['page_id']),
                'wikipedia_title': wiki_data['title'],
                'location_summary': wiki_data['summary'],
                'key_topics': wiki_data['key_topics']
            }
            
            # Add POIs as nested documents
            if wiki_data.get('pois'):
                doc['nearby_poi'] = [{
                    'name': poi.name,
                    'wikipedia_page_id': str(poi.wikipedia_page_id) if poi.wikipedia_page_id else None,
                    'category': poi.category.value if hasattr(poi.category, 'value') else poi.category,
                    'significance_score': poi.significance_score,
                    'description': poi.description,
                    'key_topics': poi.key_topics if poi.key_topics else []
                } for poi in wiki_data['pois'][:10]]  # Limit to 10 POIs
        
        # Add neighborhood context if available
        if neighborhood_wiki_data:
            doc['neighborhood_context'] = {
                'wikipedia_page_id': str(neighborhood_wiki_data['page_id']),
                'wikipedia_title': neighborhood_wiki_data['title'],
                'description': neighborhood_wiki_data['summary'],
                'key_topics': neighborhood_wiki_data['key_topics']
            }
        
        # Create enriched search text combining all sources
        search_text_parts = [
            doc.get('description', ''),
            wiki_data.get('summary', '') if wiki_data else '',
            ' '.join(wiki_data.get('key_topics', [])) if wiki_data else '',
            ' '.join([poi.name for poi in wiki_data.get('pois', [])[:5]]) if wiki_data and wiki_data.get('pois') else '',
            neighborhood_wiki_data.get('summary', '') if neighborhood_wiki_data else '',
            ' '.join(neighborhood_wiki_data.get('key_topics', [])) if neighborhood_wiki_data else ''
        ]
        doc['enriched_search_text'] = ' '.join(filter(None, search_text_parts)).lower()
        
        return doc
    
    def enrich_properties(self, properties: List[Dict[str, Any]]) -> List[Dict]:
        """Batch enrich properties with Wikipedia data."""
        # Pre-load all unique locations for batch efficiency
        unique_locations = set()
        for prop in properties:
            address = prop.get('address', {})
            city = address.get('city')
            state = address.get('state')
            if city and state:
                unique_locations.add((city, state))
        
        # Batch load Wikipedia data for all unique locations
        logger.info(f"Pre-loading Wikipedia data for {len(unique_locations)} unique locations")
        for city, state in unique_locations:
            cache_key = f"{city}_{state}"
            if cache_key not in self._location_cache:
                self._location_cache[cache_key] = self.get_location_wikipedia_data(city, state)
        
        # Now enrich all properties using cached data
        enriched = []
        stats = {'total': len(properties), 'with_location': 0, 'with_neighborhood': 0, 'with_pois': 0}
        
        for prop in properties:
            enriched_doc = self._enrich_with_cache(prop)
            enriched.append(enriched_doc)
            
            # Track coverage stats
            if 'location_context' in enriched_doc:
                stats['with_location'] += 1
            if 'neighborhood_context' in enriched_doc:
                stats['with_neighborhood'] += 1
            if 'nearby_poi' in enriched_doc:
                stats['with_pois'] += 1
        
        # Log coverage statistics
        logger.info(f"Enrichment complete: {stats['with_location']}/{stats['total']} with location context, "
                   f"{stats['with_neighborhood']}/{stats['total']} with neighborhood context, "
                   f"{stats['with_pois']}/{stats['total']} with POIs")
        
        # Clear cache after batch operation
        self._location_cache.clear()
        
        return enriched
    
    def _enrich_with_cache(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich property using cached Wikipedia data."""
        doc = property_data.copy()
        
        # Extract location
        address = property_data.get('address', {})
        city = address.get('city')
        state = address.get('state')
        neighborhood = property_data.get('neighborhood', {})
        neighborhood_name = neighborhood.get('name') if isinstance(neighborhood, dict) else None
        
        if not city or not state:
            return doc
        
        # Get city-level Wikipedia data from cache
        cache_key = f"{city}_{state}"
        wiki_data = self._location_cache.get(cache_key)
        
        # Try to get neighborhood-specific Wikipedia data if available
        neighborhood_wiki_data = None
        if neighborhood_name:
            try:
                # Search for neighborhood-specific Wikipedia articles
                neighborhood_articles = self.extractor.get_articles_by_title_pattern(
                    pattern=neighborhood_name,
                    city=city,
                    state=state,
                    limit=1
                )
                if neighborhood_articles:
                    neighborhood_article = neighborhood_articles[0]
                    neighborhood_wiki_data = {
                        'page_id': neighborhood_article.page_id,
                        'title': neighborhood_article.title,
                        'summary': neighborhood_article.short_summary,
                        'key_topics': neighborhood_article.key_topics.split(',') if neighborhood_article.key_topics else []
                    }
                    logger.debug(f"Found neighborhood Wikipedia article: {neighborhood_article.title}")
            except Exception as e:
                logger.warning(f"Error getting neighborhood Wikipedia data for {neighborhood_name}: {e}")
        
        # Add Wikipedia fields matching the mapping schema
        if wiki_data:
            # Add location context
            doc['location_context'] = {
                'wikipedia_page_id': str(wiki_data['page_id']),
                'wikipedia_title': wiki_data['title'],
                'location_summary': wiki_data['summary'],
                'key_topics': wiki_data['key_topics']
            }
            
            # Add POIs as nested documents
            if wiki_data.get('pois'):
                doc['nearby_poi'] = [{
                    'name': poi.name,
                    'wikipedia_page_id': str(poi.wikipedia_page_id) if poi.wikipedia_page_id else None,
                    'category': poi.category.value if hasattr(poi.category, 'value') else poi.category,
                    'significance_score': poi.significance_score,
                    'description': poi.description,
                    'key_topics': poi.key_topics if poi.key_topics else []
                } for poi in wiki_data['pois'][:10]]  # Limit to 10 POIs
        
        # Add neighborhood context if available
        if neighborhood_wiki_data:
            doc['neighborhood_context'] = {
                'wikipedia_page_id': str(neighborhood_wiki_data['page_id']),
                'wikipedia_title': neighborhood_wiki_data['title'],
                'description': neighborhood_wiki_data['summary'],
                'key_topics': neighborhood_wiki_data['key_topics']
            }
        
        # Create enriched search text combining all sources
        search_text_parts = [
            doc.get('description', ''),
            wiki_data.get('summary', '') if wiki_data else '',
            ' '.join(wiki_data.get('key_topics', [])) if wiki_data else '',
            ' '.join([poi.name for poi in wiki_data.get('pois', [])[:5]]) if wiki_data and wiki_data.get('pois') else '',
            neighborhood_wiki_data.get('summary', '') if neighborhood_wiki_data else '',
            ' '.join(neighborhood_wiki_data.get('key_topics', [])) if neighborhood_wiki_data else ''
        ]
        doc['enriched_search_text'] = ' '.join(filter(None, search_text_parts)).lower()
        
        return doc