"""Integration tests for Gold Layer with all entity types.

Tests the transformation of Properties, Neighborhoods, and Wikipedia articles
from Silver to Gold tier, ensuring nested structures are preserved and
minimal transformations are applied correctly for Elasticsearch.
"""

from pathlib import Path
import pytest

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.loaders.property_loader import PropertyLoader
from squack_pipeline.loaders.neighborhood_loader import NeighborhoodLoader
from squack_pipeline.loaders.wikipedia_loader import WikipediaLoader
from squack_pipeline.processors.property_silver_processor import PropertySilverProcessor
from squack_pipeline.processors.neighborhood_silver_processor import NeighborhoodSilverProcessor
from squack_pipeline.processors.wikipedia_silver_processor import WikipediaSilverProcessor
from squack_pipeline.processors.property_gold_processor import PropertyGoldProcessor
from squack_pipeline.processors.neighborhood_gold_processor import NeighborhoodGoldProcessor
from squack_pipeline.processors.wikipedia_gold_processor import WikipediaGoldProcessor


class TestPropertyGoldLayer:
    """Integration tests for Property Gold layer transformations."""
    
    @pytest.fixture
    def settings(self):
        """Load pipeline settings."""
        return PipelineSettings.load_from_yaml(Path("squack_pipeline/config.yaml"))
    
    @pytest.fixture
    def property_loader(self, settings):
        """Create property loader."""
        return PropertyLoader(settings)
    
    @pytest.fixture
    def property_silver_processor(self, settings):
        """Create Property Silver processor."""
        return PropertySilverProcessor(settings)
    
    @pytest.fixture
    def property_gold_processor(self, settings):
        """Create Property Gold processor."""
        return PropertyGoldProcessor(settings)
    
    def test_property_gold_transformation(self, property_loader, property_silver_processor, 
                                         property_gold_processor, settings):
        """Test Property Silver → Gold transformation with minimal changes."""
        print("\n=== Testing Property Gold Transformation ===")
        
        # Initialize connections
        property_loader.connection_manager.initialize(settings)
        connection = property_loader.connection_manager.get_connection()
        property_loader.set_connection(connection)
        property_silver_processor.set_connection(connection)
        property_gold_processor.set_connection(connection)
        
        try:
            # Load and process through Bronze → Silver
            print("Loading properties through Bronze and Silver layers...")
            bronze_table = property_loader.load(sample_size=10)
            silver_table = property_silver_processor.process(bronze_table)
            silver_count = property_silver_processor.count_records(silver_table)
            print(f"✓ {silver_count} properties in Silver layer")
            
            # Validate Silver input for Gold
            assert property_gold_processor.validate_input(silver_table), "Silver validation failed"
            print("✓ Silver property data validated for Gold processing")
            
            # Process through Gold layer
            print("Processing through Gold layer...")
            gold_table = property_gold_processor.process(silver_table)
            gold_count = property_gold_processor.count_records(gold_table)
            assert gold_count == silver_count, "Record count mismatch"
            print(f"✓ Processed {gold_count} properties into Gold layer")
            
            # Verify schema structure
            schema = property_gold_processor.get_table_schema(gold_table)
            
            # Check nested structures still preserved
            nested_fields = ['address', 'property_details', 'coordinates']
            for field in nested_fields:
                assert field in schema, f"Nested field {field} missing"
                assert 'STRUCT' in schema[field].upper(), f"{field} is not a STRUCT"
            print("✓ Nested structures preserved in Gold (address, property_details, coordinates)")
            
            # Check minimal transformations
            assert 'price' in schema, "Price field missing (renamed from listing_price)"
            assert 'location' in schema, "Location array missing"
            assert 'parking' in schema, "Parking object missing"
            assert 'entity_type' in schema, "Entity type missing"
            print("✓ Minimal transformations applied (price rename, location array, parking object)")
            
            # Verify computed fields with query
            compute_query = f"""
            SELECT 
                listing_id,
                price,
                location,
                parking.spaces as parking_spaces,
                parking.available as parking_available,
                entity_type
            FROM {gold_table}
            LIMIT 1
            """
            
            result = connection.execute(compute_query).fetchone()
            if result:
                lid, price, location, spaces, available, etype = result
                assert price is not None, "Price not populated"
                assert etype == 'property', "Entity type incorrect"
                print(f"✓ Sample: {lid}, price={price}, location={location}, parking={spaces}/{available}")
            
            # Validate Gold output
            assert property_gold_processor.validate_output(gold_table), "Gold validation failed"
            print("✓ Gold property data validated")
            
            # Get and verify metrics
            metrics = property_gold_processor.get_metrics()
            assert metrics['records_processed'] == gold_count, "Metrics mismatch"
            assert metrics['records_transformed'] == gold_count, "Transform count mismatch"
            print(f"✓ Metrics: {metrics['records_processed']} processed, {metrics['records_transformed']} transformed")
            
            print("✓ Property Gold transformation test passed")
            
        except Exception as e:
            pytest.fail(f"Property Gold test failed: {e}")


