"""
Neighborhood data loader implementation with integrated enrichment.

Loads neighborhood data from JSON files and returns enriched Pydantic models.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base import BaseLoader, log_operation
from property_finder_models import (
    EnrichedNeighborhood,
    GeoLocation,
    GeoPolygon
)
from ..enrichers.address_utils import expand_city_name, expand_state_code, validate_coordinates
from ..enrichers.feature_utils import normalize_feature_list
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class NeighborhoodLoader(BaseLoader[EnrichedNeighborhood]):
    """
    Loader for neighborhood data from JSON files.
    
    Loads neighborhoods from neighborhoods_sf.json and neighborhoods_pc.json files,
    applies enrichment, and returns EnrichedNeighborhood Pydantic models.
    """
    
    def __init__(self, data_path: Path):
        """
        Initialize neighborhood loader with data path.
        
        Args:
            data_path: Path to directory containing neighborhood JSON files
        """
        super().__init__(data_path)
        
        # Define expected neighborhood files
        self.sf_neighborhoods_file = data_path / "neighborhoods_sf.json"
        self.pc_neighborhoods_file = data_path / "neighborhoods_pc.json"
        
        # Validate that at least one neighborhood file exists
        if not self.sf_neighborhoods_file.exists() and not self.pc_neighborhoods_file.exists():
            logger.warning(f"No neighborhood files found in {data_path}")
    
    @log_operation("load_all_neighborhoods")
    def load_all(self) -> List[EnrichedNeighborhood]:
        """
        Load all neighborhoods from all available JSON files.
        
        Returns:
            List of EnrichedNeighborhood models
        """
        all_neighborhoods = []
        
        # Load San Francisco neighborhoods
        if self.sf_neighborhoods_file.exists():
            sf_neighborhoods = self._load_neighborhoods_from_file(
                self.sf_neighborhoods_file,
                default_city="San Francisco",
                default_state="CA"
            )
            all_neighborhoods.extend(sf_neighborhoods)
            logger.info(f"Loaded {len(sf_neighborhoods)} neighborhoods from San Francisco")
        
        # Load Park City neighborhoods
        if self.pc_neighborhoods_file.exists():
            pc_neighborhoods = self._load_neighborhoods_from_file(
                self.pc_neighborhoods_file,
                default_city="Park City",
                default_state="UT"
            )
            all_neighborhoods.extend(pc_neighborhoods)
            logger.info(f"Loaded {len(pc_neighborhoods)} neighborhoods from Park City")
        
        return all_neighborhoods
    
    @log_operation("load_neighborhoods_by_filter")
    def load_by_filter(self, city: Optional[str] = None, **filters) -> List[EnrichedNeighborhood]:
        """
        Load neighborhoods with filtering support.
        
        Args:
            city: Optional city name filter (case-insensitive)
            **filters: Additional filters (for future extension)
            
        Returns:
            List of EnrichedNeighborhood models matching the filters
        """
        # Load all neighborhoods first
        all_neighborhoods = self.load_all()
        
        # Apply city filter if provided
        if city:
            from ..enrichers.address_utils import expand_city_name
            expanded_city = expand_city_name(city)
            city_lower = expanded_city.lower()
            
            filtered_neighborhoods = [
                neighborhood for neighborhood in all_neighborhoods
                if neighborhood.city.lower() == city_lower
            ]
            
            logger.info(f"Filtered {len(filtered_neighborhoods)} neighborhoods for city '{city}' (expanded to '{expanded_city}') from total {len(all_neighborhoods)}")
            return filtered_neighborhoods
        
        # No filters, return all
        return all_neighborhoods
    
    def _load_neighborhoods_from_file(
        self, 
        file_path: Path, 
        default_city: str, 
        default_state: str
    ) -> List[EnrichedNeighborhood]:
        """
        Load neighborhoods from a specific JSON file and convert to EnrichedNeighborhood models.
        
        Args:
            file_path: Path to the JSON file
            default_city: Default city name if not present in data
            default_state: Default state code if not present in data
            
        Returns:
            List of EnrichedNeighborhood models
        """
        enriched_neighborhoods = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_neighborhoods = json.load(f)
            
            # Convert each raw neighborhood to EnrichedNeighborhood
            for raw_neighborhood in raw_neighborhoods:
                try:
                    enriched_neighborhood = self._convert_to_enriched_neighborhood(
                        raw_neighborhood,
                        default_city,
                        default_state
                    )
                    enriched_neighborhoods.append(enriched_neighborhood)
                except Exception as e:
                    neighborhood_name = raw_neighborhood.get('name', 'unknown')
                    logger.warning(f"Failed to convert neighborhood {neighborhood_name}: {e}")
            
            return enriched_neighborhoods
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {file_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to load neighborhoods from {file_path}: {e}")
            return []
    
    def _convert_to_enriched_neighborhood(
        self,
        raw_data: Dict[str, Any],
        default_city: str,
        default_state: str
    ) -> EnrichedNeighborhood:
        """
        Convert raw neighborhood data to EnrichedNeighborhood model with enrichment.
        
        Args:
            raw_data: Raw neighborhood dictionary
            default_city: Default city if not present
            default_state: Default state if not present
            
        Returns:
            EnrichedNeighborhood model
        """
        # Extract and enrich city and state
        city = raw_data.get('city', default_city)
        city = expand_city_name(city) if city else default_city
        
        state = raw_data.get('state', default_state)
        state = expand_state_code(state) if state else default_state
        
        # Extract boundaries if present
        boundaries = None
        if 'boundaries' in raw_data and raw_data['boundaries']:
            boundary_points = []
            for point in raw_data['boundaries']:
                if isinstance(point, dict):
                    lat = point.get('lat') or point.get('latitude')
                    lon = point.get('lon') or point.get('lng') or point.get('longitude')
                    if validate_coordinates(lat, lon):
                        boundary_points.append(GeoLocation(lat=float(lat), lon=float(lon)))
            
            if len(boundary_points) >= 3:
                boundaries = GeoPolygon(points=boundary_points)
        
        # Extract center point if present
        center_point = None
        center_data = raw_data.get('center_point') or raw_data.get('center') or raw_data.get('coordinates')
        if center_data:
            lat = center_data.get('lat') or center_data.get('latitude')
            lon = center_data.get('lon') or center_data.get('lng') or center_data.get('longitude')
            if validate_coordinates(lat, lon):
                center_point = GeoLocation(lat=float(lat), lon=float(lon))
        
        # Extract and normalize characteristics
        characteristics = normalize_feature_list(raw_data.get('characteristics', []))
        
        # Generate neighborhood ID if not present
        neighborhood_id = raw_data.get('neighborhood_id')
        if not neighborhood_id:
            name = raw_data.get('name', 'unknown')
            # Create a simple ID from name and city
            name_part = name.lower().replace(' ', '_').replace(',', '')
            city_part = city.lower().replace(' ', '_')
            neighborhood_id = f"{city_part}_{name_part}"
        
        # Create EnrichedNeighborhood
        enriched_neighborhood = EnrichedNeighborhood(
            neighborhood_id=neighborhood_id,
            name=raw_data.get('name', 'Unknown Neighborhood'),
            city=city,
            state=state,
            boundaries=boundaries,
            center_point=center_point,
            demographics=raw_data.get('demographics', {}),
            poi_count=raw_data.get('poi_count', 0),
            description=raw_data.get('description'),
            characteristics=characteristics
        )
        
        return enriched_neighborhood