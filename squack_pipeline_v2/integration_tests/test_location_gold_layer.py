"""Integration tests for Location Gold Layer enrichment.

Tests gold layer location data enrichment and graph building.
"""

import pytest

from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.core.table_names import ENTITY_TYPES
from squack_pipeline_v2.bronze.location import LocationBronzeIngester
from squack_pipeline_v2.silver.location import LocationSilverTransformer
from squack_pipeline_v2.gold.location import LocationGoldEnricher
from squack_pipeline_v2.gold.graph_builder import GoldGraphBuilder


class TestLocationGoldLayer:
    """Test Location Gold Layer enrichment."""
    
    @pytest.fixture
    def settings(self):
        """Create test settings."""
        settings = PipelineSettings()
        settings.duckdb.database_file = ":memory:"
        settings.data_sources.locations_file = "real_estate_data/locations.json"
        return settings
    
    @pytest.fixture
    def connection_manager(self, settings):
        """Create connection manager."""
        return DuckDBConnectionManager(settings.duckdb)
    
    @pytest.fixture
    def setup_data(self, settings, connection_manager):
        """Setup bronze and silver data for testing."""
        # Load bronze data
        bronze_ingester = LocationBronzeIngester(settings, connection_manager)
        bronze_ingester.ingest(
            table_name=ENTITY_TYPES.location.bronze_table,
            sample_size=50
        )
        
        # Transform to silver
        silver_transformer = LocationSilverTransformer(settings, connection_manager)
        silver_transformer.transform(
            input_table=ENTITY_TYPES.location.bronze_table,
            output_table=ENTITY_TYPES.location.silver_table
        )
        
        return True
    
    def test_gold_enrichment_creates_view(self, settings, connection_manager, setup_data):
        """Test that gold enrichment creates a view not a table."""
        # Create gold enrichment
        gold_enricher = LocationGoldEnricher(settings, connection_manager)
        metadata = gold_enricher.enrich(
            input_table=ENTITY_TYPES.location.silver_table,
            output_table=ENTITY_TYPES.location.gold_table
        )
        
        # Check metadata
        assert metadata.entity_type == "location"
        assert metadata.input_count == 50
        assert metadata.output_count == 50
        assert "hierarchical_ids" in metadata.enrichments_applied
        assert "graph_node_ids" in metadata.enrichments_applied
        
        # Check view exists
        conn = connection_manager.get_connection()
        result = conn.execute(
            "SELECT COUNT(*) FROM information_schema.views WHERE table_schema = ? AND table_name = ?",
            ["main", ENTITY_TYPES.location.gold_table]
        ).fetchone()
        assert result[0] == 1, "Gold table should be a view"
    
    def test_gold_location_fields(self, settings, connection_manager, setup_data):
        """Test that gold locations have all required fields."""
        # Create gold enrichment
        gold_enricher = LocationGoldEnricher(settings, connection_manager)
        gold_enricher.enrich(
            input_table=ENTITY_TYPES.location.silver_table,
            output_table=ENTITY_TYPES.location.gold_table
        )
        
        # Check fields
        conn = connection_manager.get_connection()
        sample = conn.sql(f"""
            SELECT * FROM {ENTITY_TYPES.location.gold_table}
            LIMIT 1
        """).df()
        
        required_fields = [
            'neighborhood', 'city', 'county', 'state', 'zip_code',
            'neighborhood_id', 'city_id', 'county_id', 'state_id',
            'location_type', 'graph_node_id', 'parent_location_id'
        ]
        
        for field in required_fields:
            assert field in sample.columns, f"Missing field: {field}"
    
    def test_graph_builder_uses_locations(self, settings, connection_manager, setup_data):
        """Test that graph builder uses location data when available."""
        # Create gold enrichment
        gold_enricher = LocationGoldEnricher(settings, connection_manager)
        gold_enricher.enrich(
            input_table=ENTITY_TYPES.location.silver_table,
            output_table=ENTITY_TYPES.location.gold_table
        )
        
        # Build graph nodes
        graph_builder = GoldGraphBuilder(connection_manager)
        
        # Build city nodes
        city_table = graph_builder.build_city_nodes()
        assert city_table == "gold_graph_cities"
        
        conn = connection_manager.get_connection()
        cities = conn.sql(f"SELECT * FROM {city_table}").df()
        assert len(cities) > 0
        assert 'city_id' in cities.columns
        assert 'county' in cities.columns  # Should have county from location data
        
        # Build state nodes
        state_table = graph_builder.build_state_nodes()
        assert state_table == "gold_graph_states"
        
        states = conn.sql(f"SELECT * FROM {state_table}").df()
        assert len(states) > 0
        
        # Build county nodes
        county_table = graph_builder.build_county_nodes()
        assert county_table == "gold_graph_counties"
        
        counties = conn.sql(f"SELECT * FROM {county_table}").df()
        assert len(counties) > 0
        
        # Build ZIP nodes
        zip_table = graph_builder.build_zip_code_nodes()
        assert zip_table == "gold_graph_zip_codes"
        
        zips = conn.sql(f"SELECT * FROM {zip_table}").df()
        assert len(zips) > 0
        assert 'county' in zips.columns  # Should have county from location data
    
    def test_geographic_hierarchy_relationships(self, settings, connection_manager, setup_data):
        """Test that geographic hierarchy relationships are created."""
        # Create gold enrichment
        gold_enricher = LocationGoldEnricher(settings, connection_manager)
        gold_enricher.enrich(
            input_table=ENTITY_TYPES.location.silver_table,
            output_table=ENTITY_TYPES.location.gold_table
        )
        
        # Build relationships
        graph_builder = GoldGraphBuilder(connection_manager)
        rel_table = graph_builder.build_geographic_hierarchy_relationships()
        
        assert rel_table == "gold_graph_geographic_hierarchy"
        
        conn = connection_manager.get_connection()
        relationships = conn.sql(f"""
            SELECT relationship_type, COUNT(*) as count
            FROM {rel_table}
            GROUP BY relationship_type
        """).df()
        
        # Should have different relationship types
        rel_types = relationships['relationship_type'].tolist()
        assert 'IN_CITY' in rel_types
        assert 'IN_COUNTY' in rel_types
        assert 'IN_STATE' in rel_types
        
        # Each type should have some relationships
        for _, row in relationships.iterrows():
            assert row['count'] > 0, f"No relationships for {row['relationship_type']}"
    
    def test_build_all_includes_location(self, settings, connection_manager, setup_data):
        """Test that build_all_graph_tables includes location data."""
        # Create gold enrichment
        gold_enricher = LocationGoldEnricher(settings, connection_manager)
        gold_enricher.enrich(
            input_table=ENTITY_TYPES.location.silver_table,
            output_table=ENTITY_TYPES.location.gold_table
        )
        
        # Build all graph tables
        graph_builder = GoldGraphBuilder(connection_manager)
        metadata = graph_builder.build_all_graph_tables()
        
        # Check that geographic hierarchy relationships were built
        assert "gold_graph_geographic_hierarchy" in metadata.relationship_tables
        
        # Check node tables include geographic nodes
        assert "gold_graph_cities" in metadata.node_tables
        assert "gold_graph_states" in metadata.node_tables
        assert "gold_graph_counties" in metadata.node_tables
        assert "gold_graph_zip_codes" in metadata.node_tables