class TestNeighborhoodGoldLayer:
    """Integration tests for Neighborhood Gold layer transformations."""
    
    @pytest.fixture
    def settings(self):
        """Load pipeline settings."""
        return PipelineSettings.load_from_yaml(Path("squack_pipeline/config.yaml"))
    
    @pytest.fixture
    def neighborhood_loader(self, settings):
        """Create neighborhood loader."""
        return NeighborhoodLoader(settings)
    
    @pytest.fixture
    def neighborhood_silver_processor(self, settings):
        """Create Neighborhood Silver processor."""
        return NeighborhoodSilverProcessor(settings)
    
    @pytest.fixture
    def neighborhood_gold_processor(self, settings):
        """Create Neighborhood Gold processor."""
        return NeighborhoodGoldProcessor(settings)
    
    def test_neighborhood_gold_transformation(self, neighborhood_loader, neighborhood_silver_processor,
                                             neighborhood_gold_processor, settings):
        """Test Neighborhood Silver → Gold transformation with minimal changes."""
        print("\n=== Testing Neighborhood Gold Transformation ===")
        
        # Initialize connections
        neighborhood_loader.connection_manager.initialize(settings)
        connection = neighborhood_loader.connection_manager.get_connection()
        neighborhood_loader.set_connection(connection)
        neighborhood_silver_processor.set_connection(connection)
        neighborhood_gold_processor.set_connection(connection)
        
        try:
            # Load and process through Bronze → Silver
            print("Loading neighborhoods through Bronze and Silver layers...")
            bronze_table = neighborhood_loader.load(sample_size=5)
            silver_table = neighborhood_silver_processor.process(bronze_table)
            silver_count = neighborhood_silver_processor.count_records(silver_table)
            print(f"✓ {silver_count} neighborhoods in Silver layer")
            
            # Validate Silver input for Gold
            assert neighborhood_gold_processor.validate_input(silver_table), "Silver validation failed"
            print("✓ Silver neighborhood data validated for Gold processing")
            
            # Process through Gold layer
            print("Processing through Gold layer...")
            gold_table = neighborhood_gold_processor.process(silver_table)
            gold_count = neighborhood_gold_processor.count_records(gold_table)
            assert gold_count == silver_count, "Record count mismatch"
            print(f"✓ Processed {gold_count} neighborhoods into Gold layer")
            
            # Verify schema structure
            schema = neighborhood_gold_processor.get_table_schema(gold_table)
            
            # Check nested structures still preserved
            nested_fields = ['coordinates', 'characteristics', 'demographics']
            for field in nested_fields:
                assert field in schema, f"Nested field {field} missing"
                assert 'STRUCT' in schema[field].upper(), f"{field} is not a STRUCT"
            print("✓ Nested structures preserved (coordinates, characteristics, demographics)")
            
            # Check minimal transformations
            assert 'location' in schema, "Location array missing"
            assert 'entity_type' in schema, "Entity type missing"
            print("✓ Minimal transformations applied (location array, entity_type)")
            
            # Check arrays preserved
            array_fields = ['amenities', 'lifestyle_tags']
            for field in array_fields:
                assert field in schema, f"Array field {field} missing"
            print("✓ Array fields preserved (amenities, lifestyle_tags)")
            
            # Verify computed fields with query
            compute_query = f"""
            SELECT 
                neighborhood_id,
                name,
                location,
                coordinates.latitude as lat,
                coordinates.longitude as lon,
                entity_type
            FROM {gold_table}
            LIMIT 1
            """
            
            result = connection.execute(compute_query).fetchone()
            if result:
                nid, name, location, lat, lon, etype = result
                assert etype == 'neighborhood', "Entity type incorrect"
                if lat and lon:
                    assert location == [lon, lat], "Location array incorrect"
                print(f"✓ Sample: {nid} ({name}), location={location}, entity={etype}")
            
            # Validate Gold output
            assert neighborhood_gold_processor.validate_output(gold_table), "Gold validation failed"
            print("✓ Gold neighborhood data validated")
            
            # Get and verify metrics
            metrics = neighborhood_gold_processor.get_metrics()
            assert metrics['records_processed'] == gold_count, "Metrics mismatch"
            print(f"✓ Metrics: {metrics['records_processed']} processed")
            
            print("✓ Neighborhood Gold transformation test passed")
            
        except Exception as e:
            pytest.fail(f"Neighborhood Gold test failed: {e}")


