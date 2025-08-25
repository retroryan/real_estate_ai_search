"""Property loader with constructor injection"""

import logging
from typing import List, Dict, Set, Any
from datetime import datetime
from pydantic import BaseModel, Field

from src.core.query_executor import QueryExecutor
from src.core.config import PropertyConfig, LoaderConfig
from src.data_sources import PropertyFileDataSource
from src.models.property import (
    Property, PropertyDetails, Address, Coordinates,
    PropertyType as PropertyTypeEnum, PriceRange, Feature, PropertyLoadResult
)


class PropertyLoader:
    """Load properties with injected dependencies"""
    
    def __init__(
        self,
        query_executor: QueryExecutor,
        config: PropertyConfig,
        loader_config: LoaderConfig,
        data_source: PropertyFileDataSource
    ):
        """
        Initialize property loader with dependencies
        
        Args:
            query_executor: Database query executor
            config: Property configuration
            loader_config: Loader batch configuration
            data_source: Property data source
        """
        self.query_executor = query_executor
        self.config = config
        self.loader_config = loader_config
        self.data_source = data_source
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Collections for unique entities
        self.unique_features: Set[str] = set()
        self.unique_property_types: Set[str] = set()
        self.price_ranges = PriceRange.get_standard_ranges()
        
        # Load result tracking
        self.load_result = PropertyLoadResult()
    
    def load(self) -> PropertyLoadResult:
        """
        Main loading method
        
        Returns:
            PropertyLoadResult with statistics
        """
        self.logger.info("=" * 60)
        self.logger.info("PROPERTY LOADING AND CONNECTIONS")
        self.logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Load property data from data source
            properties = self._load_and_validate_properties()
            self.load_result.properties_loaded = len(properties)
            
            # Create constraints and indexes
            self._create_constraints_and_indexes()
            
            # Create price range nodes
            self._create_price_range_nodes()
            
            # Extract and create unique features
            self._create_feature_nodes()
            
            # Extract and create property type nodes
            self._create_property_type_nodes()
            
            # Create property nodes
            nodes_created = self._create_property_nodes(properties)
            self.load_result.property_nodes = nodes_created
            
            # Create geographic relationships
            self._create_geographic_relationships()
            
            # Create feature relationships
            self._create_feature_relationships(properties)
            
            # Create type and price relationships
            self._create_type_and_price_relationships()
            
            # Calculate statistics
            self._calculate_statistics(properties)
            
            # Verify the integration
            self._verify_integration()
            
            # Calculate duration
            self.load_result.duration_seconds = (datetime.now() - start_time).total_seconds()
            self.load_result.success = True
            
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
            self.load_result.success = False
            import traceback
            traceback.print_exc()
            return self.load_result
    
    def _load_and_validate_properties(self) -> List[Property]:
        """Load and validate property data from data source"""
        self.logger.info("Loading property data from data source...")
        
        properties = []
        raw_properties = self.data_source.load_properties()
        
        for item in raw_properties:
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
        
        self.logger.info(f"Total properties loaded: {len(properties)}")
        self.logger.info(f"Unique features found: {len(self.unique_features)}")
        self.logger.info(f"Unique property types: {len(self.unique_property_types)}")
        
        return properties
    
    def _create_constraints_and_indexes(self) -> None:
        """Create property-specific constraints and indexes"""
        self.logger.info("Creating property constraints and indexes...")
        
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
            self.query_executor.create_constraint(name, query)
        
        # Indexes for better query performance
        indexes = [
            ("Property.neighborhood_id",
             "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.neighborhood_id)"),
            ("Property.city",
             "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.city)"),
            ("Property.listing_price",
             "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.listing_price)"),
            ("Property.bedrooms",
             "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.bedrooms)"),
            ("Feature.category",
             "CREATE INDEX IF NOT EXISTS FOR (f:Feature) ON (f.category)"),
            ("Asset.listing_price",
             "CREATE INDEX IF NOT EXISTS FOR (a:Asset) ON (a.listing_price)"),
        ]
        
        for name, query in indexes:
            self.query_executor.create_index(name, query)
    
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
        
        created = self.query_executor.batch_execute(query, batch_data, self.loader_config.batch_size)
        self.load_result.price_range_nodes = created
        self.logger.info(f"  Created {created} price range nodes")
    
    def _create_feature_nodes(self) -> None:
        """Create feature nodes from unique features"""
        self.logger.info(f"Creating {len(self.unique_features)} feature nodes...")
        
        batch_data = []
        for feature_name in self.unique_features:
            feature_id = feature_name.lower().replace(' ', '_').replace('-', '_')
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
        
        created = self.query_executor.batch_execute(query, batch_data, self.loader_config.feature_batch_size)
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
        
        created = self.query_executor.batch_execute(query, batch_data, self.loader_config.batch_size)
        self.load_result.property_type_nodes = created
        self.load_result.unique_property_types = len(self.unique_property_types)
        self.logger.info(f"  Created {created} property type nodes")
    
    def _create_property_nodes(self, properties: List[Property]) -> int:
        """Create property nodes in database"""
        self.logger.info(f"Creating {len(properties)} property nodes...")
        
        batch_data = []
        for prop in properties:
            # Extract address components
            address_dict = {}
            if prop.address:
                address_dict = {
                    'street': prop.address.street,
                    'city': prop.address.city,
                    'county': prop.address.county,
                    'state': prop.address.state,
                    'zip': prop.address.zip
                }
            
            # Extract coordinates
            coords = prop.get_coordinates_dict()
            
            # Extract property details
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
        
        created = self.query_executor.batch_execute(query, batch_data, self.loader_config.property_batch_size)
        self.logger.info(f"  Created {created} property nodes")
        return created
    
    def _create_geographic_relationships(self) -> None:
        """Create relationships to neighborhoods, cities, and counties"""
        self.logger.info("Creating geographic relationships...")
        
        # Connect to neighborhoods
        query = """
        MATCH (p:Property)
        WHERE p.neighborhood_id IS NOT NULL 
          AND NOT EXISTS((p)-[:IN_NEIGHBORHOOD]->())
        WITH p
        MATCH (n:Neighborhood {neighborhood_id: p.neighborhood_id})
        MERGE (p)-[r:IN_NEIGHBORHOOD]->(n)
        SET r.created_at = datetime()
        RETURN count(r) as count
        """
        result = self.query_executor.execute_write(query)
        neighborhood_count = result[0]['count'] if result else 0
        self.load_result.neighborhood_relationships = neighborhood_count
        self.logger.info(f"  Created {neighborhood_count} property->neighborhood relationships")
        
        # Connect to cities
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
        result = self.query_executor.execute_write(query)
        city_count = result[0]['count'] if result else 0
        self.load_result.city_relationships = city_count
        self.logger.info(f"  Created {city_count} property->city relationships")
    
    def _create_feature_relationships(self, properties: List[Property]) -> None:
        """Create relationships between properties and features"""
        self.logger.info("Creating feature relationships...")
        
        relationships = []
        
        # Collect all property-feature pairs
        for prop in properties:
            if not prop.features:
                continue
            
            for feature_name in prop.features:
                feature_id = feature_name.lower().replace(' ', '_').replace('-', '_')
                relationships.append({
                    'listing_id': prop.listing_id,
                    'feature_id': feature_id
                })
        
        # Create relationships in batches
        if relationships:
            batch_query = """
            UNWIND $batch AS rel
            MATCH (p:Property {listing_id: rel.listing_id})
            MATCH (f:Feature {feature_id: rel.feature_id})
            MERGE (p)-[r:HAS_FEATURE]->(f)
            SET r.created_at = datetime()
            """
            
            batch_size = 500
            total_created = 0
            for i in range(0, len(relationships), batch_size):
                batch = relationships[i:i + batch_size]
                self.query_executor.execute_write(batch_query, {'batch': batch})
                total_created += len(batch)
            
            self.load_result.feature_relationships = total_created
            self.logger.info(f"  Created {total_created} property->feature relationships")
    
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
        result = self.query_executor.execute_write(query)
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
        result = self.query_executor.execute_write(query)
        price_count = result[0]['count'] if result else 0
        self.load_result.price_range_relationships = price_count
        self.logger.info(f"  Created {price_count} property->price_range relationships")
    
    def _calculate_statistics(self, properties: List[Property]) -> None:
        """Calculate statistics for the load result"""
        if properties:
            total_features = sum(len(p.features) for p in properties if p.features)
            self.load_result.avg_features_per_property = total_features / len(properties)
    
    def _verify_integration(self) -> None:
        """Verify property integration"""
        self.logger.info("Verifying property integration...")
        
        # Count total nodes
        property_count = self.query_executor.count_nodes("Property")
        feature_count = self.query_executor.count_nodes("Feature")
        type_count = self.query_executor.count_nodes("PropertyType")
        range_count = self.query_executor.count_nodes("PriceRange")
        
        self.logger.info(f"  Total properties: {property_count}")
        self.logger.info(f"  Total features: {feature_count}")
        self.logger.info(f"  Total property types: {type_count}")
        self.logger.info(f"  Total price ranges: {range_count}")