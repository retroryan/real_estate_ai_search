"""
Wikipedia and location enrichment service.
Async implementation for enriching property data.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import hashlib
import json

from models import (
    Property, GeoLocation, WikipediaContext, POIInfo,
    NeighborhoodContext, LocationHistory, MarketContext,
    EnrichmentBundle, POICategory
)
from config.settings import settings

logger = logging.getLogger(__name__)


class WikipediaEnrichmentService:
    """Service for enriching properties with Wikipedia and location data."""
    
    def __init__(self):
        """Initialize enrichment service."""
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = timedelta(seconds=settings.enrichment.wikipedia_cache_ttl)
        
    async def enrich_property(self, property: Property) -> EnrichmentBundle:
        """Enrich a property with Wikipedia and location data."""
        enrichment = EnrichmentBundle(property_id=property.id)
        
        # Run enrichment tasks concurrently
        tasks = [
            self._enrich_wikipedia(property),
            self._enrich_neighborhood(property),
            self._enrich_pois(property),
            self._enrich_market(property)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Enrichment task {i} failed: {result}")
                continue
                
            if i == 0 and result:  # Wikipedia
                enrichment.wikipedia_context = result
            elif i == 1 and result:  # Neighborhood
                enrichment.neighborhood_context = result
            elif i == 2 and result:  # POIs
                enrichment.nearby_pois = result
            elif i == 3 and result:  # Market
                enrichment.market_context = result
        
        enrichment.enrichment_timestamp = datetime.now().isoformat()
        return enrichment
    
    async def enrich_batch(self, properties: List[Property]) -> List[EnrichmentBundle]:
        """Enrich multiple properties in batch."""
        tasks = [self.enrich_property(prop) for prop in properties]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out errors
        enrichments = []
        for result in results:
            if isinstance(result, EnrichmentBundle):
                enrichments.append(result)
            else:
                logger.warning(f"Batch enrichment failed for property: {result}")
        
        return enrichments
    
    async def _enrich_wikipedia(self, property: Property) -> Optional[WikipediaContext]:
        """Enrich with Wikipedia data for the location."""
        cache_key = f"wiki_{property.address.city}_{property.address.state}"
        
        # Check cache
        cached = self._get_cached(cache_key)
        if cached:
            return WikipediaContext(**cached)
        
        # Simulate Wikipedia API call (in production, would use actual API)
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Generate context based on city
        context = WikipediaContext(
            wikipedia_title=f"{property.address.city}, {property.address.state}",
            wikipedia_url=f"https://en.wikipedia.org/wiki/{property.address.city},_{property.address.state}",
            summary=f"{property.address.city} is a vibrant city in {property.address.state} known for its diverse culture and growing economy.",
            location_summary=f"Located in {property.address.state}, {property.address.city} offers a unique blend of urban amenities and natural beauty.",
            key_topics=["culture", "economy", "education", "recreation"],
            notable_features=["tech hub", "music scene", "outdoor activities"],
            confidence_score=0.85
        )
        
        # Cache result
        self._set_cache(cache_key, context.model_dump())
        
        return context
    
    async def _enrich_neighborhood(self, property: Property) -> Optional[NeighborhoodContext]:
        """Enrich with neighborhood data."""
        # Simulate neighborhood data lookup
        await asyncio.sleep(0.05)
        
        # Generate neighborhood context
        neighborhood = NeighborhoodContext(
            name=f"{property.address.city} Downtown",
            city=property.address.city,
            state=property.address.state,
            center=property.address.location,
            walkability_score=75,
            transit_score=60,
            bike_score=70,
            school_rating=7.5,
            median_home_price=property.price * 1.1,
            price_trend=2.5
        )
        
        return neighborhood
    
    async def _enrich_pois(self, property: Property) -> List[POIInfo]:
        """Enrich with nearby points of interest."""
        if not property.address.location:
            return []
        
        # Simulate POI lookup
        await asyncio.sleep(0.05)
        
        # Generate sample POIs
        pois = [
            POIInfo(
                name="Central Park",
                category=POICategory.recreation,
                subcategory="park",
                location=GeoLocation(
                    lat=property.address.location.lat + 0.01,
                    lon=property.address.location.lon - 0.01
                ),
                distance_miles=0.8,
                description="Large urban park with trails and playgrounds"
            ),
            POIInfo(
                name="Whole Foods Market",
                category=POICategory.shopping,
                subcategory="grocery",
                distance_miles=1.2,
                rating=4.5,
                description="Organic grocery store"
            ),
            POIInfo(
                name="Elementary School",
                category=POICategory.education,
                subcategory="school",
                distance_miles=0.5,
                rating=4.2,
                description="Highly rated public elementary school"
            ),
            POIInfo(
                name="City Medical Center",
                category=POICategory.healthcare,
                subcategory="hospital",
                distance_miles=2.5,
                description="Full-service medical facility"
            ),
            POIInfo(
                name="Downtown Station",
                category=POICategory.transportation,
                subcategory="transit",
                distance_miles=1.8,
                description="Major transit hub"
            )
        ]
        
        # Return top POIs based on settings
        return pois[:settings.enrichment.max_pois]
    
    async def _enrich_market(self, property: Property) -> Optional[MarketContext]:
        """Enrich with market context data."""
        # Simulate market data lookup
        await asyncio.sleep(0.05)
        
        # Generate market context
        market = MarketContext(
            location_name=property.address.city,
            median_price=property.price * 0.95,
            average_price_sqft=property.price / property.square_feet if property.square_feet else None,
            inventory_count=150,
            days_on_market=35,
            price_trend_30d=1.2,
            price_trend_90d=2.8,
            price_trend_1y=5.5,
            buyer_seller_index=0.1,
            forecast_3m="Stable with slight upward trend",
            forecast_1y="Moderate appreciation expected"
        )
        
        return market
    
    async def get_location_history(self, location: GeoLocation, city: str, state: str) -> Optional[LocationHistory]:
        """Get historical information about a location."""
        cache_key = f"history_{city}_{state}"
        
        # Check cache
        cached = self._get_cached(cache_key)
        if cached:
            return LocationHistory(**cached)
        
        # Simulate historical data lookup
        await asyncio.sleep(0.1)
        
        # Generate location history
        history = LocationHistory(
            location=location,
            city=city,
            state=state,
            founded_year=1850,
            historical_events=[
                {"year": 1850, "event": "City founded"},
                {"year": 1900, "event": "Railroad arrives"},
                {"year": 1950, "event": "Major industrial growth"},
                {"year": 2000, "event": "Tech industry boom begins"}
            ],
            notable_landmarks=["Historic Downtown", "City Hall", "Central Park", "Museum District"],
            cultural_significance="Known for music, arts, and innovation",
            economic_history="Evolved from agricultural center to tech hub"
        )
        
        # Cache result
        self._set_cache(cache_key, history.model_dump(mode='json'))
        
        return history
    
    def _get_cache_key(self, *args) -> str:
        """Generate cache key from arguments."""
        key_str = "_".join(str(arg) for arg in args)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self.cache:
            cached_time, value = self.cache[key]
            if datetime.now() - cached_time < self.cache_ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def _set_cache(self, key: str, value: Any):
        """Set cache value with timestamp."""
        self.cache[key] = (datetime.now(), value)