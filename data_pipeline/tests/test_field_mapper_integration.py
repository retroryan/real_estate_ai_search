"""Integration tests for field mapper with real Spark DataFrames."""

import pytest
import tempfile
import json
import os
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType

from data_pipeline.transformers.field_mapper import FieldMapper, MappingConfiguration


@pytest.fixture(scope="session")
def spark():
    """Create a Spark session for integration testing."""
    return SparkSession.builder.appName("test_field_mapper_integration").getOrCreate()


@pytest.fixture
def integration_config():
    """Complete field mapping configuration for integration testing."""
    return {
        "property_mappings": {
            "field_mappings": {
                "zip": "zip_code",
                "listing_price": "price",
                "garage_spaces": "parking_spaces"
            },
            "nested_object_mappings": {
                "address": {
                    "street": "address.street",
                    "city": "address.city",
                    "state": "address.state",
                    "zip": "address.zip_code",
                    "county": "address.county",
                    "latitude": "address.location[1]",
                    "longitude": "address.location[0]"
                },
                "neighborhood": {
                    "neighborhood_id": "neighborhood.id",
                    "neighborhood": "neighborhood.name"
                },
                "parking": {
                    "garage_spaces": "parking.spaces",
                    "parking_type": "parking.type"
                }
            },
            "type_conversions": {
                "price": "float",
                "listing_price": "float",
                "bedrooms": "int",
                "bathrooms": "float",
                "square_feet": "int",
                "year_built": "int",
                "latitude": "float",
                "longitude": "float"
            },
            "list_fields": [
                "features",
                "amenities"
            ],
            "required_fields": [
                "listing_id"
            ]
        },
        "neighborhood_mappings": {
            "field_mappings": {
                "zip": "zip_code"
            },
            "nested_object_mappings": {
                "address": {
                    "city": "address.city",
                    "state": "address.state",
                    "latitude": "address.location[1]",
                    "longitude": "address.location[0]"
                }
            },
            "type_conversions": {
                "walkability_score": "int",
                "school_rating": "float",
                "latitude": "float",
                "longitude": "float"
            },
            "list_fields": [
                "amenities"
            ],
            "required_fields": [
                "listing_id",
                "neighborhood_id"
            ]
        },
        "wikipedia_mappings": {
            "field_mappings": {},
            "nested_object_mappings": {
                "address": {
                    "latitude": "address.location[1]",
                    "longitude": "address.location[0]"
                }
            },
            "type_conversions": {
                "page_id": "int",
                "latitude": "float",
                "longitude": "float"
            },
            "list_fields": [
                "topics",
                "key_topics"
            ],
            "required_fields": [
                "listing_id",
                "page_id",
                "title"
            ]
        },
        "wikipedia_enrichment_mappings": {
            "location_context": {
                "location_wikipedia_page_id": "location_context.wikipedia_page_id",
                "location_wikipedia_title": "location_context.wikipedia_title",
                "location_summary": "location_context.location_summary"
            }
        }
    }


