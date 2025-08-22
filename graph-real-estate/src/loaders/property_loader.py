"""Property loader for Phase 5"""
import json
from pathlib import Path
from typing import List, Dict, Set, Any
from datetime import datetime

from src.loaders.base import BaseLoader
from src.loaders.config import GraphLoadingConfig
from src.models.neighborhood import Neighborhood
from src.models.property import (
    Property, PropertyDetails, Address, Coordinates,
    PropertyType as PropertyTypeEnum, PriceRange, Feature, PropertyLoadResult
)


class PropertyLoader(BaseLoader):
    """Load properties from JSON files and connect to existing graph"""
    
    def __init__(self):
        """Initialize property loader"""
        super().__init__()
        self.properties: List[Property] = []
        self.load_result = PropertyLoadResult()
        
        # Load batch size configuration
        self.batch_config = GraphLoadingConfig.from_yaml()
        
        # Paths to property JSON files
        self.sf_path = self.base_path / 'real_estate_data' / 'properties_sf.json'
        self.pc_path = self.base_path / 'real_estate_data' / 'properties_pc.json'
        
        # Collections for unique entities
        self.unique_features: Set[str] = set()
        self.unique_property_types: Set[str] = set()
        self.price_ranges = PriceRange.get_standard_ranges()
    
    def load(self) -> PropertyLoadResult:
        """Main loading method"""
        self.logger.info("=" * 60)
        self.logger.info("PROPERTY LOADING AND CONNECTIONS")
        self.logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Load property data from JSON
            self.properties = self._load_properties_from_json()
            self.load_result.properties_loaded = len(self.properties)
            
            # Create constraints and indexes
            self._create_constraints_and_indexes()
            
            # Create price range nodes
            self._create_price_range_nodes()
            
            # Extract and create unique features
            self._create_feature_nodes()
            
            # Extract and create property type nodes
            self._create_property_type_nodes()
            
            # Create property nodes
            nodes_created = self._create_property_nodes()
            self.load_result.property_nodes = nodes_created
            
            # Create geographic relationships
            self._create_geographic_relationships()
            
            # Create feature relationships
            self._create_feature_relationships()
            
            # Create type and price relationships
            self._create_type_and_price_relationships()
            
            # Create Wikipedia→Property relationships (must be done after properties exist)
            self._create_wikipedia_property_relationships()
            
            # Calculate statistics
            self._calculate_statistics()
            
            # Verify the integration
            self._verify_integration()
            
            # Calculate duration
            self.load_result.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            self.logger.info("=" * 60)
            self.logger.info("✅ PROPERTY LOADING COMPLETE")
            self.logger.info(f"  Properties loaded: {self.load_result.properties_loaded}")
            self.logger.info(f"  Property nodes: {self.load_result.property_nodes}")
            self.logger.info(f"  Feature nodes: {self.load_result.feature_nodes}")
            self.logger.info(f"  Neighborhood connections: {self.load_result.neighborhood_relationships}")
            self.logger.info(f"  City connections: {self.load_result.city_relationships}")
            self.logger.info(f"  Duration: {self.load_result.duration_seconds:.1f}s")
            self.logger.info("=" * 60)
            
            return self.load_result
            
        except Exception as e:
            self.logger.error(f"Failed to load properties: {e}")
            self.load_result.add_error(str(e))
            import traceback
            traceback.print_exc()
            return self.load_result
    
    def _load_properties_from_json(self) -> List[Property]:
        """Load and parse property data from JSON files"""
        self.logger.info("Loading property data from JSON files...")
        
        properties = []
        
        for city_name, path in [('San Francisco', self.sf_path), ('Park City', self.pc_path)]:
            if not path.exists():
                self.load_result.add_warning(f"Property file not found: {path}")
                continue
            
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                
                for item in data:
                    try:
                        # Parse and validate with Pydantic
                        property_obj = Property(**item)
                        
                        # Extract features for tracking
                        if property_obj.features:
                            self.unique_features.update(property_obj.features)
                        
                        # Extract property type
                        prop_type = property_obj.get_property_type()
                        if prop_type and prop_type != 'unknown':
                            self.unique_property_types.add(prop_type)
                        
                        properties.append(property_obj)
                        
                    except Exception as e:
                        self.load_result.add_warning(
                            f"Failed to parse property {item.get('listing_id', 'unknown')}: {e}"
                        )
                
                self.logger.info(f"  Loaded {len([p for p in properties if path == self.sf_path or path == self.pc_path])} {city_name} properties")
                
            except Exception as e:
                self.load_result.add_error(f"Failed to load {path}: {e}")
        
        self.logger.info(f"Total properties loaded: {len(properties)}")
        self.logger.info(f"Unique features found: {len(self.unique_features)}")
        self.logger.info(f"Unique property types: {len(self.unique_property_types)}")
        
        return properties
    
    def _create_constraints_and_indexes(self) -> None:
        """Create enhanced property-specific constraints and indexes from FIX_v7"""
        self.logger.info("Creating enhanced property constraints and indexes...")
        
        # Node key constraints for data integrity
        constraints = [
            ("Property.listing_id",
             "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Property) REQUIRE p.listing_id IS UNIQUE"),
            ("Feature.feature_id",
             "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Feature) REQUIRE f.feature_id IS UNIQUE"),
            ("PropertyType.type_id",
             "CREATE CONSTRAINT IF NOT EXISTS FOR (pt:PropertyType) REQUIRE pt.type_id IS UNIQUE"),
            ("PriceRange.range_id",
             "CREATE CONSTRAINT IF NOT EXISTS FOR (pr:PriceRange) REQUIRE pr.range_id IS UNIQUE"),
        ]
        
        for name, query in constraints:
            self.create_constraint(name, query)
        
        # Enhanced indexes for better query performance
        indexes = [
            # Property indexes - optimized for common queries
            ("Property.neighborhood_id",
             "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.neighborhood_id)"),
            ("Property.city",
             "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.city)"),
            ("Property.listing_price",
             "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.listing_price)"),
            ("Property.bedrooms",
             "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.bedrooms)"),
            ("Property.bathrooms",
             "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.bathrooms)"),
            ("Property.square_feet",
             "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.square_feet)"),
            ("Property.price_per_sqft",
             "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.price_per_sqft)"),
            
            # Feature indexes
            ("Feature.category",
             "CREATE INDEX IF NOT EXISTS FOR (f:Feature) ON (f.category)"),
            ("Feature.name",
             "CREATE INDEX IF NOT EXISTS FOR (f:Feature) ON (f.name)"),
            
            # Asset label indexes (hierarchical)
            ("Asset.listing_price",
             "CREATE INDEX IF NOT EXISTS FOR (a:Asset) ON (a.listing_price)"),
        ]
        
        for name, query in indexes:
            self.create_index(name, query)
        
        # Create full-text search index for properties
        self._create_property_fulltext_index()
    
    def _create_property_fulltext_index(self) -> None:
        """Create full-text search index for properties"""
        try:
            # Check if index already exists
            check_query = "SHOW INDEXES YIELD name WHERE name = 'propertySearch' RETURN name"
            result = self.execute_query(check_query)
            
            if not result:
                query = """
                CALL db.index.fulltext.createNodeIndex(
                    'propertySearch',
                    ['Property'],
                    ['description', 'street', 'city', 'neighborhood_id']
                )
                """
                self.execute_query(query)
                self.logger.info("Created full-text index: propertySearch")
            else:
                self.logger.info("Full-text index already exists: propertySearch")
        except Exception as e:
            # Full-text search may not be available in all Neo4j versions
            if "unknown function" in str(e).lower() or "procedure" in str(e).lower():
                self.logger.debug("Full-text indexes not supported in this Neo4j version")
            else:
                self.logger.warning(f"Could not create full-text index: {e}")
    
    def _create_price_range_nodes(self) -> None:
        """Create price range nodes"""
        self.logger.info("Creating price range nodes...")
        
        batch_data = []
        for price_range in self.price_ranges:
            batch_data.append({
                'range_id': price_range.range_id,
                'label': price_range.label,
                'min_price': price_range.min_price,
                'max_price': price_range.max_price if price_range.max_price else 999999999
            })
        
        query = """
        WITH item
        MERGE (pr:PriceRange {range_id: item.range_id})
        SET pr.label = item.label,
            pr.min_price = item.min_price,
            pr.max_price = item.max_price,
            pr.created_at = datetime()
        """
        
        created = self.batch_execute(query, batch_data, batch_size=self.batch_config.default_batch_size)
        self.load_result.price_range_nodes = created
        self.logger.info(f"  Created {created} price range nodes")
    
    def _create_feature_nodes(self) -> None:
        """Create feature nodes from unique features"""
        self.logger.info(f"Creating {len(self.unique_features)} feature nodes...")
        
        batch_data = []
        for feature_name in self.unique_features:
            feature_id = feature_name.lower().replace(' ', '_').replace('-', '_')
            
            # Categorize features (simplified categorization)
            category = self._categorize_feature(feature_name)
            
            batch_data.append({
                'feature_id': feature_id,
                'name': feature_name,
                'category': category
            })
        
        query = """
        WITH item
        MERGE (f:Feature {feature_id: item.feature_id})
        SET f.name = item.name,
            f.category = item.category,
            f.created_at = datetime()
        """
        
        created = self.batch_execute(query, batch_data, batch_size=self.batch_config.feature_batch_size)
        self.load_result.feature_nodes = created
        self.load_result.unique_features = len(self.unique_features)
        self.logger.info(f"  Created {created} feature nodes")
    
    def _categorize_feature(self, feature_name: str) -> str:
        """Categorize a feature based on its name"""
        feature_lower = feature_name.lower()
        
        if any(word in feature_lower for word in ['view', 'vista', 'panoramic']):
            return 'View'
        elif any(word in feature_lower for word in ['pool', 'spa', 'hot tub', 'garden', 'yard', 'patio', 'deck']):
            return 'Outdoor'
        elif any(word in feature_lower for word in ['kitchen', 'appliance', 'granite', 'marble']):
            return 'Kitchen'
        elif any(word in feature_lower for word in ['parking', 'garage', 'carport']):
            return 'Parking'
        elif any(word in feature_lower for word in ['gym', 'fitness', 'concierge', 'doorman', 'security']):
            return 'Building Amenities'
        elif any(word in feature_lower for word in ['hardwood', 'fireplace', 'ceiling', 'crown']):
            return 'Interior'
        elif any(word in feature_lower for word in ['smart', 'wifi', 'wired', 'solar']):
            return 'Technology'
        elif any(word in feature_lower for word in ['storage', 'closet', 'pantry']):
            return 'Storage'
        else:
            return 'Other'
    
    def _create_property_type_nodes(self) -> None:
        """Create property type nodes"""
        self.logger.info(f"Creating {len(self.unique_property_types)} property type nodes...")
        
        batch_data = []
        for prop_type in self.unique_property_types:
            type_id = f"type_{prop_type.replace('-', '_')}"
            label = prop_type.replace('-', ' ').title()
            
            batch_data.append({
                'type_id': type_id,
                'name': prop_type,
                'label': label
            })
        
        query = """
        WITH item
        MERGE (pt:PropertyType {type_id: item.type_id})
        SET pt.name = item.name,
            pt.label = item.label,
            pt.created_at = datetime()
        """
        
        created = self.batch_execute(query, batch_data, batch_size=self.batch_config.default_batch_size)
        self.load_result.property_type_nodes = created
        self.load_result.unique_property_types = len(self.unique_property_types)
        self.logger.info(f"  Created {created} property type nodes")
    
    def _create_property_nodes(self) -> int:
        """Create property nodes in database"""
        self.logger.info(f"Creating {len(self.properties)} property nodes...")
        
        batch_data = []
        for prop in self.properties:
            # Extract address components - no isinstance needed anymore!
            address_dict = {}
            if prop.address:
                address_dict = {
                    'street': prop.address.street,
                    'city': prop.address.city,
                    'county': prop.address.county,
                    'state': prop.address.state,
                    'zip': prop.address.zip
                }
            
            # Extract coordinates - simplified!
            coords = prop.get_coordinates_dict()
            
            # Extract property details - simplified!
            details = {}
            if prop.property_details:
                details = {
                    'bedrooms': prop.property_details.bedrooms,
                    'bathrooms': prop.property_details.bathrooms,
                    'square_feet': prop.property_details.square_feet,
                    'year_built': prop.property_details.year_built,
                    'property_type': prop.property_details.property_type,
                    'lot_size': prop.property_details.lot_size,
                    'stories': prop.property_details.stories,
                    'garage_spaces': prop.property_details.garage_spaces
                }
            
            batch_data.append({
                'listing_id': prop.listing_id,
                'neighborhood_id': prop.neighborhood_id,
                'street': address_dict.get('street', ''),
                'city': address_dict.get('city', ''),
                'county': address_dict.get('county', ''),
                'state': address_dict.get('state', ''),
                'zip': address_dict.get('zip', ''),
                'latitude': coords['lat'],
                'longitude': coords['lng'],
                'listing_price': prop.listing_price,
                'price_per_sqft': prop.price_per_sqft or 0,
                'description': prop.description or '',
                'features': prop.features or [],
                'bedrooms': details.get('bedrooms', 0),
                'bathrooms': details.get('bathrooms', 0),
                'square_feet': details.get('square_feet', 0),
                'year_built': details.get('year_built'),
                'property_type': details.get('property_type', 'unknown'),
                'lot_size': details.get('lot_size'),
                'stories': details.get('stories'),
                'garage_spaces': details.get('garage_spaces'),
                'listing_date': prop.listing_date
            })
        
        query = """
        WITH item
        MERGE (p:Property:Asset {listing_id: item.listing_id})
        SET p.neighborhood_id = item.neighborhood_id,
            p.street = item.street,
            p.city = item.city,
            p.county = item.county,
            p.state = item.state,
            p.zip = item.zip,
            p.latitude = item.latitude,
            p.longitude = item.longitude,
            p.listing_price = item.listing_price,
            p.price_per_sqft = item.price_per_sqft,
            p.description = item.description,
            p.features = item.features,
            p.bedrooms = item.bedrooms,
            p.bathrooms = item.bathrooms,
            p.square_feet = item.square_feet,
            p.year_built = item.year_built,
            p.property_type = item.property_type,
            p.lot_size = item.lot_size,
            p.stories = item.stories,
            p.garage_spaces = item.garage_spaces,
            p.listing_date = item.listing_date,
            p.created_at = datetime()
        """
        
        created = self.batch_execute(query, batch_data, batch_size=self.batch_config.property_batch_size)
        self.logger.info(f"  Created {created} property nodes")
        return created
    
    def _create_geographic_relationships(self) -> None:
        """Create relationships to neighborhoods, cities, and counties with optimized queries"""
        self.logger.info("Creating geographic relationships...")
        
        # Connect to neighborhoods - optimized with index hints and filtering
        query = """
        MATCH (p:Property)
        WHERE p.neighborhood_id IS NOT NULL 
          AND NOT EXISTS((p)-[:IN_NEIGHBORHOOD]->())
        WITH p
        MATCH (n:Neighborhood {neighborhood_id: p.neighborhood_id})
        USING INDEX n:Neighborhood(neighborhood_id)
        MERGE (p)-[r:IN_NEIGHBORHOOD]->(n)
        SET r.created_at = datetime()
        RETURN count(r) as count
        """
        result = self.execute_query(query)
        neighborhood_count = result[0]['count'] if result else 0
        self.load_result.neighborhood_relationships = neighborhood_count
        self.logger.info(f"  Created {neighborhood_count} property->neighborhood relationships")
        
        # Connect to cities - optimized with early filtering
        query = """
        MATCH (p:Property)
        WHERE p.city IS NOT NULL 
          AND NOT EXISTS((p)-[:IN_CITY]->())
        WITH p, toLower(replace(p.city, ' ', '_')) as city_id
        MATCH (c:City)
        WHERE c.city_id = city_id OR toLower(c.city_name) = toLower(p.city)
        WITH p, c
        ORDER BY c.city_id
        LIMIT 1
        MERGE (p)-[r:IN_CITY]->(c)
        SET r.created_at = datetime()
        RETURN count(r) as count
        """
        result = self.execute_query(query)
        city_count = result[0]['count'] if result else 0
        self.load_result.city_relationships = city_count
        self.logger.info(f"  Created {city_count} property->city relationships")
        
        # Connect to counties - optimized with early filtering
        query = """
        MATCH (p:Property)
        WHERE p.county IS NOT NULL 
          AND NOT EXISTS((p)-[:IN_COUNTY]->())
        WITH p, 
             CASE
                WHEN p.county CONTAINS 'County' THEN toLower(replace(p.county, ' ', '_'))
                ELSE toLower(replace(p.county + ' County', ' ', '_'))
             END as county_id
        MATCH (c:County)
        WHERE c.county_id = county_id 
           OR toLower(c.county_name) = toLower(p.county) 
           OR toLower(c.county_name) = toLower(p.county + ' County')
        WITH p, c
        ORDER BY c.county_id
        LIMIT 1
        MERGE (p)-[r:IN_COUNTY]->(c)
        SET r.created_at = datetime()
        RETURN count(r) as count
        """
        result = self.execute_query(query)
        county_count = result[0]['count'] if result else 0
        self.load_result.county_relationships = county_count
        self.logger.info(f"  Created {county_count} property->county relationships")
        
        # Check for properties without neighborhoods
        query = """
        MATCH (p:Property)
        WHERE NOT EXISTS((p)-[:IN_NEIGHBORHOOD]->(:Neighborhood))
        RETURN count(p) as count
        """
        result = self.execute_query(query)
        orphaned = result[0]['count'] if result else 0
        if orphaned > 0:
            self.load_result.properties_without_neighborhoods = orphaned
            self.load_result.add_warning(f"{orphaned} properties could not be connected to neighborhoods")
    
    def _create_feature_relationships(self) -> None:
        """Create relationships between properties and features"""
        self.logger.info("Creating feature relationships...")
        
        # Process in batches to avoid memory issues
        # Optimized batch processing for feature relationships
        total_relationships = 0
        relationships = []
        
        # Collect all property-feature pairs
        for prop in self.properties:
            if not prop.features:
                continue
            
            for feature_name in prop.features:
                feature_id = feature_name.lower().replace(' ', '_').replace('-', '_')
                relationships.append({
                    'listing_id': prop.listing_id,
                    'feature_id': feature_id
                })
        
        # Create relationships in batches using UNWIND
        if relationships:
            batch_query = """
            UNWIND $batch AS rel
            MATCH (p:Property {listing_id: rel.listing_id})
            USING INDEX p:Property(listing_id)
            MATCH (f:Feature {feature_id: rel.feature_id})
            USING INDEX f:Feature(feature_id)
            MERGE (p)-[r:HAS_FEATURE]->(f)
            SET r.created_at = datetime()
            """
            
            batch_size = 500
            for i in range(0, len(relationships), batch_size):
                batch = relationships[i:i + batch_size]
                self.execute_query(batch_query, {'batch': batch})
                total_relationships += len(batch)
        
        self.load_result.feature_relationships = total_relationships
        self.logger.info(f"  Created {total_relationships} property->feature relationships")
    
    def _create_type_and_price_relationships(self) -> None:
        """Create property type and price range relationships"""
        self.logger.info("Creating property type and price range relationships...")
        
        # Create property type relationships
        query = """
        MATCH (p:Property)
        WHERE p.property_type IS NOT NULL AND p.property_type <> 'unknown'
        WITH p, 'type_' + replace(p.property_type, '-', '_') as type_id
        MATCH (pt:PropertyType {type_id: type_id})
        MERGE (p)-[r:OF_TYPE]->(pt)
        SET r.created_at = datetime()
        RETURN count(r) as count
        """
        result = self.execute_query(query)
        type_count = result[0]['count'] if result else 0
        self.load_result.type_relationships = type_count
        self.logger.info(f"  Created {type_count} property->type relationships")
        
        # Create price range relationships
        query = """
        MATCH (p:Property)
        WITH p,
             CASE
                WHEN p.listing_price < 500000 THEN 'range_0_500k'
                WHEN p.listing_price < 1000000 THEN 'range_500k_1m'
                WHEN p.listing_price < 2000000 THEN 'range_1m_2m'
                WHEN p.listing_price < 3000000 THEN 'range_2m_3m'
                WHEN p.listing_price < 5000000 THEN 'range_3m_5m'
                ELSE 'range_5m_plus'
             END as range_id
        MATCH (pr:PriceRange {range_id: range_id})
        MERGE (p)-[r:IN_PRICE_RANGE]->(pr)
        SET r.created_at = datetime()
        RETURN count(r) as count
        """
        result = self.execute_query(query)
        price_count = result[0]['count'] if result else 0
        self.load_result.price_range_relationships = price_count
        self.logger.info(f"  Created {price_count} property->price_range relationships")
    
    def _calculate_statistics(self) -> None:
        """Calculate statistics for the load result"""
        if self.properties:
            total_features = sum(len(p.features) for p in self.properties if p.features)
            self.load_result.avg_features_per_property = total_features / len(self.properties)
    
    def _create_wikipedia_property_relationships(self) -> None:
        """Create direct RELEVANT_TO relationships between Wikipedia articles and properties"""
        self.logger.info("Creating Wikipedia→Property relationships...")
        
        # Load neighborhood data to get Wikipedia metadata
        neighborhoods = []
        for path in [self.sf_path, self.pc_path]:
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                    for item in data:
                        neighborhoods.append(item)
        
        total_created = 0
        
        # For each neighborhood with Wikipedia metadata
        for neigh_data in neighborhoods:
            if 'graph_metadata' not in neigh_data:
                continue
            
            neighborhood_id = neigh_data['neighborhood_id']
            graph_meta = neigh_data['graph_metadata']
            
            # Get all Wikipedia page IDs for this neighborhood
            wiki_page_ids = []
            
            # Add primary Wikipedia article
            if graph_meta.get('primary_wiki_article'):
                wiki = graph_meta['primary_wiki_article']
                wiki_page_ids.append({
                    'page_id': wiki['page_id'],
                    'confidence': wiki.get('confidence', 0.8),
                    'rel_type': 'primary'
                })
            
            # Add related Wikipedia articles
            for wiki in graph_meta.get('related_wiki_articles', []):
                wiki_page_ids.append({
                    'page_id': wiki['page_id'],
                    'confidence': wiki.get('confidence', 0.7),
                    'rel_type': wiki.get('relationship', 'related')
                })
            
            # Create relationships for each Wikipedia article to all properties in neighborhood
            for wiki_info in wiki_page_ids:
                query = """
                MATCH (w:WikipediaArticle {page_id: $page_id})
                MATCH (p:Property {neighborhood_id: $neighborhood_id})
                MERGE (w)-[r:RELEVANT_TO]->(p)
                SET r.confidence = $confidence,
                    r.relationship_type = $rel_type,
                    r.neighborhood_context = true,
                    r.created_at = datetime()
                RETURN count(r) as created
                """
                
                result = self.execute_query(query, {
                    'page_id': wiki_info['page_id'],
                    'neighborhood_id': neighborhood_id,
                    'confidence': wiki_info['confidence'],
                    'rel_type': wiki_info['rel_type']
                })
                
                if result:
                    created = result[0]['created']
                    total_created += created
        
        self.logger.info(f"  Created {total_created} Wikipedia→Property relationships")
        self.load_result.wikipedia_property_relationships = total_created
    
    def _verify_integration(self) -> None:
        """Verify property integration"""
        self.logger.info("Verifying property integration...")
        
        # Count total nodes
        property_count = self.count_nodes("Property")
        feature_count = self.count_nodes("Feature")
        type_count = self.count_nodes("PropertyType")
        range_count = self.count_nodes("PriceRange")
        
        self.logger.info(f"  Total properties: {property_count}")
        self.logger.info(f"  Total features: {feature_count}")
        self.logger.info(f"  Total property types: {type_count}")
        self.logger.info(f"  Total price ranges: {range_count}")
        
        # Check connectivity
        query = """
        MATCH (p:Property)
        OPTIONAL MATCH (p)-[:IN_NEIGHBORHOOD]->(n:Neighborhood)
        OPTIONAL MATCH (p)-[:IN_CITY]->(c:City)
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
        RETURN 
            count(DISTINCT p) as total_properties,
            count(DISTINCT n) as connected_neighborhoods,
            count(DISTINCT c) as connected_cities,
            count(DISTINCT f) as connected_features
        """
        result = self.execute_query(query)
        if result:
            stats = result[0]
            self.logger.info(f"  Properties with neighborhoods: {stats['connected_neighborhoods']}")
            self.logger.info(f"  Properties with cities: {stats['connected_cities']}")
            self.logger.info(f"  Features in use: {stats['connected_features']}")