class TestWikipediaGoldLayer:
    """Integration tests for Wikipedia Gold layer transformations."""
    
    @pytest.fixture
    def settings(self):
        """Load pipeline settings."""
        return PipelineSettings.load_from_yaml(Path("squack_pipeline/config.yaml"))
    
    @pytest.fixture
    def wikipedia_loader(self, settings):
        """Create Wikipedia loader."""
        return WikipediaLoader(settings)
    
    @pytest.fixture
    def wikipedia_silver_processor(self, settings):
        """Create Wikipedia Silver processor."""
        return WikipediaSilverProcessor(settings)
    
    @pytest.fixture
    def wikipedia_gold_processor(self, settings):
        """Create Wikipedia Gold processor."""
        return WikipediaGoldProcessor(settings)
    
    def test_wikipedia_gold_transformation(self, wikipedia_loader, wikipedia_silver_processor,
                                          wikipedia_gold_processor, settings):
        """Test Wikipedia Silver → Gold transformation with minimal changes."""
        print("\n=== Testing Wikipedia Gold Transformation ===")
        
        # Initialize connections
        wikipedia_loader.connection_manager.initialize(settings)
        connection = wikipedia_loader.connection_manager.get_connection()
        wikipedia_loader.set_connection(connection)
        wikipedia_silver_processor.set_connection(connection)
        wikipedia_gold_processor.set_connection(connection)
        
        try:
            # Load and process through Bronze → Silver
            print("Loading Wikipedia articles through Bronze and Silver layers...")
            bronze_table = wikipedia_loader.load(sample_size=20)
            silver_table = wikipedia_silver_processor.process(bronze_table)
            silver_count = wikipedia_silver_processor.count_records(silver_table)
            print(f"✓ {silver_count} Wikipedia articles in Silver layer")
            
            # Validate Silver input for Gold
            assert wikipedia_gold_processor.validate_input(silver_table), "Silver validation failed"
            print("✓ Silver Wikipedia data validated for Gold processing")
            
            # Process through Gold layer
            print("Processing through Gold layer...")
            gold_table = wikipedia_gold_processor.process(silver_table)
            gold_count = wikipedia_gold_processor.count_records(gold_table)
            assert gold_count == silver_count, "Record count mismatch"
            print(f"✓ Processed {gold_count} Wikipedia articles into Gold layer")
            
            # Verify schema structure
            schema = wikipedia_gold_processor.get_table_schema(gold_table)
            
            # Check field renaming
            assert 'page_id' in schema, "page_id missing (renamed from pageid)"
            assert 'entity_type' in schema, "Entity type missing"
            print("✓ Field renamed (pageid → page_id)")
            
            # Check minimal transformations
            assert 'location' in schema, "Location array missing"
            print("✓ Minimal transformations applied (location array, entity_type)")
            
            # Verify computed fields with query
            compute_query = f"""
            SELECT 
                id,
                page_id,
                title,
                location,
                latitude,
                longitude,
                entity_type
            FROM {gold_table}
            LIMIT 1
            """
            
            result = connection.execute(compute_query).fetchone()
            if result:
                wid, page_id, title, location, lat, lon, etype = result
                assert etype == 'wikipedia', "Entity type incorrect"
                if lat and lon:
                    assert location == [lon, lat], "Location array incorrect"
                print(f"✓ Sample: {wid} ({title[:30]}...), location={location}, entity={etype}")
            
            # Check location array creation
            location_query = f"""
            SELECT 
                COUNT(*) as total,
                COUNT(location) as has_location,
                COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 END) as has_coords
            FROM {gold_table}
            """
            
            result = connection.execute(location_query).fetchone()
            if result:
                total, has_loc, has_coords = result
                print(f"✓ Location arrays: {has_loc}/{total} created, {has_coords}/{total} with coordinates")
                if has_coords > 0:
                    assert has_loc == has_coords, "Location array count mismatch"
            
            # Validate Gold output
            assert wikipedia_gold_processor.validate_output(gold_table), "Gold validation failed"
            print("✓ Gold Wikipedia data validated")
            
            # Get and verify metrics
            metrics = wikipedia_gold_processor.get_metrics()
            assert metrics['records_processed'] == gold_count, "Metrics mismatch"
            print(f"✓ Metrics: {metrics['records_processed']} processed")
            
            print("✓ Wikipedia Gold transformation test passed")
            
        except Exception as e:
            pytest.fail(f"Wikipedia Gold test failed: {e}")