@pytest.fixture
def temp_config_file(integration_config):
    """Create temporary config file for integration testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(integration_config, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


class TestFieldMapperIntegration:
    """Integration tests for field mapper with realistic data."""
    
    def test_property_complete_transformation(self, spark, temp_config_file):
        """Test complete property field transformation with realistic data."""
        mapper = FieldMapper(temp_config_file)
        
        # Create realistic property DataFrame
        schema = StructType([
            StructField("listing_id", StringType(), True),
            StructField("zip", StringType(), True),
            StructField("listing_price", StringType(), True),  # String to be converted
            StructField("bedrooms", StringType(), True),       # String to be converted
            StructField("bathrooms", StringType(), True),      # String to be converted
            StructField("square_feet", StringType(), True),    # String to be converted
            StructField("street", StringType(), True),
            StructField("city", StringType(), True),
            StructField("state", StringType(), True),
            StructField("county", StringType(), True),
            StructField("latitude", StringType(), True),       # String to be converted
            StructField("longitude", StringType(), True),      # String to be converted
            StructField("neighborhood_id", StringType(), True),
            StructField("neighborhood", StringType(), True),
            StructField("garage_spaces", StringType(), True),  # String to be converted
            StructField("parking_type", StringType(), True),
            StructField("features", StringType(), True),       # Comma-separated list
            StructField("amenities", StringType(), True)       # Comma-separated list
        ])
        
        data = [(
            "prop_12345",
            "94102",
            "750000.0",
            "3",
            "2.5",
            "1800",
            "123 Main Street",
            "San Francisco",
            "CA",
            "San Francisco County",
            "37.7749",
            "-122.4194",
            "nhood_001",
            "Pacific Heights",
            "2",
            "garage",
            "hardwood floors,updated kitchen,bay windows",
            "pool,gym,concierge"
        )]
        
        df = spark.createDataFrame(data, schema)
        
        # Apply field mapping
        result = mapper.map_property_fields(df)
        
        # Verify transformation was successful
        assert result.dataframe is not None
        assert len(result.mapped_fields) > 0
        assert len(result.missing_required_fields) == 0
        
        # Collect result to verify transformations
        transformed_row = result.dataframe.collect()[0]
        
        # Check direct field mappings
        assert transformed_row.zip_code == "94102"
        assert isinstance(transformed_row.price, float)
        assert transformed_row.price == 750000.0
        
        # Check type conversions
        assert isinstance(transformed_row.bedrooms, int)
        assert transformed_row.bedrooms == 3
        assert isinstance(transformed_row.bathrooms, float)
        assert transformed_row.bathrooms == 2.5
        assert isinstance(transformed_row.square_feet, int)
        assert transformed_row.square_feet == 1800
        
        # Check nested address object
        assert hasattr(transformed_row, 'address')
        address = transformed_row.address
        assert address.street == "123 Main Street"
        assert address.city == "San Francisco"
        assert address.state == "CA"
        assert address.zip_code == "94102"
        assert address.county == "San Francisco County"
        assert address.location is not None
        assert len(address.location) == 2
        assert address.location[0] == -122.4194  # longitude first
        assert address.location[1] == 37.7749    # latitude second
        
        # Check nested neighborhood object
        assert hasattr(transformed_row, 'neighborhood')
        neighborhood = transformed_row.neighborhood
        assert neighborhood.id == "nhood_001"
        assert neighborhood.name == "Pacific Heights"
        
        # Check nested parking object
        assert hasattr(transformed_row, 'parking')
        parking = transformed_row.parking
        assert parking.spaces == 2  # Should be converted to int
        assert parking.type == "garage"
        
        # Check list field handling
        assert hasattr(transformed_row, 'features')
        features = transformed_row.features
        assert isinstance(features, list)
        assert "hardwood floors" in features
        assert "updated kitchen" in features
        assert "bay windows" in features
        
        assert hasattr(transformed_row, 'amenities')
        amenities = transformed_row.amenities
        assert isinstance(amenities, list)
        assert "pool" in amenities
        assert "gym" in amenities
        assert "concierge" in amenities
    
    def test_neighborhood_transformation(self, spark, temp_config_file):
        """Test neighborhood field transformation."""
        mapper = FieldMapper(temp_config_file)
        
        schema = StructType([
            StructField("listing_id", StringType(), True),
            StructField("neighborhood_id", StringType(), True),
            StructField("zip", StringType(), True),
            StructField("city", StringType(), True),
            StructField("state", StringType(), True),
            StructField("latitude", StringType(), True),
            StructField("longitude", StringType(), True),
            StructField("walkability_score", StringType(), True),
            StructField("school_rating", StringType(), True),
            StructField("amenities", StringType(), True)
        ])
        
        data = [(
            "listing_1",
            "nhood_001",
            "94102",
            "San Francisco",
            "CA",
            "37.7749",
            "-122.4194",
            "85",
            "8.5",
            "restaurants,shopping,transit"
        )]
        
        df = spark.createDataFrame(data, schema)
        
        # Apply mapping
        result = mapper.map_neighborhood_fields(df)
        
        # Verify transformation
        transformed_row = result.dataframe.collect()[0]
        
        # Check field mappings
        assert transformed_row.zip_code == "94102"
        
        # Check type conversions
        assert isinstance(transformed_row.walkability_score, int)
        assert transformed_row.walkability_score == 85
        assert isinstance(transformed_row.school_rating, float)
        assert transformed_row.school_rating == 8.5
        
        # Check nested address
        address = transformed_row.address
        assert address.city == "San Francisco"
        assert address.state == "CA"
        assert address.location[0] == -122.4194  # longitude
        assert address.location[1] == 37.7749    # latitude
        
        # Check list handling
        amenities = transformed_row.amenities
        assert isinstance(amenities, list)
        assert "restaurants" in amenities
        assert "shopping" in amenities
        assert "transit" in amenities
    
    def test_wikipedia_transformation(self, spark, temp_config_file):
        """Test Wikipedia field transformation."""
        mapper = FieldMapper(temp_config_file)
        
        schema = StructType([
            StructField("listing_id", StringType(), True),
            StructField("page_id", StringType(), True),
            StructField("title", StringType(), True),
            StructField("latitude", StringType(), True),
            StructField("longitude", StringType(), True),
            StructField("topics", StringType(), True)
        ])
        
        data = [(
            "listing_1",
            "12345",
            "San Francisco",
            "37.7749",
            "-122.4194",
            "city,california,bay area"
        )]
        
        df = spark.createDataFrame(data, schema)
        
        # Apply mapping
        result = mapper.map_wikipedia_fields(df)
        
        # Verify transformation
        transformed_row = result.dataframe.collect()[0]
        
        # Check type conversions
        assert isinstance(transformed_row.page_id, int)
        assert transformed_row.page_id == 12345
        
        # Check nested address
        address = transformed_row.address
        assert address.location[0] == -122.4194  # longitude
        assert address.location[1] == 37.7749    # latitude
        
        # Check list handling
        topics = transformed_row.topics
        assert isinstance(topics, list)
        assert "city" in topics
        assert "california" in topics
        assert "bay area" in topics
    
    def test_missing_optional_fields(self, spark, temp_config_file):
        """Test handling of missing optional fields."""
        mapper = FieldMapper(temp_config_file)
        
        # Create minimal DataFrame with only required fields
        schema = StructType([
            StructField("listing_id", StringType(), True)
        ])
        
        data = [("prop_001",)]
        df = spark.createDataFrame(data, schema)
        
        # Apply mapping - should not fail
        result = mapper.map_property_fields(df)
        
        # Should have successful result with no mapped fields
        assert result.dataframe is not None
        assert len(result.missing_required_fields) == 0
        assert len(result.unmapped_fields) == 0  # No unmapped fields since we only had required ones
        
        # Verify required field is still present
        transformed_row = result.dataframe.collect()[0]
        assert transformed_row.listing_id == "prop_001"
    
    def test_error_handling_invalid_types(self, spark, temp_config_file):
        """Test error handling for invalid type conversions."""
        mapper = FieldMapper(temp_config_file)
        
        # Create DataFrame with invalid data for type conversion
        schema = StructType([
            StructField("listing_id", StringType(), True),
            StructField("listing_price", StringType(), True)  # Invalid float value
        ])
        
        data = [("prop_001", "not_a_number")]
        df = spark.createDataFrame(data, schema)
        
        # Apply mapping - should still work but log warnings
        result = mapper.map_property_fields(df)
        
        # Should have warnings about failed conversions
        assert len(result.warnings) > 0
        
        # But should still produce a result
        assert result.dataframe is not None
        
    def test_configuration_loading(self, integration_config):
        """Test that configuration is loaded correctly."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(integration_config, f)
            temp_path = f.name
        
        try:
            mapper = FieldMapper(temp_path)
            config = mapper.mapping_config
            
            # Verify configuration was loaded
            assert isinstance(config, MappingConfiguration)
            
            # Check property mappings
            prop_config = config.property_mappings
            assert "zip" in prop_config.field_mappings
            assert prop_config.field_mappings["zip"] == "zip_code"
            assert "listing_id" in prop_config.required_fields
            assert "features" in prop_config.list_fields
            
            # Check nested mappings
            assert "address" in prop_config.nested_object_mappings
            address_mapping = prop_config.nested_object_mappings["address"]
            assert "street" in address_mapping
            assert address_mapping["street"] == "address.street"
            
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__])