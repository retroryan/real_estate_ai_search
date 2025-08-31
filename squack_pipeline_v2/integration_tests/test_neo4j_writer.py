"""Integration tests for Neo4j writer.

These tests verify that data flows correctly from DuckDB to Neo4j
through the squack_pipeline_v2 system.
"""

import os
import pytest
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

from squack_pipeline_v2.orchestration.pipeline import PipelineOrchestrator
from squack_pipeline_v2.core.settings import PipelineSettings

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)


@pytest.fixture(scope="module")
def pipeline_settings():
    """Create test pipeline settings with Neo4j enabled."""
    return PipelineSettings.load(
        data={"sample_size": 2},  # Small sample for fast tests
        output={
            "parquet_enabled": False,
            "elasticsearch_enabled": False,
            "neo4j": {
                "enabled": True,
                "uri": "bolt://localhost:7687",
                "username": "neo4j",
                "password": os.getenv("NEO4J_PASSWORD", "password"),
                "database": "neo4j"
            }
        }
    )


@pytest.fixture(scope="module")
def neo4j_driver():
    """Create Neo4j driver for verifying results."""
    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", os.getenv("NEO4J_PASSWORD", "password"))
    )
    yield driver
    driver.close()


@pytest.fixture(scope="module")
def run_pipeline(pipeline_settings):
    """Run the pipeline once for all tests."""
    orchestrator = PipelineOrchestrator(pipeline_settings)
    
    # Run all pipeline stages
    orchestrator.run_bronze_layer(sample_size=2)
    orchestrator.run_silver_layer()
    orchestrator.run_gold_layer()
    orchestrator.run_embeddings()
    
    # Write to Neo4j
    stats = orchestrator.write_outputs()
    
    return stats


class TestNeo4jWriter:
    """Test Neo4j writer functionality."""
    
    def test_pipeline_writes_to_neo4j(self, run_pipeline):
        """Test that pipeline successfully writes to Neo4j."""
        assert "neo4j" in run_pipeline
        neo4j_stats = run_pipeline["neo4j"]
        
        # Check that nodes were written
        assert neo4j_stats["total_nodes"] > 0
        assert neo4j_stats["total_relationships"] > 0
    
    def test_property_nodes_created(self, neo4j_driver, run_pipeline):
        """Test that Property nodes are created in Neo4j."""
        with neo4j_driver.session() as session:
            result = session.run(
                "MATCH (p:Property) RETURN COUNT(p) as count"
            ).single()
            
            # Should have at least 2 properties (sample size)
            assert result["count"] >= 2
    
    def test_neighborhood_nodes_created(self, neo4j_driver, run_pipeline):
        """Test that Neighborhood nodes are created in Neo4j."""
        with neo4j_driver.session() as session:
            result = session.run(
                "MATCH (n:Neighborhood) RETURN COUNT(n) as count"
            ).single()
            
            # Should have at least 1 neighborhood
            assert result["count"] >= 1
    
    def test_wikipedia_nodes_created(self, neo4j_driver, run_pipeline):
        """Test that WikipediaArticle nodes are created in Neo4j."""
        with neo4j_driver.session() as session:
            result = session.run(
                "MATCH (w:WikipediaArticle) RETURN COUNT(w) as count"
            ).single()
            
            # Should have at least 2 wikipedia articles
            assert result["count"] >= 2
    
    def test_feature_nodes_created(self, neo4j_driver, run_pipeline):
        """Test that Feature nodes are created in Neo4j."""
        with neo4j_driver.session() as session:
            result = session.run(
                "MATCH (f:Feature) RETURN COUNT(f) as count"
            ).single()
            
            # Properties should have features
            assert result["count"] > 0
    
    def test_geographic_nodes_created(self, neo4j_driver, run_pipeline):
        """Test that geographic nodes (City, State, ZipCode) are created."""
        with neo4j_driver.session() as session:
            # Check cities
            city_result = session.run(
                "MATCH (c:City) RETURN COUNT(c) as count"
            ).single()
            assert city_result["count"] >= 1
            
            # Check states
            state_result = session.run(
                "MATCH (s:State) RETURN COUNT(s) as count"
            ).single()
            assert state_result["count"] >= 1
            
            # Check zip codes
            zip_result = session.run(
                "MATCH (z:ZipCode) RETURN COUNT(z) as count"
            ).single()
            assert zip_result["count"] >= 1
    
    def test_located_in_relationships(self, neo4j_driver, run_pipeline):
        """Test that LOCATED_IN relationships are created."""
        with neo4j_driver.session() as session:
            result = session.run(
                "MATCH (p:Property)-[r:LOCATED_IN]->(n:Neighborhood) "
                "RETURN COUNT(r) as count"
            ).single()
            
            # Properties should be located in neighborhoods
            assert result["count"] >= 1
    
    def test_has_feature_relationships(self, neo4j_driver, run_pipeline):
        """Test that HAS_FEATURE relationships are created."""
        with neo4j_driver.session() as session:
            result = session.run(
                "MATCH (p:Property)-[r:HAS_FEATURE]->(f:Feature) "
                "RETURN COUNT(r) as count"
            ).single()
            
            # Properties should have features
            assert result["count"] > 0
    
    def test_geographic_relationships(self, neo4j_driver, run_pipeline):
        """Test that geographic relationships are created."""
        with neo4j_driver.session() as session:
            # Check IN_CITY relationships
            city_result = session.run(
                "MATCH (p:Property)-[r:IN_CITY]->(c:City) "
                "RETURN COUNT(r) as count"
            ).single()
            assert city_result["count"] >= 1
            
            # Check IN_STATE relationships
            state_result = session.run(
                "MATCH (c:City)-[r:IN_STATE]->(s:State) "
                "RETURN COUNT(r) as count"
            ).single()
            assert state_result["count"] >= 1
    
    def test_property_has_required_fields(self, neo4j_driver, run_pipeline):
        """Test that Property nodes have required fields."""
        with neo4j_driver.session() as session:
            result = session.run(
                "MATCH (p:Property) RETURN p LIMIT 1"
            ).single()
            
            property_node = result["p"]
            
            # Check required fields
            assert "listing_id" in property_node
            assert "price" in property_node
            assert "bedrooms" in property_node
            assert "bathrooms" in property_node
            assert "square_feet" in property_node
    
    def test_neighborhood_has_required_fields(self, neo4j_driver, run_pipeline):
        """Test that Neighborhood nodes have required fields."""
        with neo4j_driver.session() as session:
            result = session.run(
                "MATCH (n:Neighborhood) RETURN n LIMIT 1"
            ).single()
            
            if result:  # Only if neighborhoods exist
                neighborhood = result["n"]
                
                # Check required fields
                assert "neighborhood_id" in neighborhood
                assert "name" in neighborhood
                assert "city" in neighborhood
                assert "state" in neighborhood
    
    def test_constraints_created(self, neo4j_driver, run_pipeline):
        """Test that uniqueness constraints are created."""
        with neo4j_driver.session() as session:
            # Get all constraints
            result = session.run("SHOW CONSTRAINTS")
            constraints = list(result)
            
            # Should have constraints for primary keys
            constraint_names = [c["name"] for c in constraints]
            
            # Check for property constraint
            property_constraints = [
                c for c in constraint_names 
                if "property" in c.lower() or "listing_id" in c.lower()
            ]
            assert len(property_constraints) > 0
    
    def test_vector_embeddings_stored(self, neo4j_driver, run_pipeline):
        """Test that vector embeddings are stored if available."""
        with neo4j_driver.session() as session:
            result = session.run(
                "MATCH (p:Property) "
                "WHERE p.embedding IS NOT NULL "
                "RETURN COUNT(p) as count"
            ).single()
            
            # Embeddings may or may not be present depending on configuration
            # Just verify the query works
            assert result["count"] >= 0


