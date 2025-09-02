"""Graph database initialization utilities - extracted from graph_archive/controllers/graph_builder.py"""

from typing import Optional
from neo4j import Driver
from graph_real_estate.utils.database import get_neo4j_driver, close_neo4j_driver, run_query, clear_database


class GraphDatabaseInitializer:
    """Initialize Neo4j database with schema, constraints, and indexes"""
    
    def __init__(self, driver: Optional[Driver] = None):
        """
        Initialize the graph database initializer
        
        Args:
            driver: Optional Neo4j driver instance. If not provided, creates one.
        """
        self.driver = driver if driver else get_neo4j_driver()
    
    def test_connection(self) -> bool:
        """
        Test Neo4j connectivity
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            result = run_query(self.driver, "RETURN 1 as test")
            print("✓ Neo4j connection successful")
            return True
        except Exception as e:
            print(f"✗ Neo4j connection failed: {e}")
            return False
    
    def clear_database(self) -> None:
        """Clear all existing data from the database"""
        print("\nClearing database...")
        clear_database(self.driver)
        print("✓ Database cleared")
    
    def _create_vector_indexes(self, dimension: int = 1024) -> None:
        """
        Create vector indexes for embeddings.
        
        Args:
            dimension: Embedding dimension (default 1024 for nomic-embed-text)
        """
        # Define vector indexes to create
        vector_indexes = [
            ("property_embedding", "Property", "embedding"),
            ("neighborhood_embedding", "Neighborhood", "embedding"),
            ("wikipedia_embedding", "Wikipedia", "embedding")
        ]
        
        for index_name, label, field in vector_indexes:
            # Create vector index
            vector_index_query = f"""
            CREATE VECTOR INDEX {index_name} IF NOT EXISTS
            FOR (n:{label})
            ON n.{field}
            OPTIONS {{ indexConfig: {{
                `vector.dimensions`: {dimension},
                `vector.similarity_function`: 'cosine'
            }}}}
            """
            
            try:
                run_query(self.driver, vector_index_query)
                print(f"  ✓ Vector index created: {index_name} on {label}.{field} (dimensions: {dimension})")
            except Exception as e:
                print(f"  ⚠ Vector index {index_name}: {e}")
    
    def create_constraints_and_indexes(self) -> None:
        """Create all necessary constraints and indexes including vector indexes"""
        print("\nCreating constraints and indexes...")
        
        # Define constraints
        constraints = [
            ("property_id", "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Property) REQUIRE p.listing_id IS UNIQUE"),
            ("neighborhood_id", "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Neighborhood) REQUIRE n.neighborhood_id IS UNIQUE"),
            ("city_id", "CREATE CONSTRAINT IF NOT EXISTS FOR (c:City) REQUIRE c.city_id IS UNIQUE"),
            ("county_id", "CREATE CONSTRAINT IF NOT EXISTS FOR (co:County) REQUIRE co.county_id IS UNIQUE"),
            ("state_id", "CREATE CONSTRAINT IF NOT EXISTS FOR (s:State) REQUIRE s.state_id IS UNIQUE"),
            ("wikipedia_id", "CREATE CONSTRAINT IF NOT EXISTS FOR (w:Wikipedia) REQUIRE w.page_id IS UNIQUE"),
            ("feature_name", "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Feature) REQUIRE f.name IS UNIQUE"),
            ("price_range", "CREATE CONSTRAINT IF NOT EXISTS FOR (pr:PriceRange) REQUIRE pr.range IS UNIQUE"),
            ("property_type", "CREATE CONSTRAINT IF NOT EXISTS FOR (pt:PropertyType) REQUIRE pt.name IS UNIQUE")
        ]
        
        # Create constraints
        for name, constraint in constraints:
            try:
                run_query(self.driver, constraint)
                print(f"  ✓ Constraint created: {name}")
            except Exception as e:
                print(f"  ⚠ Constraint {name} may already exist: {e}")
        
        # Define indexes for performance
        indexes = [
            ("property_price", "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.listing_price)"),
            ("property_type", "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.property_type)"),
            ("property_bedrooms", "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.bedrooms)"),
            ("property_city", "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.city)"),
            ("property_state", "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.state)"),
            ("neighborhood_city", "CREATE INDEX IF NOT EXISTS FOR (n:Neighborhood) ON (n.city)"),
            ("neighborhood_state", "CREATE INDEX IF NOT EXISTS FOR (n:Neighborhood) ON (n.state)"),
            ("neighborhood_walkability", "CREATE INDEX IF NOT EXISTS FOR (n:Neighborhood) ON (n.walkability_score)"),
            ("wikipedia_type", "CREATE INDEX IF NOT EXISTS FOR (w:Wikipedia) ON (w.relationship_type)"),
            ("wikipedia_confidence", "CREATE INDEX IF NOT EXISTS FOR (w:Wikipedia) ON (w.confidence)"),
            ("city_state", "CREATE INDEX IF NOT EXISTS FOR (c:City) ON (c.state)"),
            ("county_state", "CREATE INDEX IF NOT EXISTS FOR (co:County) ON (co.state)")
        ]
        
        # Create indexes
        for name, index in indexes:
            try:
                run_query(self.driver, index)
                print(f"  ✓ Index created: {name}")
            except Exception as e:
                print(f"  ⚠ Index {name}: {e}")
        
        # Create vector indexes for embeddings
        self._create_vector_indexes(1024)
    
    def initialize_database(self, clear: bool = False) -> bool:
        """
        Initialize the database with schema, constraints, and indexes
        
        Args:
            clear: If True, clear the database before initialization
            
        Returns:
            True if initialization successful, False otherwise
        """
        print("\n" + "="*60)
        print("DATABASE INITIALIZATION")
        print("="*60)
        
        # Test connection
        if not self.test_connection():
            return False
        
        # Clear database if requested
        if clear:
            self.clear_database()
        
        # Create constraints and indexes
        self.create_constraints_and_indexes()
        
        print("\n" + "="*60)
        print("✓ Database initialization complete")
        print("="*60)
        
        return True
    
    def get_stats(self) -> dict:
        """
        Get database statistics
        
        Returns:
            Dictionary containing database statistics
        """
        stats = {}
        
        # Get node counts by label
        node_labels = ['Property', 'Neighborhood', 'City', 'County', 'State', 
                      'Wikipedia', 'Feature', 'PriceRange', 'PropertyType']
        
        for label in node_labels:
            query = f"MATCH (n:{label}) RETURN count(n) as count"
            result = run_query(self.driver, query)
            stats[f'nodes_{label}'] = result[0]['count'] if result else 0
        
        # Get relationship counts by type
        rel_types = ['LOCATED_IN', 'IN_CITY', 'IN_COUNTY', 'IN_STATE',
                    'DESCRIBES', 'HAS_FEATURE', 'IN_PRICE_RANGE', 'TYPE_OF',
                    'NEAR']
        
        for rel_type in rel_types:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
            result = run_query(self.driver, query)
            stats[f'relationships_{rel_type}'] = result[0]['count'] if result else 0
        
        # Get totals
        query = "MATCH (n) RETURN count(n) as count"
        result = run_query(self.driver, query)
        stats['total_nodes'] = result[0]['count'] if result else 0
        
        query = "MATCH ()-[r]->() RETURN count(r) as count"
        result = run_query(self.driver, query)
        stats['total_relationships'] = result[0]['count'] if result else 0
        
        return stats
    
    def print_stats(self) -> None:
        """Print database statistics"""
        stats = self.get_stats()
        
        print("\n" + "="*60)
        print("DATABASE STATISTICS")
        print("="*60)
        
        print("\n📊 NODE COUNTS:")
        node_labels = ['Property', 'Neighborhood', 'City', 'County', 'State', 
                      'Wikipedia', 'Feature', 'PriceRange', 'PropertyType']
        for label in node_labels:
            count = stats.get(f'nodes_{label}', 0)
            if count > 0:
                print(f"  {label}: {count}")
        
        print("\n🔗 RELATIONSHIP COUNTS:")
        rel_types = ['LOCATED_IN', 'IN_CITY', 'IN_COUNTY', 'IN_STATE',
                    'DESCRIBES', 'HAS_FEATURE', 'IN_PRICE_RANGE', 'TYPE_OF',
                    'NEAR']
        for rel_type in rel_types:
            count = stats.get(f'relationships_{rel_type}', 0)
            if count > 0:
                print(f"  {rel_type}: {count}")
        
        print("\n📈 TOTALS:")
        print(f"  Total nodes: {stats.get('total_nodes', 0)}")
        print(f"  Total relationships: {stats.get('total_relationships', 0)}")
        
        print("="*60)
    
    def clear_database_complete(self) -> None:
        """Clear all data, relationships, indexes, and constraints from the database"""
        print("\nClearing database completely...")
        
        try:
            # Delete all relationships first
            query = "MATCH ()-[r]->() DELETE r RETURN COUNT(r) as count"
            result = run_query(self.driver, query)
            rel_count = result[0]['count'] if result and result else 0
            print(f"Deleted {rel_count} relationships")
            
            # Delete all nodes
            query = "MATCH (n) DELETE n RETURN COUNT(n) as count"
            result = run_query(self.driver, query)
            node_count = result[0]['count'] if result and result else 0
            print(f"Deleted {node_count} nodes")
            
            # Drop all constraints
            constraints = run_query(self.driver, "SHOW CONSTRAINTS")
            if constraints:
                for constraint in constraints:
                    try:
                        run_query(self.driver, f"DROP CONSTRAINT {constraint['name']}")
                    except Exception as e:
                        print(f"  Warning: Could not drop constraint {constraint.get('name', 'unknown')}: {e}")
                print(f"Dropped {len(constraints)} constraints")
            
            # Drop all indexes
            indexes = run_query(self.driver, 'SHOW INDEXES WHERE type <> "LOOKUP"')
            if indexes:
                for index in indexes:
                    try:
                        run_query(self.driver, f"DROP INDEX {index['name']}")
                    except Exception as e:
                        # Some indexes may be tied to constraints, which is OK
                        pass
                print(f"Dropped {len(indexes)} indexes")
            
            print("✓ Database cleared completely")
        except Exception as e:
            print(f"✗ Error clearing database: {e}")
            raise
    
    def run_sample_query(self) -> None:
        """Run a sample query to verify data"""
        print("\nRunning sample query...")
        
        try:
            query = """
            MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
            WITH p, n
            OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
            WITH p, n, COLLECT(f.name) as features
            RETURN 
                p.listing_id as listing_id,
                p.listing_price as price,
                p.bedrooms as bedrooms,
                p.bathrooms as bathrooms,
                p.square_feet as sqft,
                n.name as neighborhood,
                features
            LIMIT 3
            """
            
            results = run_query(self.driver, query)
            
            if not results:
                print("\n⚠ No properties found in the database")
                print("  Please load data using the pipeline first")
                return
            
            print("\nSample Properties:")
            print("-" * 80)
            for record in results:
                print(f"Property ID: {record.get('listing_id', 'N/A')}")
                price = record.get('price', 0)
                if price:
                    print(f"  Price: ${price:,.0f}")
                else:
                    print(f"  Price: N/A")
                print(f"  Bedrooms: {record.get('bedrooms', 'N/A')}, Bathrooms: {record.get('bathrooms', 'N/A')}")
                sqft = record.get('sqft', 0)
                if sqft:
                    print(f"  Square Feet: {sqft:,.0f}")
                else:
                    print(f"  Square Feet: N/A")
                print(f"  Neighborhood: {record.get('neighborhood', 'N/A')}")
                if record.get('features'):
                    features_display = record['features'][:5]
                    if len(record['features']) > 5:
                        features_display.append(f"... and {len(record['features']) - 5} more")
                    print(f"  Features: {', '.join(features_display)}")
                print()
            
            print("✓ Sample query completed")
        except Exception as e:
            print(f"✗ Error running sample query: {e}")
    
    def show_detailed_stats(self) -> None:
        """Show detailed database statistics including health check"""
        from datetime import datetime
        
        print(f"\nDatabase Status Report")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Node counts
        print("\n📊 Node Statistics:")
        node_labels = [
            'Property', 'Neighborhood', 'WikipediaArticle',
            'Feature', 'PropertyType', 'PriceRange',
            'City', 'State', 'ZipCode'
        ]
        
        total_nodes = 0
        for label in node_labels:
            query = f"MATCH (n:{label}) RETURN COUNT(n) as count"
            result = run_query(self.driver, query)
            count = result[0]['count'] if result else 0
            total_nodes += count
            if count > 0:
                print(f"  {label:20} {count:>10,} nodes")
        
        print(f"  {'TOTAL':20} {total_nodes:>10,} nodes")
        
        # Relationship counts
        print("\n🔗 Relationship Statistics:")
        rel_types = [
            'LOCATED_IN', 'HAS_FEATURE', 'IN_CITY', 'IN_STATE',
            'IN_ZIP_CODE', 'TYPE_OF', 'IN_PRICE_RANGE',
            'NEAR', 'DESCRIBES'
        ]
        
        total_rels = 0
        for rel_type in rel_types:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN COUNT(r) as count"
            result = run_query(self.driver, query)
            count = result[0]['count'] if result else 0
            total_rels += count
            if count > 0:
                print(f"  {rel_type:20} {count:>10,} relationships")
        
        print(f"  {'TOTAL':20} {total_rels:>10,} relationships")
        
        # Constraints and Indexes
        print("\n🔐 Constraints:")
        constraints = run_query(self.driver, "SHOW CONSTRAINTS")
        for i, constraint in enumerate(constraints[:5]):
            print(f"  • {constraint['name']}")
        if len(constraints) > 5:
            print(f"  ... and {len(constraints) - 5} more")
        
        print("\n🔍 Indexes:")
        indexes = run_query(self.driver, 'SHOW INDEXES WHERE type <> "LOOKUP"')
        for i, index in enumerate(indexes[:5]):
            print(f"  • {index['name']} ({index.get('state', 'N/A')})")
        if len(indexes) > 5:
            print(f"  ... and {len(indexes) - 5} more")
        
        # Health check
        print("\n✅ Health Status:")
        if total_nodes > 0:
            print("  Database:     HEALTHY")
            print("  Connectivity: OK")
            print(f"  Data Present: YES ({total_nodes:,} nodes)")
        else:
            print("  Database:     EMPTY")
            print("  Connectivity: OK")
            print("  Data Present: NO")
    
    def close(self) -> None:
        """Close database connection"""
        if self.driver:
            close_neo4j_driver(self.driver)
            print("✓ Database connection closed")