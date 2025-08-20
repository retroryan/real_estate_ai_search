"""Graph builder controller for real estate data"""
from typing import List, Dict, Any
from src.database import get_neo4j_driver, close_neo4j_driver, run_query, clear_database, print_stats
from src.data_loader import (
    load_property_data, 
    validate_property_data, 
    get_unique_neighborhoods, 
    get_unique_features,
    get_unique_cities
)
from src.models import Property, PropertyDetails, Neighborhood, City, Feature, PriceRange, GraphStats

class RealEstateGraphBuilder:
    """Main controller for building the real estate graph database"""
    
    def __init__(self):
        """Initialize the graph builder with database connection and data"""
        self.driver = get_neo4j_driver()
        self.data = load_property_data()
        self.stats = GraphStats()
        
    def setup_environment(self) -> bool:
        """Environment Setup & Data Preparation with Pydantic validation"""
        print("\n" + "="*60)
        print("ENVIRONMENT SETUP & DATA PREPARATION")
        print("="*60)
        print("Using Pydantic for data validation and type safety")
        
        # Test Neo4j connectivity
        try:
            result = run_query(self.driver, "RETURN 1 as test")
            print("✓ Neo4j connection successful")
        except Exception as e:
            print(f"✗ Neo4j connection failed: {e}")
            return False
        
        # Report loaded data (already validated by Pydantic)
        print(f"\n✓ Loaded {len(self.data['sf'])} SF properties (Pydantic validated)")
        print(f"✓ Loaded {len(self.data['pc'])} Park City properties (Pydantic validated)")
        print(f"✓ Total properties: {len(self.data['all'])}")
        
        # Validate data structure
        print("\nValidating data structure with Pydantic...")
        sf_valid = validate_property_data(self.data['sf'])
        pc_valid = validate_property_data(self.data['pc'])
        
        if sf_valid and pc_valid:
            print("\n✓ Environment Setup Complete: Ready with Pydantic validation")
            return True
        else:
            print("\n⚠ Environment Setup: Some validation warnings (continuing anyway)")
            return True
    
    def create_schema(self) -> bool:
        """Core Graph Schema Implementation with Pydantic models"""
        print("\n" + "="*60)
        print("CORE GRAPH SCHEMA IMPLEMENTATION")
        print("="*60)
        
        # Clear existing data
        print("Clearing existing data...")
        clear_database(self.driver)
        
        # Create constraints and indexes
        print("Creating constraints and indexes...")
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Property) REQUIRE p.listing_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Neighborhood) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:City) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Feature) REQUIRE f.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (pr:PriceRange) REQUIRE pr.range IS UNIQUE"
        ]
        
        for constraint in constraints:
            try:
                run_query(self.driver, constraint)
            except Exception as e:
                # Constraint might already exist
                pass
        
        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.neighborhood_id)",
            "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.listing_price)",
            "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.property_type)",
            "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.city)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Neighborhood) ON (n.city)"
        ]
        
        for index in indexes:
            run_query(self.driver, index)
        
        print("✓ Constraints and indexes created")
        
        # Create Cities using Pydantic models
        print("\nCreating geographic hierarchy...")
        cities = get_unique_cities(self.data['all'])
        
        for city in cities:
            query = """
            MERGE (c:City {name: $name})
            SET c.state = $state
            """
            # Use Pydantic model fields directly
            run_query(self.driver, query, {'name': city.name, 'state': city.state})
        
        print(f"✓ {len(cities)} Cities created")
        
        # Create Neighborhoods using Pydantic models
        neighborhoods = get_unique_neighborhoods(self.data['all'])
        print(f"Creating {len(neighborhoods)} neighborhoods...")
        
        for neighborhood in neighborhoods:
            query = """
            MATCH (c:City {name: $city})
            MERGE (n:Neighborhood {id: $id})
            SET n.name = $name, n.city = $city, n.state = $state
            MERGE (n)-[:PART_OF]->(c)
            """
            # Use Pydantic model fields directly
            params = {
                'id': neighborhood.id,
                'name': neighborhood.name,
                'city': neighborhood.city,
                'state': neighborhood.state
            }
            run_query(self.driver, query, params)
        
        print("✓ Neighborhoods created and linked to cities")
        
        # Create PriceRange nodes
        for price_range in PriceRange:
            query = "MERGE (pr:PriceRange {range: $range})"
            run_query(self.driver, query, {'range': price_range.value})
        
        print("✓ Price ranges created")
        
        # Load Property nodes using Pydantic models directly
        print(f"\nLoading {len(self.data['all'])} properties...")
        
        for prop in self.data['all']:
            # Use Pydantic model directly with typed methods
            price_range = prop.calculate_price_range()
            coords = prop.get_coordinates_dict()  # This is needed for Neo4j compatibility
            
            # Create property and link to neighborhood and price range
            query = """
            MATCH (n:Neighborhood {id: $neighborhood_id})
            MATCH (pr:PriceRange {range: $price_range})
            CREATE (p:Property {
                listing_id: $listing_id,
                neighborhood_id: $neighborhood_id,
                address: $address,
                listing_price: $listing_price,
                property_type: $property_type,
                bedrooms: $bedrooms,
                bathrooms: $bathrooms,
                square_feet: $square_feet,
                year_built: $year_built,
                description: $description,
                latitude: $latitude,
                longitude: $longitude,
                price_per_sqft: $price_per_sqft,
                listing_date: $listing_date,
                city: $city,
                state: $state
            })
            CREATE (p)-[:LOCATED_IN]->(n)
            CREATE (p)-[:IN_PRICE_RANGE]->(pr)
            """
            
            # Use Pydantic model methods and fields directly - no dict operations
            params = {
                'neighborhood_id': prop.neighborhood_id,
                'price_range': price_range,
                'listing_id': prop.listing_id,
                'address': prop.get_address_string(),
                'listing_price': prop.listing_price,
                'property_type': prop.get_property_type(),  # Using typed method
                'bedrooms': prop.get_bedrooms(),             # Using typed method
                'bathrooms': prop.get_bathrooms(),           # Using typed method
                'square_feet': prop.get_square_feet(),       # Using typed method
                'year_built': prop.get_year_built(),         # Using typed method
                'description': prop.description or '',
                'latitude': coords.get('lat', 0),  # coords dict needed for Neo4j
                'longitude': coords.get('lng', 0), # coords dict needed for Neo4j
                'price_per_sqft': prop.price_per_sqft or 0,
                'listing_date': prop.listing_date or '',
                'city': prop.city or '',
                'state': prop.state or ''
            }
            
            run_query(self.driver, query, params)
        
        print("✓ Properties loaded and linked")
        
        # Create PropertyType nodes using Pydantic model methods
        property_types = set()
        for prop in self.data['all']:
            # Use typed method to get property type
            prop_type = prop.get_property_type()
            if prop_type:
                property_types.add(prop_type)
        
        for pt in property_types:
            query = "MERGE (pt:PropertyType {name: $name})"
            run_query(self.driver, query, {'name': pt})
            
            # Link properties to their types
            query = """
            MATCH (p:Property {property_type: $type})
            MATCH (pt:PropertyType {name: $type})
            MERGE (p)-[:TYPE_OF]->(pt)
            """
            run_query(self.driver, query, {'type': pt})
        
        print(f"✓ {len(property_types)} Property types created and linked")
        
        print_stats(self.driver)
        print("\n✓ Schema Creation Complete: Core graph schema implemented with Pydantic models")
        return True
    
    def create_relationships(self) -> bool:
        """Create Graph Relationships with Pydantic validation"""
        print("\n" + "="*60)
        print("GRAPH RELATIONSHIPS CREATION")
        print("="*60)
        
        # Extract and create Feature nodes using Pydantic models
        print("Creating feature nodes with categories...")
        features = get_unique_features(self.data['all'])
        print(f"Found {len(features)} unique features")
        
        # Group features by category for reporting
        categories = {}
        for feature in features:
            query = "MERGE (f:Feature {name: $name}) SET f.category = $category"
            # Use Pydantic model fields directly
            run_query(self.driver, query, {'name': feature.name, 'category': feature.category})
            
            # Track categories
            cat = feature.category or 'Other'
            categories[cat] = categories.get(cat, 0) + 1
        
        print("Feature categories created:")
        for cat, count in sorted(categories.items()):
            print(f"  - {cat}: {count} features")
        
        # Link properties to features
        print("\nLinking properties to features...")
        feature_links = 0
        for prop in self.data['all']:
            if prop.features:
                for feature_name in prop.features:
                    query = """
                    MATCH (p:Property {listing_id: $listing_id})
                    MATCH (f:Feature {name: $feature})
                    MERGE (p)-[:HAS_FEATURE]->(f)
                    """
                    run_query(self.driver, query, {
                        'listing_id': prop.listing_id,
                        'feature': feature_name
                    })
                    feature_links += 1
        
        print(f"✓ Created {feature_links} property-feature relationships")
        
        # Calculate and create similarity relationships
        print("\nCalculating property similarities...")
        
        # Enhanced similarity calculation using multiple factors
        query = """
        MATCH (p1:Property)-[:LOCATED_IN]->(n:Neighborhood)<-[:LOCATED_IN]-(p2:Property)
        WHERE p1.listing_id < p2.listing_id
        AND abs(p1.listing_price - p2.listing_price) / p1.listing_price < 0.2
        AND p1.property_type = p2.property_type
        AND abs(p1.bedrooms - p2.bedrooms) <= 1
        AND abs(p1.square_feet - p2.square_feet) / p1.square_feet < 0.3
        WITH p1, p2, 
             (1.0 - abs(p1.listing_price - p2.listing_price) / p1.listing_price) * 0.4 +
             (1.0 - abs(p1.square_feet - p2.square_feet) / p1.square_feet) * 0.3 +
             (CASE WHEN p1.bedrooms = p2.bedrooms THEN 0.2 ELSE 0.1 END) +
             (CASE WHEN p1.bathrooms = p2.bathrooms THEN 0.1 ELSE 0.0 END) as similarity_score
        WHERE similarity_score > 0.5
        CREATE (p1)-[:SIMILAR_TO {score: similarity_score}]->(p2)
        CREATE (p2)-[:SIMILAR_TO {score: similarity_score}]->(p1)
        """
        
        run_query(self.driver, query)
        
        # Count similarities created
        query = "MATCH ()-[r:SIMILAR_TO]->() RETURN count(DISTINCT r) as count"
        result = run_query(self.driver, query)
        sim_count = result[0]['count'] if result else 0
        
        print(f"✓ Created {sim_count} similarity relationships")
        
        # Create neighborhood connections (adjacent neighborhoods in same city)
        print("\nCreating neighborhood connections...")
        
        # Connect neighborhoods in the same city
        query = """
        MATCH (n1:Neighborhood)-[:PART_OF]->(c:City)<-[:PART_OF]-(n2:Neighborhood)
        WHERE n1.id < n2.id
        MERGE (n1)-[:NEAR]->(n2)
        MERGE (n2)-[:NEAR]->(n1)
        """
        run_query(self.driver, query)
        
        # Count neighborhood connections
        query = "MATCH (n1:Neighborhood)-[r:NEAR]->(n2:Neighborhood) RETURN count(DISTINCT r) as count"
        result = run_query(self.driver, query)
        near_count = result[0]['count'] if result else 0
        
        print(f"✓ Created {near_count} neighborhood connections")
        
        print_stats(self.driver)
        print("\n✓ Relationship Creation Complete: Graph relationships established with Pydantic validation")
        return True
    
    def run_sample_queries(self):
        """Run sample queries to demonstrate the graph"""
        from src.demos import QueryDemonstrator
        
        demonstrator = QueryDemonstrator(self.driver)
        demonstrator.run_phase4_queries()
    
    def close(self):
        """Close database connection"""
        close_neo4j_driver(self.driver)