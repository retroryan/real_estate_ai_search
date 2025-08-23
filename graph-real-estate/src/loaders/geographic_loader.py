"""Geographic foundation loader with constructor injection"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from src.core.query_executor import QueryExecutor
from src.core.config import GeographicConfig
from src.data_sources import GeographicFileDataSource
from src.models.geographic import State, County, City, GeographicLoadResult


class GeographicFoundationLoader:
    """Load geographic foundation data with injected dependencies"""
    
    def __init__(
        self,
        query_executor: QueryExecutor,
        config: GeographicConfig,
        data_source: GeographicFileDataSource
    ):
        """
        Initialize geographic loader with dependencies
        
        Args:
            query_executor: Database query executor
            config: Geographic configuration
            data_source: Geographic data source
        """
        self.query_executor = query_executor
        self.config = config
        self.data_source = data_source
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Geographic index for lookups
        self.geographic_index: Dict[str, Dict[str, Any]] = {}
        
        # Load result tracking
        self.load_result = GeographicLoadResult()
    
    def load(self) -> GeographicLoadResult:
        """
        Main loading method
        
        Returns:
            GeographicLoadResult with statistics
        """
        self.logger.info("=" * 60)
        self.logger.info("GEOGRAPHIC FOUNDATION LOADING")
        self.logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Create constraints and indexes
            self._create_constraints_and_indexes()
            
            # Load states if configured
            if self.config.load_states:
                self._load_states()
            
            # Load counties if configured
            if self.config.load_counties:
                self._load_counties()
            
            # Load cities if configured
            if self.config.load_cities:
                self._load_cities()
            
            # Create geographic relationships
            self._create_geographic_relationships()
            
            # Build geographic index
            self._build_geographic_index()
            
            # Calculate duration
            self.load_result.duration_seconds = (datetime.now() - start_time).total_seconds()
            self.load_result.success = True
            
            self.logger.info("=" * 60)
            self.logger.info("✅ GEOGRAPHIC FOUNDATION COMPLETE")
            self.logger.info(f"  States: {self.load_result.total_states}")
            self.logger.info(f"  Counties: {self.load_result.total_counties}")
            self.logger.info(f"  Cities: {self.load_result.total_cities}")
            self.logger.info(f"  Duration: {self.load_result.duration_seconds:.1f}s")
            self.logger.info("=" * 60)
            
            return self.load_result
            
        except Exception as e:
            self.logger.error(f"Failed to load geographic data: {e}")
            self.load_result.add_error(str(e))
            self.load_result.success = False
            import traceback
            traceback.print_exc()
            return self.load_result
    
    def _create_constraints_and_indexes(self) -> None:
        """Create geographic constraints and indexes"""
        self.logger.info("Creating geographic constraints and indexes...")
        
        # Constraints
        constraints = [
            ("State.state_id",
             "CREATE CONSTRAINT IF NOT EXISTS FOR (s:State) REQUIRE s.state_id IS UNIQUE"),
            ("County.county_id",
             "CREATE CONSTRAINT IF NOT EXISTS FOR (c:County) REQUIRE c.county_id IS UNIQUE"),
            ("City.city_id",
             "CREATE CONSTRAINT IF NOT EXISTS FOR (c:City) REQUIRE c.city_id IS UNIQUE"),
        ]
        
        for name, query in constraints:
            self.query_executor.create_constraint(name, query)
        
        # Indexes
        indexes = [
            ("State.state_code",
             "CREATE INDEX IF NOT EXISTS FOR (s:State) ON (s.state_code)"),
            ("State.state_name",
             "CREATE INDEX IF NOT EXISTS FOR (s:State) ON (s.state_name)"),
            ("County.county_name",
             "CREATE INDEX IF NOT EXISTS FOR (c:County) ON (c.county_name)"),
            ("City.city_name",
             "CREATE INDEX IF NOT EXISTS FOR (c:City) ON (c.city_name)"),
            ("Location.latitude",
             "CREATE INDEX IF NOT EXISTS FOR (l:Location) ON (l.latitude)"),
            ("Location.longitude",
             "CREATE INDEX IF NOT EXISTS FOR (l:Location) ON (l.longitude)"),
        ]
        
        for name, query in indexes:
            self.query_executor.create_index(name, query)
    
    def _load_states(self) -> None:
        """Load state data"""
        self.logger.info("Loading states...")
        
        states = self.data_source.load_states()
        
        if not states:
            self.logger.warning("No states data found")
            return
        
        batch_data = []
        for state_data in states:
            try:
                # Validate with Pydantic
                state = State(**state_data)
                
                batch_data.append({
                    'state_id': state.state_id,
                    'state_code': state.state_code,
                    'state_name': state.state_name,
                    'region': state.region,
                    'division': state.division,
                    'capital': state.capital,
                    'largest_city': state.largest_city,
                    'population': state.population,
                    'total_area_sq_mi': state.total_area_sq_mi,
                    'land_area_sq_mi': state.land_area_sq_mi,
                    'water_area_sq_mi': state.water_area_sq_mi,
                    'latitude': state.latitude,
                    'longitude': state.longitude
                })
                
            except Exception as e:
                self.logger.warning(f"Failed to parse state {state_data.get('state_name', 'unknown')}: {e}")
        
        if batch_data:
            query = """
            WITH item
            MERGE (s:State:Location {state_id: item.state_id})
            SET s.state_code = item.state_code,
                s.state_name = item.state_name,
                s.region = item.region,
                s.division = item.division,
                s.capital = item.capital,
                s.largest_city = item.largest_city,
                s.population = item.population,
                s.total_area_sq_mi = item.total_area_sq_mi,
                s.land_area_sq_mi = item.land_area_sq_mi,
                s.water_area_sq_mi = item.water_area_sq_mi,
                s.latitude = item.latitude,
                s.longitude = item.longitude,
                s.created_at = datetime()
            """
            
            created = self.query_executor.batch_execute(query, batch_data)
            self.load_result.total_states = created
            self.logger.info(f"  Created {created} state nodes")
    
    def _load_counties(self) -> None:
        """Load county data"""
        self.logger.info("Loading counties...")
        
        counties = self.data_source.load_counties()
        
        if not counties:
            self.logger.warning("No counties data found")
            return
        
        batch_data = []
        for county_data in counties:
            try:
                # Validate with Pydantic
                county = County(**county_data)
                
                batch_data.append({
                    'county_id': county.county_id,
                    'county_name': county.county_name,
                    'state_id': county.state_id,
                    'state_code': county.state_code,
                    'county_seat': county.county_seat,
                    'population': county.population,
                    'total_area_sq_mi': county.total_area_sq_mi,
                    'land_area_sq_mi': county.land_area_sq_mi,
                    'water_area_sq_mi': county.water_area_sq_mi,
                    'latitude': county.latitude,
                    'longitude': county.longitude
                })
                
            except Exception as e:
                self.logger.warning(f"Failed to parse county {county_data.get('county_name', 'unknown')}: {e}")
        
        if batch_data:
            query = """
            WITH item
            MERGE (c:County:Location {county_id: item.county_id})
            SET c.county_name = item.county_name,
                c.state_id = item.state_id,
                c.state_code = item.state_code,
                c.county_seat = item.county_seat,
                c.population = item.population,
                c.total_area_sq_mi = item.total_area_sq_mi,
                c.land_area_sq_mi = item.land_area_sq_mi,
                c.water_area_sq_mi = item.water_area_sq_mi,
                c.latitude = item.latitude,
                c.longitude = item.longitude,
                c.created_at = datetime()
            """
            
            created = self.query_executor.batch_execute(query, batch_data)
            self.load_result.total_counties = created
            self.logger.info(f"  Created {created} county nodes")
    
    def _load_cities(self) -> None:
        """Load city data"""
        self.logger.info("Loading cities...")
        
        cities = self.data_source.load_cities()
        
        if not cities:
            self.logger.warning("No cities data found")
            return
        
        batch_data = []
        for city_data in cities:
            try:
                # Validate with Pydantic
                city = City(**city_data)
                
                batch_data.append({
                    'city_id': city.city_id,
                    'city_name': city.city_name,
                    'county_id': city.county_id,
                    'county_name': city.county_name,
                    'state_id': city.state_id,
                    'state_code': city.state_code,
                    'city_type': city.city_type,
                    'incorporated': city.incorporated,
                    'population': city.population,
                    'population_density_per_sq_mi': city.population_density_per_sq_mi,
                    'total_area_sq_mi': city.total_area_sq_mi,
                    'land_area_sq_mi': city.land_area_sq_mi,
                    'water_area_sq_mi': city.water_area_sq_mi,
                    'elevation_ft': city.elevation_ft,
                    'latitude': city.latitude,
                    'longitude': city.longitude,
                    'timezone': city.timezone,
                    'neighborhoods': city.neighborhoods or []
                })
                
            except Exception as e:
                self.logger.warning(f"Failed to parse city {city_data.get('city_name', 'unknown')}: {e}")
        
        if batch_data:
            query = """
            WITH item
            MERGE (c:City:Location {city_id: item.city_id})
            SET c.city_name = item.city_name,
                c.county_id = item.county_id,
                c.county_name = item.county_name,
                c.state_id = item.state_id,
                c.state_code = item.state_code,
                c.city_type = item.city_type,
                c.incorporated = item.incorporated,
                c.population = item.population,
                c.population_density_per_sq_mi = item.population_density_per_sq_mi,
                c.total_area_sq_mi = item.total_area_sq_mi,
                c.land_area_sq_mi = item.land_area_sq_mi,
                c.water_area_sq_mi = item.water_area_sq_mi,
                c.elevation_ft = item.elevation_ft,
                c.latitude = item.latitude,
                c.longitude = item.longitude,
                c.timezone = item.timezone,
                c.neighborhoods = item.neighborhoods,
                c.created_at = datetime()
            """
            
            created = self.query_executor.batch_execute(query, batch_data)
            self.load_result.total_cities = created
            self.logger.info(f"  Created {created} city nodes")
    
    def _create_geographic_relationships(self) -> None:
        """Create relationships between geographic entities"""
        self.logger.info("Creating geographic relationships...")
        
        # County -> State relationships
        query = """
        MATCH (c:County)
        MATCH (s:State {state_id: c.state_id})
        MERGE (c)-[r:IN_STATE]->(s)
        SET r.created_at = datetime()
        RETURN count(r) as count
        """
        result = self.query_executor.execute_write(query)
        county_state = result[0]['count'] if result else 0
        self.logger.info(f"  Created {county_state} county->state relationships")
        
        # City -> County relationships
        query = """
        MATCH (city:City)
        MATCH (county:County {county_id: city.county_id})
        MERGE (city)-[r:IN_COUNTY]->(county)
        SET r.created_at = datetime()
        RETURN count(r) as count
        """
        result = self.query_executor.execute_write(query)
        city_county = result[0]['count'] if result else 0
        self.logger.info(f"  Created {city_county} city->county relationships")
        
        # City -> State relationships (direct)
        query = """
        MATCH (city:City)
        MATCH (s:State {state_id: city.state_id})
        MERGE (city)-[r:IN_STATE]->(s)
        SET r.created_at = datetime()
        RETURN count(r) as count
        """
        result = self.query_executor.execute_write(query)
        city_state = result[0]['count'] if result else 0
        self.logger.info(f"  Created {city_state} city->state relationships")
    
    def _build_geographic_index(self) -> None:
        """Build geographic index for fast lookups"""
        self.logger.info("Building geographic index...")
        
        # Index states
        query = "MATCH (s:State) RETURN s"
        states = self.query_executor.execute_read(query)
        for record in states:
            state = record['s']
            self.geographic_index[f"state_{state['state_id']}"] = state
            self.geographic_index[f"state_code_{state['state_code']}"] = state
        
        # Index counties
        query = "MATCH (c:County) RETURN c"
        counties = self.query_executor.execute_read(query)
        for record in counties:
            county = record['c']
            self.geographic_index[f"county_{county['county_id']}"] = county
        
        # Index cities
        query = "MATCH (c:City) RETURN c"
        cities = self.query_executor.execute_read(query)
        for record in cities:
            city = record['c']
            self.geographic_index[f"city_{city['city_id']}"] = city
        
        self.logger.info(f"  Indexed {len(self.geographic_index)} geographic entities")
    
    def get_geographic_index(self) -> Dict[str, Dict[str, Any]]:
        """Get the geographic index for lookups"""
        return self.geographic_index