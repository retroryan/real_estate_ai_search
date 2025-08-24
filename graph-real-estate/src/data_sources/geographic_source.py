"""Geographic data source implementation"""

from typing import List, Dict, Any
import logging

from api_client import APIClientFactory, StatsAPIClient, SystemAPIClient
from src.core.interfaces import IGeographicDataSource


class GeographicFileDataSource(IGeographicDataSource):
    """API-based geographic data source"""
    
    def __init__(self, api_factory: APIClientFactory):
        """
        Initialize geographic data source
        
        Args:
            api_factory: Factory for creating API clients
        """
        self.api_factory = api_factory
        self.stats_client = api_factory.create_stats_client()
        self.system_client = api_factory.create_system_client()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def exists(self) -> bool:
        """Check if data source exists"""
        try:
            health_status = self.system_client.check_readiness()
            return health_status.get('status') == 'ready'
        except Exception as e:
            self.logger.warning(f"API health check failed: {e}")
            return False
    
    def load(self) -> Dict[str, Any]:
        """Load all geographic data"""
        return {
            "states": self.load_states(),
            "counties": self.load_counties(),
            "cities": self.load_cities()
        }
    
    def load_states(self) -> List[Dict[str, Any]]:
        """
        Load state data
        
        Returns:
            List of state dictionaries
        """
        try:
            # Try to get geographic data via API statistics
            # For demo purposes, fall back to default states if API doesn't have geographic endpoints yet
            stats = self.stats_client.get_all_stats()
            
            # Check if geographic data is available in stats
            if hasattr(stats, 'geographic') and stats.geographic:
                geographic_data = stats.geographic.model_dump() if hasattr(stats.geographic, 'model_dump') else stats.geographic
                if isinstance(geographic_data, dict) and 'states' in geographic_data:
                    states = geographic_data['states']
                    self.logger.info(f"Loaded {len(states)} states from API")
                    return states
            
            # Fall back to default states for demo
            self.logger.info("API geographic data not available, using default states for demo")
            return self._get_default_states()
            
        except Exception as e:
            self.logger.warning(f"Failed to load states from API: {e}, using default states")
            return self._get_default_states()
    
    def load_counties(self) -> List[Dict[str, Any]]:
        """
        Load county data
        
        Returns:
            List of county dictionaries
        """
        try:
            # Try to get geographic data via API statistics
            stats = self.stats_client.get_all_stats()
            
            # Check if geographic data is available in stats
            if hasattr(stats, 'geographic') and stats.geographic:
                geographic_data = stats.geographic.model_dump() if hasattr(stats.geographic, 'model_dump') else stats.geographic
                if isinstance(geographic_data, dict) and 'counties' in geographic_data:
                    counties = geographic_data['counties']
                    self.logger.info(f"Loaded {len(counties)} counties from API")
                    return counties
            
            # Fall back to default counties for demo
            self.logger.info("API geographic data not available, using default counties for demo")
            return self._get_default_counties()
            
        except Exception as e:
            self.logger.warning(f"Failed to load counties from API: {e}, using default counties")
            return self._get_default_counties()
    
    def load_cities(self) -> List[Dict[str, Any]]:
        """
        Load city data
        
        Returns:
            List of city dictionaries
        """
        try:
            # Try to get geographic data via API statistics
            stats = self.stats_client.get_all_stats()
            
            # Check if geographic data is available in stats
            if hasattr(stats, 'geographic') and stats.geographic:
                geographic_data = stats.geographic.model_dump() if hasattr(stats.geographic, 'model_dump') else stats.geographic
                if isinstance(geographic_data, dict) and 'cities' in geographic_data:
                    cities = geographic_data['cities']
                    self.logger.info(f"Loaded {len(cities)} cities from API")
                    return cities
            
            # Fall back to default cities for demo
            self.logger.info("API geographic data not available, using default cities for demo")
            return self._get_default_cities()
            
        except Exception as e:
            self.logger.warning(f"Failed to load cities from API: {e}, using default cities")
            return self._get_default_cities()
    
    def _get_default_states(self) -> List[Dict[str, Any]]:
        """Get default state data for California and Utah"""
        return [
            {
                "state_id": "california",
                "state_code": "CA",
                "state_name": "California",
                "region": "West",
                "division": "Pacific",
                "capital": "Sacramento",
                "largest_city": "Los Angeles",
                "population": 39538223,
                "total_area_sq_mi": 163695,
                "land_area_sq_mi": 155779,
                "water_area_sq_mi": 7916,
                "latitude": 36.778261,
                "longitude": -119.417932
            },
            {
                "state_id": "utah",
                "state_code": "UT",
                "state_name": "Utah",
                "region": "West",
                "division": "Mountain",
                "capital": "Salt Lake City",
                "largest_city": "Salt Lake City",
                "population": 3271616,
                "total_area_sq_mi": 84897,
                "land_area_sq_mi": 82170,
                "water_area_sq_mi": 2727,
                "latitude": 39.321,
                "longitude": -111.0937
            }
        ]
    
    def _get_default_counties(self) -> List[Dict[str, Any]]:
        """Get default county data for San Francisco and Summit counties"""
        return [
            {
                "county_id": "san_francisco_county",
                "county_name": "San Francisco County",
                "state_id": "california",
                "state_code": "CA",
                "county_seat": "San Francisco",
                "population": 873965,
                "total_area_sq_mi": 231.89,
                "land_area_sq_mi": 46.87,
                "water_area_sq_mi": 185.02,
                "latitude": 37.7749,
                "longitude": -122.4194
            },
            {
                "county_id": "summit_county",
                "county_name": "Summit County",
                "state_id": "utah",
                "state_code": "UT",
                "county_seat": "Coalville",
                "population": 42357,
                "total_area_sq_mi": 1882,
                "land_area_sq_mi": 1849,
                "water_area_sq_mi": 33,
                "latitude": 40.8689,
                "longitude": -110.9557
            }
        ]
    
    def _get_default_cities(self) -> List[Dict[str, Any]]:
        """Get default city data for San Francisco and Park City"""
        return [
            {
                "city_id": "san_francisco",
                "city_name": "San Francisco",
                "county_id": "san_francisco_county",
                "county_name": "San Francisco County",
                "state_id": "california",
                "state_code": "CA",
                "city_type": "city-county",
                "incorporated": "1850-04-15",
                "population": 873965,
                "population_density_per_sq_mi": 18630,
                "total_area_sq_mi": 231.89,
                "land_area_sq_mi": 46.87,
                "water_area_sq_mi": 185.02,
                "elevation_ft": 52,
                "latitude": 37.7749,
                "longitude": -122.4194,
                "timezone": "America/Los_Angeles",
                "neighborhoods": [
                    "Mission District", "SOMA", "Financial District", "Nob Hill",
                    "Castro", "Haight-Ashbury", "Marina District", "Pacific Heights"
                ]
            },
            {
                "city_id": "park_city",
                "city_name": "Park City",
                "county_id": "summit_county",
                "county_name": "Summit County",
                "state_id": "utah",
                "state_code": "UT",
                "city_type": "city",
                "incorporated": "1884-01-05",
                "population": 8504,
                "population_density_per_sq_mi": 504,
                "total_area_sq_mi": 17.567,
                "land_area_sq_mi": 17.567,
                "water_area_sq_mi": 0,
                "elevation_ft": 7000,
                "latitude": 40.6461,
                "longitude": -111.4980,
                "timezone": "America/Denver",
                "neighborhoods": [
                    "Old Town", "Park Meadows", "Deer Valley", "The Aerie",
                    "Prospector", "Thaynes Canyon", "Silver Springs"
                ]
            }
        ]