class TestGoldLayerIntegration:
    """Integration tests for Gold layer cross-entity operations."""
    
    @pytest.fixture
    def settings(self):
        """Load pipeline settings."""
        return PipelineSettings.load_from_yaml(Path("squack_pipeline/config.yaml"))
    
    def test_all_entities_gold_processing(self, settings):
        """Test that all three entity types can be processed through Gold layer."""
        print("\n=== Testing All Entities Gold Processing ===")
        
        # Initialize loaders
        property_loader = PropertyLoader(settings)
        neighborhood_loader = NeighborhoodLoader(settings)
        wikipedia_loader = WikipediaLoader(settings)
        
        # Initialize Silver processors
        property_silver = PropertySilverProcessor(settings)
        neighborhood_silver = NeighborhoodSilverProcessor(settings)
        wikipedia_silver = WikipediaSilverProcessor(settings)
        
        # Initialize Gold processors
        property_gold = PropertyGoldProcessor(settings)
        neighborhood_gold = NeighborhoodGoldProcessor(settings)
        wikipedia_gold = WikipediaGoldProcessor(settings)
        
        # Initialize connection
        property_loader.connection_manager.initialize(settings)
        connection = property_loader.connection_manager.get_connection()
        
        # Set connections for all
        for component in [property_loader, neighborhood_loader, wikipedia_loader,
                         property_silver, neighborhood_silver, wikipedia_silver,
                         property_gold, neighborhood_gold, wikipedia_gold]:
            component.set_connection(connection)
        
        try:
            # Load all entities through Bronze → Silver → Gold
            print("Processing all entities through Bronze → Silver → Gold...")
            
            # Properties
            print("Processing properties...")
            prop_bronze = property_loader.load(sample_size=5)
            prop_silver = property_silver.process(prop_bronze)
            prop_gold = property_gold.process(prop_silver)
            
            # Add small delay to ensure different timestamps
            import time
            time.sleep(0.01)
            
            # Neighborhoods  
            print("Processing neighborhoods...")
            hood_bronze = neighborhood_loader.load(sample_size=3)
            hood_silver = neighborhood_silver.process(hood_bronze)
            hood_gold = neighborhood_gold.process(hood_silver)
            
            # Add small delay to ensure different timestamps
            time.sleep(0.01)
            
            # Wikipedia
            print("Processing Wikipedia...")
            wiki_bronze = wikipedia_loader.load(sample_size=10)
            wiki_silver = wikipedia_silver.process(wiki_bronze)
            wiki_gold = wikipedia_gold.process(wiki_silver)
            
            # Verify all Gold tables exist
            for table in [prop_gold, hood_gold, wiki_gold]:
                result = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                assert result and result[0] > 0, f"No data in {table}"
            
            print(f"✓ Property Gold: {property_gold.count_records(prop_gold)} records")
            print(f"✓ Neighborhood Gold: {neighborhood_gold.count_records(hood_gold)} records")
            print(f"✓ Wikipedia Gold: {wikipedia_gold.count_records(wiki_gold)} records")
            
            # Verify all have Gold metadata
            for table in [prop_gold, hood_gold, wiki_gold]:
                schema_result = connection.execute(f"DESCRIBE {table}").fetchall()
                schema = {row[0]: row[1] for row in schema_result}
                assert 'gold_processed_at' in schema, f"Missing Gold metadata in {table}"
                assert 'entity_type' in schema, f"Missing entity_type in {table}"
            
            print("✓ All entities have Gold tier metadata")
            
            # Verify entity types are set correctly
            entity_query = """
            SELECT entity_type, COUNT(*) as count
            FROM (
                SELECT entity_type FROM {prop_table}
                UNION ALL
                SELECT entity_type FROM {hood_table}
                UNION ALL
                SELECT entity_type FROM {wiki_table}
            ) combined
            GROUP BY entity_type
            ORDER BY entity_type
            """
            
            formatted_query = entity_query.format(
                prop_table=prop_gold,
                hood_table=hood_gold,
                wiki_table=wiki_gold
            )
            
            entity_counts = connection.execute(formatted_query).fetchall()
            entity_types = {row[0]: row[1] for row in entity_counts}
            
            assert 'property' in entity_types, "Property entity type missing"
            assert 'neighborhood' in entity_types, "Neighborhood entity type missing"
            assert 'wikipedia' in entity_types, "Wikipedia entity type missing"
            
            print(f"✓ Entity types: property({entity_types.get('property', 0)}), "
                  f"neighborhood({entity_types.get('neighborhood', 0)}), "
                  f"wikipedia({entity_types.get('wikipedia', 0)})")
            
            # Verify location arrays are created
            location_check = """
            SELECT 
                'property' as entity,
                COUNT(*) as total,
                COUNT(location) as has_location
            FROM {prop_table}
            UNION ALL
            SELECT 
                'neighborhood' as entity,
                COUNT(*) as total,
                COUNT(location) as has_location
            FROM {hood_table}
            UNION ALL
            SELECT 
                'wikipedia' as entity,
                COUNT(*) as total,
                COUNT(location) as has_location
            FROM {wiki_table}
            """
            
            formatted_location = location_check.format(
                prop_table=prop_gold,
                hood_table=hood_gold,
                wiki_table=wiki_gold
            )
            
            location_stats = connection.execute(formatted_location).fetchall()
            for entity, total, has_loc in location_stats:
                print(f"✓ {entity}: {has_loc}/{total} records with location array")
            
            # Verify nested structures are preserved in Gold
            prop_nested = connection.execute(
                f"SELECT address, property_details, coordinates FROM {prop_gold} LIMIT 1"
            ).fetchone()
            if prop_nested:
                assert prop_nested[0] is not None, "Property address lost"
                assert prop_nested[1] is not None, "Property details lost"
                print("✓ Property nested structures preserved in Gold")
            
            hood_nested = connection.execute(
                f"SELECT coordinates, characteristics, demographics FROM {hood_gold} LIMIT 1"
            ).fetchone()
            if hood_nested:
                assert hood_nested[0] is not None, "Neighborhood coordinates lost"
                assert hood_nested[1] is not None, "Neighborhood characteristics lost"
                print("✓ Neighborhood nested structures preserved in Gold")
            
            print("✓ All entities successfully processed through Gold layer")
            print("✓ Nested structures preserved throughout pipeline")
            print("✓ Minimal transformations applied for Elasticsearch")
            
        except Exception as e:
            pytest.fail(f"Multi-entity Gold processing failed: {e}")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "--tb=short"])