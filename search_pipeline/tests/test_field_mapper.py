"""Tests for field mapping functionality in search pipeline."""

import pytest
import tempfile
import json
import os
from unittest.mock import Mock, patch
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType

# Import field mapper components
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from data_pipeline.transformers.field_mapper import (
    FieldMapper,
    FieldMappingConfig,
    MappingConfiguration,
    FieldMappingResult
)
from search_pipeline.builders.base import BaseDocumentBuilder
from search_pipeline.builders.property_builder import PropertyDocumentBuilder


@pytest.fixture
def spark():
    """Create a Spark session for testing."""
    return SparkSession.builder.appName("test_field_mapper").getOrCreate()


@pytest.fixture
def sample_field_mappings():
    """Sample field mappings configuration."""
    return {
        "property_mappings": {
            "field_mappings": {
                "zip": "zip_code",
                "listing_price": "price"
            },
            "nested_object_mappings": {
                "address": {
                    "street": "address.street",
                    "city": "address.city",
                    "zip": "address.zip_code",
                    "latitude": "address.location[1]",
                    "longitude": "address.location[0]"
                }
            },
            "type_conversions": {
                "price": "float",
                "bedrooms": "int",
                "latitude": "float",
                "longitude": "float"
            },
            "list_fields": ["features", "amenities"],
            "required_fields": ["listing_id"]
        },
        "neighborhood_mappings": {
            "field_mappings": {"zip": "zip_code"},
            "nested_object_mappings": {},
            "type_conversions": {"population": "int"},
            "list_fields": ["amenities"],
            "required_fields": ["listing_id", "neighborhood_id"]
        },
        "wikipedia_mappings": {
            "field_mappings": {},
            "nested_object_mappings": {},
            "type_conversions": {"page_id": "int"},
            "list_fields": ["topics"],
            "required_fields": ["listing_id", "page_id", "title"]
        },
        "wikipedia_enrichment_mappings": {}
    }


