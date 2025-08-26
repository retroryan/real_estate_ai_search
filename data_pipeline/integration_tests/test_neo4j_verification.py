"""
Neo4j Database Verification Integration Test

Verifies that the Neo4j database was properly populated with nodes and embeddings
after running the data pipeline with neo4j.config.yaml.
"""

import os
import pytest
from dotenv import load_dotenv
from neo4j import GraphDatabase
from typing import Dict, Any, Optional


class TestNeo4jVerification:
    """Integration test for Neo4j database verification."""
    
    @classmethod
    def setup_class(cls):
        """Set up Neo4j connection for all tests."""
        # Load environment variables
        load_dotenv()
        
        # Neo4j connection parameters
        cls.uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        cls.username = os.getenv('NEO4J_USERNAME', 'neo4j')
        cls.password = os.getenv('NEO4J_PASSWORD')
        
        if not cls.password:
            pytest.skip("NEO4J_PASSWORD not set - skipping Neo4j tests")
        
        # Create driver
        try:
            cls.driver = GraphDatabase.driver(cls.uri, auth=(cls.username, cls.password))
            # Test connection
            with cls.driver.session() as session:
                session.run("RETURN 1").single()
        except Exception as e:
            pytest.skip(f"Cannot connect to Neo4j: {e}")
    
    @classmethod
    def teardown_class(cls):
        """Clean up Neo4j connection."""
        if hasattr(cls, 'driver'):
            cls.driver.close()
    
    def get_node_counts(self) -> Dict[str, int]:
        """Get counts of all node types in the database."""
        node_queries = [
            ('Property', 'MATCH (p:Property) RETURN count(p) as count'),
            ('Neighborhood', 'MATCH (n:Neighborhood) RETURN count(n) as count'),
            ('WikipediaArticle', 'MATCH (w:WikipediaArticle) RETURN count(w) as count'),
            ('Feature', 'MATCH (f:Feature) RETURN count(f) as count'),
            ('PropertyType', 'MATCH (pt:PropertyType) RETURN count(pt) as count'),
            ('PriceRange', 'MATCH (pr:PriceRange) RETURN count(pr) as count'),
            ('County', 'MATCH (c:County) RETURN count(c) as count'),
            ('TopicCluster', 'MATCH (tc:TopicCluster) RETURN count(tc) as count'),
            ('City', 'MATCH (city:City) RETURN count(city) as count'),
            ('State', 'MATCH (s:State) RETURN count(s) as count')
        ]
        
        counts = {}
        with self.driver.session() as session:
            for node_type, query in node_queries:
                result = session.run(query)
                record = result.single()
                counts[node_type] = record['count'] if record else 0
        
        return counts
    
    def get_embedding_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get embedding statistics for each entity type."""
        embedding_queries = [
            ('Property', 'MATCH (p:Property) WHERE p.embedding IS NOT NULL RETURN count(p) as count, avg(size(p.embedding)) as avg_size'),
            ('Neighborhood', 'MATCH (n:Neighborhood) WHERE n.embedding IS NOT NULL RETURN count(n) as count, avg(size(n.embedding)) as avg_size'),
            ('WikipediaArticle', 'MATCH (w:WikipediaArticle) WHERE w.embedding IS NOT NULL RETURN count(w) as count, avg(size(w.embedding)) as avg_size')
        ]
        
        stats = {}
        with self.driver.session() as session:
            for entity_type, query in embedding_queries:
                result = session.run(query)
                record = result.single()
                if record and record['count'] > 0:
                    stats[entity_type] = {
                        'count': record['count'],
                        'avg_dimensions': int(record['avg_size']) if record['avg_size'] else 0
                    }
                else:
                    stats[entity_type] = {'count': 0, 'avg_dimensions': 0}
        
        return stats
    
    def get_sample_data(self) -> Dict[str, list]:
        """Get sample data to verify content quality."""
        samples = {}
        
        with self.driver.session() as session:
            # Sample properties
            result = session.run("""
                MATCH (p:Property) 
                RETURN p.street as address, p.listing_id as listing_id, p.city as city, p.state as state, 
                       p.property_type as property_type, p.listing_price as listing_price, 
                       p.embedding IS NOT NULL as has_embedding
                LIMIT 3
            """)
            samples['properties'] = [dict(record) for record in result]
            
            # Sample neighborhoods  
            result = session.run("""
                MATCH (n:Neighborhood)
                RETURN n.name as name, n.city as city, n.state as state, n.description as description,
                       n.embedding IS NOT NULL as has_embedding
                LIMIT 3
            """)
            samples['neighborhoods'] = [dict(record) for record in result]
            
            # Sample Wikipedia articles
            result = session.run("""
                MATCH (w:WikipediaArticle)
                RETURN w.title as title, w.best_city as best_city, w.best_state as best_state, w.confidence as confidence,
                       w.embedding IS NOT NULL as has_embedding
                LIMIT 3
            """)
            samples['wikipedia'] = [dict(record) for record in result]
        
        return samples
    
    def test_database_has_nodes(self):
        """Test that the database contains the expected node types."""
        print("\n=== TESTING NODE COUNTS ===")
        counts = self.get_node_counts()
        
        for node_type, count in counts.items():
            print(f"{node_type}: {count}")
        
        # Core entities should exist if pipeline ran successfully
        core_entities = ['Property', 'Neighborhood', 'WikipediaArticle']
        for entity in core_entities:
            assert counts[entity] > 0, f"No {entity} nodes found - pipeline may not have run successfully"
        
        # Extracted entities should exist if pipeline completed entity extraction
        extracted_entities = ['Feature', 'PropertyType', 'PriceRange']
        for entity in extracted_entities:
            if counts[entity] == 0:
                print(f"Warning: No {entity} nodes found - entity extraction may not have completed")
    
    def test_embeddings_present(self):
        """Test that embeddings were generated and stored correctly."""
        print("\n=== TESTING EMBEDDINGS ===")
        stats = self.get_embedding_stats()
        
        for entity_type, data in stats.items():
            count = data['count']
            avg_dims = data['avg_dimensions']
            print(f"{entity_type}: {count} with embeddings (avg {avg_dims} dimensions)")
        
        # At least some core entities should have embeddings
        core_with_embeddings = ['Property', 'Neighborhood', 'WikipediaArticle']
        embeddings_found = False
        
        for entity in core_with_embeddings:
            if stats[entity]['count'] > 0:
                embeddings_found = True
                # Check that embedding dimensions are reasonable (should be 1024 for voyage-3)
                avg_dims = stats[entity]['avg_dimensions']
                assert avg_dims > 0, f"{entity} embeddings have 0 dimensions"
                assert avg_dims >= 512, f"{entity} embeddings too small ({avg_dims} dims) - may be corrupted"
                assert avg_dims <= 2048, f"{entity} embeddings too large ({avg_dims} dims) - unexpected model"
                print(f"✅ {entity} embeddings verified: {stats[entity]['count']} nodes, {avg_dims} dimensions")
        
        if not embeddings_found:
            pytest.fail("No embeddings found in any core entities - embedding generation may have failed")
    
    def test_data_quality(self):
        """Test that the stored data has reasonable quality."""
        print("\n=== TESTING DATA QUALITY ===")
        samples = self.get_sample_data()
        
        # Test properties
        properties = samples['properties']
        assert len(properties) > 0, "No property samples found"
        
        for prop in properties:
            assert prop['address'], "Property missing address"
            assert prop['listing_id'], "Property missing listing_id"  
            assert prop['city'], "Property missing city"
            assert prop['state'], "Property missing state"
            assert prop['listing_price'] is not None, "Property missing listing_price"
            print(f"✅ Property {prop['listing_id']} at {prop['address']} in {prop['city']}, {prop['state']}: ${prop['listing_price']:,}")
            print(f"   Type: {prop['property_type']}, Has embedding: {prop['has_embedding']}")
        
        # Test neighborhoods
        neighborhoods = samples['neighborhoods'] 
        assert len(neighborhoods) > 0, "No neighborhood samples found"
        
        for neighborhood in neighborhoods:
            assert neighborhood['name'], "Neighborhood missing name"
            assert neighborhood['city'], "Neighborhood missing city"
            assert neighborhood['state'], "Neighborhood missing state"
            print(f"✅ Neighborhood {neighborhood['name']} in {neighborhood['city']}, {neighborhood['state']}")
            print(f"   Has embedding: {neighborhood['has_embedding']}")
        
        # Test Wikipedia articles
        wikipedia = samples['wikipedia']
        assert len(wikipedia) > 0, "No Wikipedia samples found"
        
        for article in wikipedia:
            assert article['title'], "Wikipedia article missing title"
            print(f"✅ Wikipedia: {article['title']}")
            if article['best_city'] and article['best_state']:
                print(f"   Location: {article['best_city']}, {article['best_state']} (confidence: {article['confidence']})")
            print(f"   Has embedding: {article['has_embedding']}")
    
    def test_database_completeness(self):
        """Test that the database contains all expected node types for complete data processing."""
        print("\n=== TESTING DATABASE COMPLETENESS ===")
        
        counts = self.get_node_counts()
        
        # Core entities should be present
        core_entities = {
            'Property': 'Real estate listings',
            'Neighborhood': 'Geographic neighborhoods', 
            'WikipediaArticle': 'Location-based Wikipedia articles'
        }
        
        extracted_entities = {
            'Feature': 'Property features (extracted from properties)',
            'PropertyType': 'Property type classifications',
            'PriceRange': 'Price range categories',
            'County': 'County geographic entities',
            'TopicCluster': 'Topic clusters from Wikipedia'
        }
        
        print("Core entities (from source data):")
        for entity, description in core_entities.items():
            count = counts[entity]
            status = "✅" if count > 0 else "❌"
            print(f"  {status} {entity}: {count:,} ({description})")
        
        print("\nExtracted entities (derived during processing):")
        for entity, description in extracted_entities.items():
            count = counts[entity]
            status = "✅" if count > 0 else "⚠️"
            print(f"  {status} {entity}: {count:,} ({description})")
        
        # Test that we have core data
        for entity in core_entities:
            assert counts[entity] > 0, f"Missing {entity} nodes - core data processing failed"
        
        print("\n✅ Database completeness verified")
        print("   Relationships will be created separately with: python -m graph-real-estate build-relationships")
    
    def print_database_summary(self):
        """Print a comprehensive summary of the database state."""
        print("\n" + "="*60)
        print("🔍 NEO4J DATABASE VERIFICATION SUMMARY")
        print("="*60)
        
        # Node counts
        counts = self.get_node_counts()
        total_nodes = sum(counts.values())
        print(f"📊 Total nodes: {total_nodes:,}")
        
        for node_type, count in counts.items():
            if count > 0:
                print(f"   • {node_type}: {count:,}")
        
        # Embedding stats
        stats = self.get_embedding_stats()
        total_embeddings = sum(data['count'] for data in stats.values())
        print(f"\n🔮 Total embeddings: {total_embeddings:,}")
        
        for entity_type, data in stats.items():
            if data['count'] > 0:
                print(f"   • {entity_type}: {data['count']:,} ({data['avg_dimensions']} dimensions)")
        
        # Pipeline status
        print(f"\n🏗️ Pipeline Status: Nodes created successfully")
        print("   ✅ Ready for relationship creation")
        print("   Next: python -m graph-real-estate build-relationships")
        
        print("="*60)


def test_neo4j_verification_suite():
    """Run the complete Neo4j verification test suite."""
    verifier = TestNeo4jVerification()
    verifier.setup_class()
    
    try:
        print("\n🧪 Running Neo4j Database Verification Tests...")
        
        # Run all tests
        verifier.test_database_has_nodes()
        verifier.test_embeddings_present() 
        verifier.test_data_quality()
        verifier.test_database_completeness()
        
        # Print summary
        verifier.print_database_summary()
        
        print("\n✅ All Neo4j verification tests passed!")
        
    finally:
        verifier.teardown_class()


if __name__ == "__main__":
    test_neo4j_verification_suite()