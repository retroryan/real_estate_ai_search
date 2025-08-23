"""Geographic data source implementation"""

import json
from pathlib import Path
from typing import List, Dict, Any
import logging

from src.core.interfaces import IGeographicDataSource


class GeographicFileDataSource(IGeographicDataSource):
    """File-based geographic data source"""
    
    def __init__(self, data_path: Path):
        """
        Initialize geographic data source
        
        Args:
            data_path: Path to geographic data directory
        """
        self.data_path = data_path
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Define file paths
        self.states_file = data_path / "states.json"
        self.counties_file = data_path / "counties.json"
        self.cities_file = data_path / "cities.json"
    
    def exists(self) -> bool:
        """Check if data source exists"""
        # At least one geographic file should exist
        return (
            self.states_file.exists() or 
            self.counties_file.exists() or 
            self.cities_file.exists()
        )
    
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
        if not self.states_file.exists():
            # Return default states if file doesn't exist
            self.logger.info("States file not found, using default states")
            return self._get_default_states()
        
        try:
            with open(self.states_file, "r") as f:
                states = json.load(f)
                self.logger.info(f"Loaded {len(states)} states from file")
                return states
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse {self.states_file}: {e}")
            return self._get_default_states()
        except Exception as e:
            self.logger.error(f"Failed to load {self.states_file}: {e}")
            return self._get_default_states()
    
    def load_counties(self) -> List[Dict[str, Any]]:
        """
        Load county data
        
        Returns:
            List of county dictionaries
        """
        if not self.counties_file.exists():
            # Return default counties if file doesn't exist
            self.logger.info("Counties file not found, using default counties")
            return self._get_default_counties()
        
        try:
            with open(self.counties_file, "r") as f:
                counties = json.load(f)
                self.logger.info(f"Loaded {len(counties)} counties from file")
                return counties
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse {self.counties_file}: {e}")
            return self._get_default_counties()
        except Exception as e:
            self.logger.error(f"Failed to load {self.counties_file}: {e}")
            return self._get_default_counties()
    
    def load_cities(self) -> List[Dict[str, Any]]:
        """
        Load city data
        
        Returns:
            List of city dictionaries
        """
        if not self.cities_file.exists():
            # Return default cities if file doesn't exist
            self.logger.info("Cities file not found, using default cities")
            return self._get_default_cities()
        
        try:
            with open(self.cities_file, "r") as f:
                cities = json.load(f)
                self.logger.info(f"Loaded {len(cities)} cities from file")
                return cities
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse {self.cities_file}: {e}")
            return self._get_default_cities()
        except Exception as e:
            self.logger.error(f"Failed to load {self.cities_file}: {e}")
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