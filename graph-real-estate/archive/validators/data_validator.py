"""Data validator with Pydantic models and type safety"""
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime
from pydantic import BaseModel, Field

from models.geographic import LocationEntry
from database import get_neo4j_driver, run_query, close_neo4j_driver


class ValidationStats(BaseModel):
    """Statistics from validation"""
    locations_total: int = 0
    locations_states: int = 0
    locations_counties: int = 0
    locations_cities: int = 0
    
    wikipedia_total: int = 0
    wikipedia_with_summaries: int = 0
    wikipedia_with_topics: int = 0
    wikipedia_avg_confidence: float = 0.0
    
    properties_total: int = 0
    properties_with_county: int = 0
    
    neighborhoods_total: int = 0
    neighborhoods_with_wikipedia: int = 0
    
    timestamp: datetime = Field(default_factory=datetime.now)


class ValidationResult(BaseModel):
    """Result of validation process"""
    is_valid: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    stats: ValidationStats = Field(default_factory=ValidationStats)
    
    def add_error(self, error: str) -> None:
        """Add an error to the result"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the result"""
        self.warnings.append(warning)


class DataValidator:
    """Comprehensive data validator for all phases"""
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize validator"""
        # Go up to real_estate_ai_search directory
        self.base_path = base_path or Path(__file__).parent.parent.parent.parent
        self.result = ValidationResult()
        self.stats = ValidationStats()
        
    def validate_all(self) -> ValidationResult:
        """Run all validation checks"""
        print("="*60)
        print("DATA VALIDATION")
        print("="*60)
        
        # Check Neo4j connectivity
        neo4j_ok = self._check_neo4j()
        
        # Validate data sources
        locations_ok = self._validate_locations_json()
        wikipedia_ok = self._validate_wikipedia_database()
        properties_ok = self._validate_property_data()
        neighborhoods_ok = self._validate_neighborhood_data()
        
        # Update result stats
        self.result.stats = self.stats
        
        # Generate report
        self._print_report()
        
        # Set overall validity
        if not (neo4j_ok and locations_ok and wikipedia_ok and properties_ok and neighborhoods_ok):
            self.result.is_valid = False
        
        return self.result
    
    def _check_neo4j(self) -> bool:
        """Check Neo4j connectivity"""
        print("\n1. Checking Neo4j connectivity...")
        try:
            driver = get_neo4j_driver()
            result = run_query(driver, "RETURN 1 as test")
            close_neo4j_driver(driver)
            print("   ✓ Neo4j connection successful")
            return True
        except Exception as e:
            self.result.add_error(f"Neo4j connection failed: {e}")
            print(f"   ✗ Neo4j connection failed: {e}")
            return False
    
    def _validate_locations_json(self) -> bool:
        """Validate locations.json structure and content"""
        print("\n2. Validating locations.json...")
        file_path = self.base_path / 'real_estate_data' / 'locations.json'
        
        if not file_path.exists():
            self.result.add_error(f"locations.json not found at {file_path}")
            return False
        
        try:
            with open(file_path, 'r') as f:
                raw_data = json.load(f)
            
            # Parse into LocationEntry models
            locations: List[LocationEntry] = []
            invalid_entries = 0
            
            for item in raw_data:
                try:
                    loc = LocationEntry(**item)
                    locations.append(loc)
                except Exception as e:
                    invalid_entries += 1
                    if invalid_entries <= 3:
                        self.result.add_warning(f"Invalid location entry: {item} - {e}")
            
            # Organize by type
            states: Set[str] = set()
            counties: Set[Tuple[str, str]] = set()
            cities: Set[Tuple[str, str, str]] = set()
            county_variations: Dict[str, Set[str]] = {}
            
            for loc in locations:
                if loc.is_state_only():
                    states.add(loc.state)
                
                if loc.is_county_entry():
                    counties.add((loc.county, loc.state))
                    
                    # Track variations
                    base_name = loc.county.replace(' County', '')
                    if base_name not in county_variations:
                        county_variations[base_name] = set()
                    county_variations[base_name].add(loc.county)
                
                if loc.is_city_entry():
                    cities.add((loc.city, loc.county, loc.state))
            
            # Check for inconsistent county naming
            inconsistent = {k: v for k, v in county_variations.items() if len(v) > 1}
            if inconsistent:
                self.result.add_warning(f"Found {len(inconsistent)} counties with naming variations")
            
            # Update stats
            self.stats.locations_total = len(locations)
            self.stats.locations_states = len(states)
            self.stats.locations_counties = len(counties)
            self.stats.locations_cities = len(cities)
            
            print(f"   ✓ Loaded {len(locations)} geographic entities")
            print(f"     - States: {len(states)}")
            print(f"     - Counties: {len(counties)}")
            print(f"     - Cities: {len(cities)}")
            
            if invalid_entries > 0:
                self.result.add_warning(f"{invalid_entries} invalid location entries found")
            
            # Validate expected states
            if states != {'California', 'Utah'}:
                self.result.add_warning(f"Unexpected states found: {states - {'California', 'Utah'}}")
            
            return True
            
        except Exception as e:
            self.result.add_error(f"Error loading locations.json: {e}")
            return False
    
    def _validate_wikipedia_database(self) -> bool:
        """Validate Wikipedia database structure and content"""
        print("\n3. Validating Wikipedia database...")
        db_path = self.base_path / 'data' / 'wikipedia' / 'wikipedia.db'
        
        if not db_path.exists():
            self.result.add_error(f"Wikipedia database not found at {db_path}")
            return False
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check page_summaries table structure
            cursor.execute("PRAGMA table_info(page_summaries)")
            columns = {row[1] for row in cursor.fetchall()}
            
            required_columns = {
                'page_id', 'short_summary', 'long_summary', 
                'key_topics', 'best_city', 'best_county', 
                'best_state', 'overall_confidence'
            }
            
            missing_columns = required_columns - columns
            if missing_columns:
                self.result.add_error(f"Missing columns in page_summaries: {missing_columns}")
                return False
            
            # Get statistics
            cursor.execute("""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN short_summary IS NOT NULL THEN 1 END) as has_short,
                       COUNT(CASE WHEN long_summary IS NOT NULL THEN 1 END) as has_long,
                       COUNT(CASE WHEN key_topics IS NOT NULL THEN 1 END) as has_topics,
                       AVG(overall_confidence) as avg_confidence
                FROM page_summaries
                WHERE overall_confidence > 0.3
            """)
            
            stats = cursor.fetchone()
            
            # Update validation stats
            self.stats.wikipedia_total = stats[0] or 0
            self.stats.wikipedia_with_summaries = stats[1] or 0
            self.stats.wikipedia_with_topics = stats[3] or 0
            self.stats.wikipedia_avg_confidence = stats[4] or 0.0
            
            print(f"   ✓ Found {self.stats.wikipedia_total} Wikipedia summaries")
            print(f"     - With summaries: {self.stats.wikipedia_with_summaries}")
            print(f"     - With topics: {self.stats.wikipedia_with_topics}")
            print(f"     - Average confidence: {self.stats.wikipedia_avg_confidence:.2f}")
            
            conn.close()
            return True
            
        except Exception as e:
            self.result.add_error(f"Error validating Wikipedia database: {e}")
            return False
    
    def _validate_property_data(self) -> bool:
        """Validate property JSON files"""
        print("\n4. Validating property data...")
        
        sf_path = self.base_path / 'real_estate_data' / 'properties_sf.json'
        pc_path = self.base_path / 'real_estate_data' / 'properties_pc.json'
        
        total_properties = 0
        properties_with_county = 0
        missing_neighborhoods = 0
        
        for city, path in [('San Francisco', sf_path), ('Park City', pc_path)]:
            if not path.exists():
                self.result.add_error(f"{path.name} not found")
                continue
            
            try:
                with open(path, 'r') as f:
                    properties = json.load(f)
                
                total_properties += len(properties)
                
                # Validate structure
                for prop in properties:
                    # Check required fields
                    if 'listing_id' not in prop:
                        self.result.add_warning(f"Property missing listing_id")
                    
                    if 'neighborhood_id' not in prop:
                        missing_neighborhoods += 1
                    
                    # Check address structure
                    if 'address' in prop and isinstance(prop['address'], dict):
                        if 'county' in prop['address']:
                            properties_with_county += 1
                
                print(f"   ✓ {city}: {len(properties)} properties")
                
            except Exception as e:
                self.result.add_error(f"Error loading {path.name}: {e}")
        
        # Update stats
        self.stats.properties_total = total_properties
        self.stats.properties_with_county = properties_with_county
        
        if missing_neighborhoods > 0:
            self.result.add_warning(f"{missing_neighborhoods} properties missing neighborhood_id")
        
        return total_properties > 0
    
    def _validate_neighborhood_data(self) -> bool:
        """Validate neighborhood JSON files"""
        print("\n5. Validating neighborhood data...")
        
        sf_path = self.base_path / 'real_estate_data' / 'neighborhoods_sf.json'
        pc_path = self.base_path / 'real_estate_data' / 'neighborhoods_pc.json'
        
        total_neighborhoods = 0
        with_wikipedia = 0
        missing_county = 0
        
        for city, path in [('San Francisco', sf_path), ('Park City', pc_path)]:
            if not path.exists():
                self.result.add_error(f"{path.name} not found")
                continue
            
            try:
                with open(path, 'r') as f:
                    neighborhoods = json.load(f)
                
                total_neighborhoods += len(neighborhoods)
                
                for n in neighborhoods:
                    # Check for Wikipedia metadata
                    if 'graph_metadata' in n and n['graph_metadata']:
                        if 'primary_wiki_article' in n['graph_metadata']:
                            primary = n['graph_metadata']['primary_wiki_article']
                            if primary and primary.get('page_id'):
                                with_wikipedia += 1
                    
                    # Check geographic fields
                    if 'county' not in n:
                        missing_county += 1
                
                print(f"   ✓ {city}: {len(neighborhoods)} neighborhoods")
                
            except Exception as e:
                self.result.add_error(f"Error loading {path.name}: {e}")
        
        # Update stats
        self.stats.neighborhoods_total = total_neighborhoods
        self.stats.neighborhoods_with_wikipedia = with_wikipedia
        
        print(f"     - With Wikipedia data: {with_wikipedia}/{total_neighborhoods}")
        
        if missing_county > 0:
            self.result.add_warning(f"{missing_county} neighborhoods missing county")
        
        return total_neighborhoods > 0
    
    def _print_report(self) -> None:
        """Print validation report"""
        print("\n" + "="*60)
        print("VALIDATION REPORT")
        print("="*60)
        
        if self.result.errors:
            print("\n❌ ERRORS (must fix):")
            for error in self.result.errors[:10]:
                print(f"   - {error}")
            if len(self.result.errors) > 10:
                print(f"   ... and {len(self.result.errors) - 10} more")
        
        if self.result.warnings:
            print("\n⚠️  WARNINGS (should review):")
            for warning in self.result.warnings[:10]:
                print(f"   - {warning}")
            if len(self.result.warnings) > 10:
                print(f"   ... and {len(self.result.warnings) - 10} more")
        
        print("\n📊 STATISTICS:")
        print(f"   Locations: {self.stats.locations_total} entities")
        print(f"   Wikipedia: {self.stats.wikipedia_total} summaries")
        print(f"   Properties: {self.stats.properties_total} listings")
        print(f"   Neighborhoods: {self.stats.neighborhoods_total} areas")
        
        if not self.result.errors:
            print("\n✅ All validation checks passed!")
        else:
            print("\n❌ Validation failed. Please fix errors before proceeding.")