@pytest.fixture
def temp_config_file(sample_field_mappings):
    """Create a temporary configuration file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_field_mappings, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def field_mapper(temp_config_file):
    """Create a FieldMapper instance with test configuration."""
    return FieldMapper(temp_config_file)


class TestFieldMappingConfig:
    """Test FieldMappingConfig model."""
    
    def test_valid_config(self):
        """Test creating valid field mapping config."""
        config = FieldMappingConfig(
            field_mappings={"zip": "zip_code"},
            type_conversions={"price": "float"},
            list_fields=["features"],
            required_fields=["listing_id"]
        )
        
        assert config.field_mappings["zip"] == "zip_code"
        assert config.type_conversions["price"] == "float"
        assert "features" in config.list_fields
        assert "listing_id" in config.required_fields
    
    def test_invalid_type_conversion(self):
        """Test invalid type conversion raises error."""
        with pytest.raises(ValueError, match="Unsupported type conversion"):
            FieldMappingConfig(type_conversions={"price": "invalid_type"})


class TestMappingConfiguration:
    """Test MappingConfiguration model."""
    
    def test_complete_config(self, sample_field_mappings):
        """Test creating complete mapping configuration."""
        config = MappingConfiguration(**sample_field_mappings)
        
        assert config.property_mappings is not None
        assert config.neighborhood_mappings is not None
        assert config.wikipedia_mappings is not None


class TestFieldMapper:
    """Test FieldMapper class."""
    
    def test_initialization(self, temp_config_file):
        """Test FieldMapper initialization."""
        mapper = FieldMapper(temp_config_file)
        assert mapper.mapping_config is not None
        assert isinstance(mapper.mapping_config, MappingConfiguration)
    
    def test_missing_config_file(self):
        """Test error when config file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            FieldMapper("/nonexistent/path/config.json")
    
    def test_invalid_json_config(self):
        """Test error when config file has invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_path = f.name
        
        try:
            with pytest.raises(json.JSONDecodeError):
                FieldMapper(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_map_property_fields_basic(self, spark, field_mapper):
        """Test basic property field mapping."""
        # Create test DataFrame
        schema = StructType([
            StructField("listing_id", StringType(), True),
            StructField("zip", StringType(), True),
            StructField("listing_price", FloatType(), True)
        ])
        
        data = [("prop_1", "12345", 500000.0)]
        df = spark.createDataFrame(data, schema)
        
        # Apply mapping
        result = field_mapper.map_property_fields(df)
        
        assert isinstance(result, FieldMappingResult)
        assert result.dataframe is not None
        assert "zip" in result.mapped_fields
        assert "listing_price" in result.mapped_fields
        
        # Check that mapped fields exist in result DataFrame
        result_columns = result.dataframe.columns
        assert "zip_code" in result_columns
        assert "price" in result_columns
    
    def test_map_property_fields_with_address(self, spark, field_mapper):
        """Test property field mapping with nested address object."""
        # Create test DataFrame
        schema = StructType([
            StructField("listing_id", StringType(), True),
            StructField("street", StringType(), True),
            StructField("city", StringType(), True),
            StructField("zip", StringType(), True),
            StructField("latitude", FloatType(), True),
            StructField("longitude", FloatType(), True)
        ])
        
        data = [("prop_1", "123 Main St", "San Francisco", "94102", 37.7749, -122.4194)]
        df = spark.createDataFrame(data, schema)
        
        # Apply mapping
        result = field_mapper.map_property_fields(df)
        
        # Check that address struct was created
        assert "address" in result.dataframe.columns
        
        # Verify address structure
        first_row = result.dataframe.collect()[0]
        address = first_row.address
        assert address is not None
        assert address.street == "123 Main St"
        assert address.city == "San Francisco"
        assert address.zip_code == "94102"
        assert address.location is not None
        assert len(address.location) == 2  # [longitude, latitude]
    
    def test_missing_required_fields(self, spark, field_mapper):
        """Test error when required fields are missing."""
        # Create DataFrame without required listing_id
        schema = StructType([
            StructField("zip", StringType(), True),
        ])
        
        data = [("12345",)]
        df = spark.createDataFrame(data, schema)
        
        # Should raise ValueError for missing required fields
        with pytest.raises(ValueError, match="Missing required fields"):
            field_mapper.map_property_fields(df)
    
    def test_type_conversions(self, spark, field_mapper):
        """Test type conversions in field mapping."""
        # Create DataFrame with string values that should be converted
        schema = StructType([
            StructField("listing_id", StringType(), True),
            StructField("listing_price", StringType(), True),  # String to be converted to float
            StructField("bedrooms", StringType(), True)       # String to be converted to int
        ])
        
        data = [("prop_1", "500000.0", "3")]
        df = spark.createDataFrame(data, schema)
        
        # Apply mapping
        result = field_mapper.map_property_fields(df)
        
        # Check that types were converted
        first_row = result.dataframe.collect()[0]
        assert isinstance(first_row.price, float)
        assert isinstance(first_row.bedrooms, int)
    
    def test_validate_required_fields(self, spark, field_mapper):
        """Test validation of required fields."""
        # Create DataFrame with all required fields
        schema = StructType([
            StructField("listing_id", StringType(), True),
            StructField("zip", StringType(), True)
        ])
        
        data = [("prop_1", "12345")]
        df = spark.createDataFrame(data, schema)
        
        # Should return empty list (no missing fields)
        missing = field_mapper.validate_required_fields(df, "property")
        assert missing == []
        
        # Test with missing fields
        schema_missing = StructType([
            StructField("zip", StringType(), True)
        ])
        
        data_missing = [("12345",)]
        df_missing = spark.createDataFrame(data_missing, schema_missing)
        
        missing = field_mapper.validate_required_fields(df_missing, "property")
        assert "listing_id" in missing
    
    def test_neighborhood_field_mapping(self, spark, field_mapper):
        """Test neighborhood-specific field mapping."""
        schema = StructType([
            StructField("listing_id", StringType(), True),
            StructField("neighborhood_id", StringType(), True),
            StructField("zip", StringType(), True),
            StructField("population", StringType(), True)
        ])
        
        data = [("listing_1", "neighborhood_1", "12345", "50000")]
        df = spark.createDataFrame(data, schema)
        
        result = field_mapper.map_neighborhood_fields(df)
        
        assert "zip_code" in result.dataframe.columns
        first_row = result.dataframe.collect()[0]
        assert isinstance(first_row.population, int)
    
    def test_wikipedia_field_mapping(self, spark, field_mapper):
        """Test Wikipedia-specific field mapping."""
        schema = StructType([
            StructField("listing_id", StringType(), True),
            StructField("page_id", StringType(), True),
            StructField("title", StringType(), True)
        ])
        
        data = [("listing_1", "12345", "San Francisco")]
        df = spark.createDataFrame(data, schema)
        
        result = field_mapper.map_wikipedia_fields(df)
        
        first_row = result.dataframe.collect()[0]
        assert isinstance(first_row.page_id, int)


class TestBaseDocumentBuilderIntegration:
    """Test integration of FieldMapper with BaseDocumentBuilder."""
    
    @patch('search_pipeline.builders.base.FieldMapper')
    def test_base_builder_field_mapper_initialization(self, mock_field_mapper_class):
        """Test that BaseDocumentBuilder initializes field mapper."""
        mock_mapper = Mock()
        mock_field_mapper_class.return_value = mock_mapper
        
        # Create builder
        builder = BaseDocumentBuilder()
        
        # Should have called FieldMapper constructor
        mock_field_mapper_class.assert_called_once()
        assert builder.field_mapper == mock_mapper
    
    def test_apply_field_mapping(self, spark):
        """Test apply_field_mapping method."""
        # Mock field mapper
        mock_mapper = Mock()
        mock_result = FieldMappingResult(
            dataframe=Mock(),
            mapped_fields=["zip"],
            missing_required_fields=[],
            unmapped_fields=[],
            warnings=[]
        )
        mock_mapper.map_property_fields.return_value = mock_result
        
        # Create builder and set mock mapper
        builder = BaseDocumentBuilder()
        builder.field_mapper = mock_mapper
        
        # Create test DataFrame
        schema = StructType([
            StructField("listing_id", StringType(), True),
            StructField("zip", StringType(), True)
        ])
        data = [("prop_1", "12345")]
        df = spark.createDataFrame(data, schema)
        
        # Apply field mapping
        result_df = builder.apply_field_mapping(df, "property")
        
        # Verify mapper was called
        mock_mapper.map_property_fields.assert_called_once_with(df)
        assert result_df == mock_result.dataframe
    
    def test_validate_field_mapping_requirements(self, spark):
        """Test validate_field_mapping_requirements method."""
        # Mock field mapper
        mock_mapper = Mock()
        mock_mapper.validate_required_fields.return_value = []
        
        # Create builder and set mock mapper
        builder = BaseDocumentBuilder()
        builder.field_mapper = mock_mapper
        
        # Create test DataFrame
        schema = StructType([StructField("listing_id", StringType(), True)])
        data = [("prop_1",)]
        df = spark.createDataFrame(data, schema)
        
        # Should not raise exception
        builder.validate_field_mapping_requirements(df, "property")
        
        # Test with missing fields
        mock_mapper.validate_required_fields.return_value = ["required_field"]
        
        with pytest.raises(ValueError, match="Missing required fields"):
            builder.validate_field_mapping_requirements(df, "property")


class TestPropertyDocumentBuilderIntegration:
    """Test PropertyDocumentBuilder with field mapping."""
    
    def test_property_builder_with_field_mapping(self, spark, temp_config_file):
        """Test that PropertyDocumentBuilder uses field mapping."""
        # Create property builder with real field mapper
        builder = PropertyDocumentBuilder()
        
        # Mock the field mapper to avoid complex setup
        mock_mapper = Mock()
        mock_result = FieldMappingResult(
            dataframe=Mock(),
            mapped_fields=["zip"],
            missing_required_fields=[],
            unmapped_fields=[],
            warnings=[]
        )
        
        # Configure mock DataFrame that collect() will return
        mock_dataframe = Mock()
        mock_row = Mock()
        mock_row.asDict.return_value = {
            "listing_id": "prop_1",
            "price": 500000.0,
            "bedrooms": 3,
            "bathrooms": 2.0
        }
        mock_dataframe.collect.return_value = [mock_row]
        mock_result.dataframe = mock_dataframe
        
        mock_mapper.map_property_fields.return_value = mock_result
        mock_mapper.validate_required_fields.return_value = []
        
        builder.field_mapper = mock_mapper
        
        # Create test DataFrame
        schema = StructType([
            StructField("listing_id", StringType(), True),
            StructField("zip", StringType(), True)
        ])
        data = [("prop_1", "12345")]
        df = spark.createDataFrame(data, schema)
        
        # Transform should call field mapping
        documents = builder.transform(df)
        
        # Verify field mapper was used
        mock_mapper.validate_required_fields.assert_called_once_with(df, "property")
        mock_mapper.map_property_fields.assert_called_once_with(df)
        
        # Should return documents
        assert len(documents) > 0


if __name__ == "__main__":
    pytest.main([__file__])