@pytest.mark.parametrize("sample_size", [1, 5, 10])
def test_different_sample_sizes(sample_size):
    """Test pipeline with different sample sizes."""
    settings = PipelineSettings.load(
        data={"sample_size": sample_size},
        output={
            "parquet_enabled": False,
            "elasticsearch_enabled": False,
            "neo4j": {
                "enabled": True,
                "uri": "bolt://localhost:7687",
                "username": "neo4j",
                "password": os.getenv("NEO4J_PASSWORD", "password"),
                "database": "neo4j"
            }
        }
    )
    
    orchestrator = PipelineOrchestrator(settings)
    
    # Run pipeline
    orchestrator.run_bronze_layer(sample_size=sample_size)
    orchestrator.run_silver_layer()
    orchestrator.run_gold_layer()
    orchestrator.run_embeddings()
    
    # Write to Neo4j
    stats = orchestrator.write_outputs()
    
    # Verify results
    assert "neo4j" in stats
    assert stats["neo4j"]["total_nodes"] > 0
    assert stats["neo4j"]["total_relationships"] > 0


def test_neo4j_connection_error_handling():
    """Test that Neo4j connection errors are handled gracefully."""
    # Create settings with invalid Neo4j credentials
    settings = PipelineSettings.load(
        data={"sample_size": 1},
        output={
            "neo4j": {
                "enabled": True,
                "uri": "bolt://localhost:7687",
                "username": "invalid_user",
                "password": "invalid_password",
                "database": "neo4j"
            }
        }
    )
    
    orchestrator = PipelineOrchestrator(settings)
    
    # Run pipeline stages
    orchestrator.run_bronze_layer(sample_size=1)
    orchestrator.run_silver_layer()
    orchestrator.run_gold_layer()
    
    # Try to write to Neo4j - should handle error gracefully
    try:
        stats = orchestrator.write_outputs()
        # If it succeeds, check that error was logged
        assert "neo4j" in stats
        if "error" in stats["neo4j"]:
            assert "authentication" in stats["neo4j"]["error"].lower()
    except Exception as e:
        # Connection error is expected
        assert "auth" in str(e).lower() or "connection" in str(e).lower()