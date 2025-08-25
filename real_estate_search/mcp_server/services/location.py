"""
Location service for geocoding and location-based operations.
Clean async implementation for location intelligence.
"""

import logging
import asyncio
import math
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from models import (
    GeoLocation, POIInfo, POICategory,
    NeighborhoodContext, LocationHistory
)
from config.settings import settings

logger = logging.getLogger(__name__)


class LocationService:
    """Service for location-based operations and analysis."""
    
    def __init__(self):
        """Initialize location service."""
        self.poi_cache: Dict[str, List[POIInfo]] = {}
        
    async def geocode_address(self, address: str) -> Optional[GeoLocation]:
        """Geocode an address to coordinates."""
        # In production, would use actual geocoding service
        # For demo, return simulated coordinates based on city
        await asyncio.sleep(0.05)  # Simulate API call
        
        city_coords = {
            "austin": (30.2672, -97.7431),
            "dallas": (32.7767, -96.7970),
            "houston": (29.7604, -95.3698),
            "san antonio": (29.4241, -98.4936),
            "fort worth": (32.7555, -97.3308)
        }
        
        address_lower = address.lower()
        for city, coords in city_coords.items():
            if city in address_lower:
                # Add slight variation
                import random
                lat = coords[0] + random.uniform(-0.05, 0.05)
                lon = coords[1] + random.uniform(-0.05, 0.05)
                return GeoLocation(lat=lat, lon=lon)
        
        # Default coordinates
        return GeoLocation(lat=30.2672, lon=-97.7431)
    
    async def reverse_geocode(self, location: GeoLocation) -> Optional[str]:
        """Reverse geocode coordinates to address."""
        # Simulated reverse geocoding
        await asyncio.sleep(0.05)
        
        # Determine nearest city based on coordinates
        if 29 < location.lat < 31 and -98 < location.lon < -97:
            return "Austin, TX"
        elif 32 < location.lat < 33 and -97 < location.lon < -96:
            return "Dallas, TX"
        elif 29 < location.lat < 30 and -96 < location.lon < -95:
            return "Houston, TX"
        else:
            return "Texas"
    
    async def find_nearby_pois(
        self,
        center: GeoLocation,
        radius_miles: float = 2.0,
        categories: Optional[List[POICategory]] = None
    ) -> List[POIInfo]:
        """Find points of interest near a location."""
        cache_key = f"{center.lat:.4f}_{center.lon:.4f}_{radius_miles}"
        
        # Check cache
        if cache_key in self.poi_cache:
            pois = self.poi_cache[cache_key]
        else:
            # Generate POIs (in production, would query actual POI service)
            pois = await self._generate_pois(center, radius_miles)
            self.poi_cache[cache_key] = pois
        
        # Filter by categories if specified
        if categories:
            pois = [poi for poi in pois if poi.category in categories]
        
        # Sort by distance
        pois.sort(key=lambda x: x.distance_miles or float('inf'))
        
        return pois[:settings.enrichment.max_pois]
    
    async def calculate_walkability_score(self, location: GeoLocation) -> int:
        """Calculate walkability score for a location."""
        # Find nearby amenities
        pois = await self.find_nearby_pois(location, radius_miles=0.5)
        
        # Count walkable amenities
        walkable_categories = [
            POICategory.shopping,
            POICategory.dining,
            POICategory.entertainment,
            POICategory.recreation
        ]
        
        walkable_count = sum(
            1 for poi in pois
            if poi.category in walkable_categories
        )
        
        # Calculate score (simplified)
        if walkable_count >= 20:
            score = 95
        elif walkable_count >= 15:
            score = 85
        elif walkable_count >= 10:
            score = 75
        elif walkable_count >= 5:
            score = 60
        elif walkable_count >= 3:
            score = 45
        else:
            score = 30
        
        return score
    
    async def calculate_commute_time(
        self,
        origin: GeoLocation,
        destination: GeoLocation,
        mode: str = "driving"
    ) -> Optional[int]:
        """Calculate commute time between two locations."""
        # Calculate distance
        distance = self.calculate_distance(origin, destination)
        
        # Estimate time based on mode (simplified)
        if mode == "driving":
            # Assume average 30 mph in city
            time_minutes = int((distance / 30) * 60)
        elif mode == "transit":
            # Assume average 20 mph with stops
            time_minutes = int((distance / 20) * 60) + 10  # Add transfer time
        elif mode == "cycling":
            # Assume average 12 mph
            time_minutes = int((distance / 12) * 60)
        elif mode == "walking":
            # Assume average 3 mph
            time_minutes = int((distance / 3) * 60)
        else:
            time_minutes = None
        
        return time_minutes
    
    async def get_demographic_data(self, location: GeoLocation) -> Dict[str, Any]:
        """Get demographic data for a location."""
        # Simulated demographic data
        await asyncio.sleep(0.05)
        
        return {
            "population": 50000,
            "median_age": 34,
            "median_income": 75000,
            "education": {
                "bachelors_or_higher": 45,
                "high_school": 90
            },
            "employment_rate": 96,
            "diversity_index": 0.65
        }
    
    async def get_school_data(self, location: GeoLocation) -> List[Dict[str, Any]]:
        """Get school information for a location."""
        # Simulated school data
        await asyncio.sleep(0.05)
        
        schools = [
            {
                "name": "Lincoln Elementary",
                "type": "elementary",
                "rating": 8.5,
                "distance_miles": 0.5,
                "enrollment": 450
            },
            {
                "name": "Washington Middle School",
                "type": "middle",
                "rating": 7.8,
                "distance_miles": 1.2,
                "enrollment": 800
            },
            {
                "name": "Jefferson High School",
                "type": "high",
                "rating": 8.2,
                "distance_miles": 2.0,
                "enrollment": 1500
            }
        ]
        
        return schools
    
    async def get_safety_data(self, location: GeoLocation) -> Dict[str, Any]:
        """Get safety/crime data for a location."""
        # Simulated safety data
        await asyncio.sleep(0.05)
        
        return {
            "crime_grade": "B+",
            "violent_crime_rate": 2.5,  # Per 1000 residents
            "property_crime_rate": 18.2,  # Per 1000 residents
            "safety_score": 75,
            "trend": "improving"
        }
    
    async def analyze_neighborhood(
        self,
        location: GeoLocation,
        name: str,
        city: str,
        state: str
    ) -> NeighborhoodContext:
        """Perform comprehensive neighborhood analysis."""
        # Run analysis tasks concurrently
        tasks = [
            self.calculate_walkability_score(location),
            self.get_demographic_data(location),
            self.get_school_data(location),
            self.get_safety_data(location),
            self.find_nearby_pois(location, radius_miles=1.0)
        ]
        
        results = await asyncio.gather(*tasks)
        
        walkability = results[0]
        demographics = results[1]
        schools = results[2]
        safety = results[3]
        pois = results[4]
        
        # Calculate transit score (simplified)
        transit_pois = [p for p in pois if p.category == POICategory.transportation]
        transit_score = min(len(transit_pois) * 20, 100)
        
        # Calculate bike score (simplified)
        bike_score = int(walkability * 0.8)
        
        # Get school rating
        school_ratings = [s["rating"] for s in schools]
        avg_school_rating = sum(school_ratings) / len(school_ratings) if school_ratings else 0
        
        return NeighborhoodContext(
            name=name,
            city=city,
            state=state,
            center=location,
            demographics=demographics,
            walkability_score=walkability,
            transit_score=transit_score,
            bike_score=bike_score,
            crime_grade=safety["crime_grade"],
            school_rating=avg_school_rating,
            median_home_price=demographics["median_income"] * 5,  # Rough estimate
            price_trend=2.5  # Simulated growth rate
        )
    
    def calculate_distance(self, loc1: GeoLocation, loc2: GeoLocation) -> float:
        """Calculate distance between two locations in miles using Haversine formula."""
        R = 3959  # Earth's radius in miles
        
        lat1_rad = math.radians(loc1.lat)
        lat2_rad = math.radians(loc2.lat)
        dlat = math.radians(loc2.lat - loc1.lat)
        dlon = math.radians(loc2.lon - loc1.lon)
        
        a = (
            math.sin(dlat / 2) ** 2 +
            math.cos(lat1_rad) * math.cos(lat2_rad) *
            math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return round(distance, 2)
    
    async def _generate_pois(
        self,
        center: GeoLocation,
        radius_miles: float
    ) -> List[POIInfo]:
        """Generate simulated POIs for demo purposes."""
        pois = []
        
        # Define POI templates
        poi_templates = [
            ("Whole Foods Market", POICategory.shopping, "grocery", 4.5),
            ("Target", POICategory.shopping, "retail", 4.2),
            ("Central Park", POICategory.recreation, "park", 4.8),
            ("City Gym", POICategory.recreation, "fitness", 4.3),
            ("Main Street Elementary", POICategory.education, "school", 4.1),
            ("St. Mary's Hospital", POICategory.healthcare, "hospital", 4.4),
            ("Downtown Clinic", POICategory.healthcare, "clinic", 4.0),
            ("Italian Bistro", POICategory.dining, "restaurant", 4.6),
            ("Coffee House", POICategory.dining, "cafe", 4.5),
            ("Movie Theater", POICategory.entertainment, "cinema", 4.2),
            ("City Library", POICategory.cultural, "library", 4.7),
            ("Art Museum", POICategory.cultural, "museum", 4.5),
            ("Bus Station", POICategory.transportation, "transit", 3.8),
            ("Train Station", POICategory.transportation, "transit", 4.0),
            ("City Hall", POICategory.government, "municipal", 4.0)
        ]
        
        # Generate POIs within radius
        import random
        num_pois = min(len(poi_templates), int(radius_miles * 10))
        selected = random.sample(poi_templates, num_pois)
        
        for name, category, subcategory, rating in selected:
            # Random distance within radius
            distance = random.uniform(0.1, radius_miles)
            
            # Random location offset
            angle = random.uniform(0, 2 * math.pi)
            lat_offset = (distance / 69.0) * math.sin(angle)  # 69 miles per degree latitude
            lon_offset = (distance / (69.0 * math.cos(math.radians(center.lat)))) * math.cos(angle)
            
            poi_location = GeoLocation(
                lat=center.lat + lat_offset,
                lon=center.lon + lon_offset
            )
            
            poi = POIInfo(
                name=name,
                category=category,
                subcategory=subcategory,
                location=poi_location,
                distance_miles=distance,
                rating=rating,
                description=f"Popular {subcategory} in the area"
            )
            
            pois.append(poi)
        
        return pois