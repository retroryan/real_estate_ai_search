"""Geographic foundation loader with Pydantic models and type safety"""
import json
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict

from src.loaders.base import BaseLoader
from src.loaders.config import GraphLoadingConfig
from src.models.geographic import (
    State, County, City, LocationEntry, 
    GeographicHierarchy, GeographicStats
)
from src.utils.geographic import GeographicUtils
from src.database import clear_database


class GeographicFoundationLoader(BaseLoader):
    """Load geographic hierarchy from locations.json with type safety"""
    
    def __init__(self, locations_path: Optional[Path] = None):
        """Initialize the geographic loader"""
        super().__init__()
        
        # Load batch size configuration
        self.batch_config = GraphLoadingConfig.from_yaml()
        
        if locations_path:
            self.locations_path = locations_path
        else:
            self.locations_path = self.base_path / 'real_estate_data' / 'locations.json'
        
        self.hierarchy = GeographicHierarchy()
        self.geographic_index: Dict[str, any] = {}
        
    
    def _clear_database(self) -> None:
        """Clear all existing data from database"""
        self.logger.info("Clearing database...")
        clear_database(self.driver)
        self.logger.info("Database cleared")
    
    def _load_locations(self) -> List[LocationEntry]:
        """Load and validate locations from JSON"""
        self.logger.info(f"Loading locations from {self.locations_path}")
        
        if not self.locations_path.exists():
            raise FileNotFoundError(f"Locations file not found: {self.locations_path}")
        
        with open(self.locations_path, 'r') as f:
            raw_data = json.load(f)
        
        # Convert to Pydantic models
        locations = []
        for item in raw_data:
            try:
                location = LocationEntry(**item)
                locations.append(location)
            except Exception as e:
                self.logger.warning(f"Invalid location entry: {item} - {e}")
        
        self.logger.info(f"Loaded {len(locations)} location entries")
        return locations
    
    def _organize_hierarchy(self, locations: List[LocationEntry]) -> None:
        """Organize locations into hierarchical structure"""
        self.logger.info("Organizing geographic hierarchy...")
        
        # Use sets to track unique entities
        states_set: Set[str] = set()
        counties_set: Set[Tuple[str, str]] = set()  # (county, state)
        cities_set: Set[Tuple[str, str, str]] = set()  # (city, county, state)
        
        # Track county name variations
        county_variations: Dict[str, Set[str]] = defaultdict(set)
        
        for loc in locations:
            # Track states
            if loc.state:
                states_set.add(loc.state)
            
            # Track counties
            if loc.is_county_entry():
                counties_set.add((loc.county, loc.state))
                
                # Track variations
                base_name, _ = GeographicUtils.parse_county_variations(loc.county)
                county_variations[base_name].add(loc.county)
            
            # Track cities
            if loc.is_city_entry():
                cities_set.add((loc.city, loc.county, loc.state))
        
        # Report county variations
        inconsistent = {k: v for k, v in county_variations.items() if len(v) > 1}
        if inconsistent:
            self.logger.warning(f"Found {len(inconsistent)} counties with naming variations")
            for base, variations in list(inconsistent.items())[:5]:
                self.logger.debug(f"  {base}: {variations}")
        
        # Create State models
        for state_name in sorted(states_set):
            state_code = GeographicUtils.get_state_code(state_name)
            if state_code:
                state = State(
                    state_code=state_code,
                    state_name=state_name
                )
                self.hierarchy.states.append(state)
        
        # Create County models  
        for county_name, state_name in sorted(counties_set):
            state_code = GeographicUtils.get_state_code(state_name)
            if state_code:
                # Use official county name (preserve "County" suffix if present)
                county_id = GeographicUtils.normalize_county_id(county_name, state_code)
                county = County(
                    county_id=county_id,
                    county_name=county_name,  # Keep official name
                    state_code=state_code,
                    state_name=state_name
                )
                self.hierarchy.counties.append(county)
        
        # Create City models
        for city_name, county_name, state_name in sorted(cities_set):
            state_code = GeographicUtils.get_state_code(state_name)
            if state_code:
                county_id = GeographicUtils.normalize_county_id(county_name, state_code)
                city_id = GeographicUtils.normalize_city_id(city_name, state_code)
                city = City(
                    city_id=city_id,
                    city_name=city_name,
                    county_id=county_id,
                    county_name=county_name,
                    state_code=state_code,
                    state_name=state_name
                )
                self.hierarchy.cities.append(city)
        
        self.logger.info(f"Organized: {len(self.hierarchy.states)} states, "
                        f"{len(self.hierarchy.counties)} counties, "
                        f"{len(self.hierarchy.cities)} cities")
    
    def _create_constraints_and_indexes(self) -> None:
        """Create database constraints and indexes with optimizations from FIX_v7"""
        self.logger.info("Creating enhanced constraints and indexes...")
        
        # Node key constraints for data integrity
        constraints = [
            ("State.state_code", 
             "CREATE CONSTRAINT IF NOT EXISTS FOR (s:State) REQUIRE s.state_code IS UNIQUE"),
            ("County.county_id", 
             "CREATE CONSTRAINT IF NOT EXISTS FOR (c:County) REQUIRE c.county_id IS UNIQUE"),
            ("City.city_id", 
             "CREATE CONSTRAINT IF NOT EXISTS FOR (c:City) REQUIRE c.city_id IS UNIQUE"),
        ]
        
        for name, query in constraints:
            self.create_constraint(name, query)
        
        # Enhanced indexes for better query performance
        indexes = [
            # State indexes
            ("State.state_name", 
             "CREATE INDEX IF NOT EXISTS FOR (s:State) ON (s.state_name)"),
            
            # County indexes
            ("County.state_code", 
             "CREATE INDEX IF NOT EXISTS FOR (c:County) ON (c.state_code)"),
            ("County.county_name",
             "CREATE INDEX IF NOT EXISTS FOR (c:County) ON (c.county_name)"),
            
            # City indexes
            ("City.state_code", 
             "CREATE INDEX IF NOT EXISTS FOR (c:City) ON (c.state_code)"),
            ("City.county_id",
             "CREATE INDEX IF NOT EXISTS FOR (c:City) ON (c.county_id)"),
            ("City.city_name",
             "CREATE INDEX IF NOT EXISTS FOR (c:City) ON (c.city_name)"),
        ]
        
        for name, query in indexes:
            self.create_index(name, query)
    
    def _create_state_nodes(self) -> None:
        """Create State nodes in database"""
        self.logger.info(f"Creating {len(self.hierarchy.states)} state nodes...")
        
        batch_data = []
        for state in self.hierarchy.states:
            batch_data.append({
                'state_code': state.state_code,
                'state_name': state.state_name
            })
            self.geographic_index[f"state:{state.state_code}"] = state
        
        query = """
        WITH item
        MERGE (s:State:Location {state_code: item.state_code})
        SET s.state_name = item.state_name,
            s.state_id = item.state_code,
            s.created_at = datetime()
        """
        
        created = self.batch_execute(query, batch_data, batch_size=self.batch_config.state_batch_size)
        self.logger.info(f"Created {created} state nodes")
    
    def _create_county_nodes(self) -> None:
        """Create County nodes in database"""
        self.logger.info(f"Creating {len(self.hierarchy.counties)} county nodes...")
        
        batch_data = []
        for county in self.hierarchy.counties:
            batch_data.append({
                'county_id': county.county_id,
                'county_name': county.county_name,
                'state_code': county.state_code
            })
            self.geographic_index[f"county:{county.county_id}"] = county
        
        query = """
        WITH item
        MATCH (s:State {state_code: item.state_code})
        MERGE (c:County:Location {county_id: item.county_id})
        SET c.county_name = item.county_name,
            c.state_code = item.state_code,
            c.created_at = datetime()
        MERGE (c)-[:IN_STATE]->(s)
        """
        
        created = self.batch_execute(query, batch_data, batch_size=self.batch_config.county_batch_size)
        self.logger.info(f"Created {created} county nodes with state relationships")
    
    def _create_city_nodes(self) -> None:
        """Create City nodes in database"""
        self.logger.info(f"Creating {len(self.hierarchy.cities)} city nodes...")
        
        batch_data = []
        for city in self.hierarchy.cities:
            batch_data.append({
                'city_id': city.city_id,
                'city_name': city.city_name,
                'county_id': city.county_id,
                'state_code': city.state_code
            })
            self.geographic_index[f"city:{city.city_id}"] = city
        
        query = """
        WITH item
        MATCH (c:County {county_id: item.county_id})
        MERGE (city:City:Location {city_id: item.city_id})
        SET city.city_name = item.city_name,
            city.county_id = item.county_id,
            city.state_code = item.state_code,
            city.created_at = datetime()
        MERGE (city)-[:IN_COUNTY]->(c)
        """
        
        created = self.batch_execute(query, batch_data, batch_size=self.batch_config.city_batch_size)
        self.logger.info(f"Created {created} city nodes with county relationships")
    
    def _verify_hierarchy(self) -> GeographicStats:
        """Verify the geographic hierarchy is complete"""
        self.logger.info("Verifying geographic hierarchy...")
        
        stats = GeographicStats()
        
        # Count nodes
        stats.total_states = self.count_nodes("State")
        stats.total_counties = self.count_nodes("County")
        stats.total_cities = self.count_nodes("City")
        
        # Verify complete paths
        query = """
        MATCH path = (city:City)-[:IN_COUNTY]->(county:County)-[:IN_STATE]->(state:State)
        RETURN count(DISTINCT city) as count
        """
        result = self.execute_query(query)
        stats.cities_with_complete_path = result[0]['count'] if result else 0
        
        self.logger.info(f"Verification complete:")
        self.logger.info(f"  States in DB: {stats.total_states}")
        self.logger.info(f"  Counties in DB: {stats.total_counties}")
        self.logger.info(f"  Cities in DB: {stats.total_cities}")
        self.logger.info(f"  Cities with complete path: {stats.cities_with_complete_path}")
        
        return stats
    
    def get_hierarchy(self) -> GeographicHierarchy:
        """Get the loaded geographic hierarchy"""
        return self.hierarchy
    
    def get_geographic_index(self) -> Dict[str, any]:
        """Get the geographic index for lookups"""
        return self.geographic_index
    
    def load(self) -> GeographicStats:
        """Main loading method that orchestrates the entire process"""
        self.logger.info("=" * 60)
        self.logger.info("GEOGRAPHIC FOUNDATION LOADING")
        self.logger.info("=" * 60)
        
        # Clear existing data
        self._clear_database()
        
        # Load and organize data
        locations = self._load_locations()
        self._organize_hierarchy(locations)
        
        # Create constraints and indexes
        self._create_constraints_and_indexes()
        
        # Create nodes
        self._create_state_nodes()
        self._create_county_nodes()
        self._create_city_nodes()
        
        # Verify and get stats
        stats = self._verify_hierarchy()
        
        # Update stats with actual counts
        stats.total_states = len(self.hierarchy.states)
        stats.total_counties = len(self.hierarchy.counties)
        stats.total_cities = len(self.hierarchy.cities)
        
        self.logger.info("=" * 60)
        self.logger.info("✅ GEOGRAPHIC FOUNDATION COMPLETE")
        self.logger.info(f"  States: {stats.total_states}")
        self.logger.info(f"  Counties: {stats.total_counties}")
        self.logger.info(f"  Cities: {stats.total_cities}")
        self.logger.info("=" * 60)
        
        return stats