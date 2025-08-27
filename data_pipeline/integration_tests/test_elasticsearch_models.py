"""
Tests for Elasticsearch Pydantic models and transformations.

Validates the type safety, configuration management, and transformation
logic in the refactored Elasticsearch writer.
"""

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, DecimalType, DoubleType

from data_pipeline.writers.elasticsearch.models import (
    EntityType,
    IndexSettings,
    SchemaTransformation,
    WriteOperation,
    WriteResult,
    ElasticsearchWriterSettings,
)
from data_pipeline.writers.elasticsearch.transformations import DataFrameTransformer


class TestElasticsearchModels:
    """Test Pydantic models for Elasticsearch operations."""

    def test_index_settings_validation(self):
        """Test IndexSettings model validation."""
        # Valid settings
        settings = IndexSettings(
            name="test_index",
            entity_type=EntityType.PROPERTIES,
            id_field="listing_id",
        )
        assert settings.name == "test_index"
        assert settings.entity_type == EntityType.PROPERTIES
        
        # Invalid index name (uppercase)
        with pytest.raises(ValueError, match="must be lowercase"):
            IndexSettings(
                name="Test_Index",
                entity_type=EntityType.PROPERTIES,
                id_field="listing_id",
            )

    def test_elasticsearch_writer_settings(self):
        """Test ElasticsearchWriterSettings model."""
        settings = ElasticsearchWriterSettings(
            batch_size=500,
        )
        
        # Test index creation for each entity type
        for entity_type in EntityType:
            index_settings = settings.create_index_settings(entity_type)
            assert index_settings.name == entity_type.value
            assert index_settings.entity_type == entity_type
            assert index_settings.id_field  # Should have appropriate ID field

    def test_write_operation_configuration(self):
        """Test WriteOperation configuration."""
        index_settings = IndexSettings(
            name="test_properties",
            entity_type=EntityType.PROPERTIES,
            id_field="listing_id",
        )
        
        operation = WriteOperation(index_settings=index_settings)
        spark_options = operation.get_spark_options()
        
        assert "es.resource" in spark_options
        assert spark_options["es.resource"] == "test_properties"
        assert spark_options["es.mapping.id"] == "id"

    def test_write_result_model(self):
        """Test WriteResult model."""
        result = WriteResult(
            success=True,
            index_name="test_index",
            entity_type=EntityType.PROPERTIES,
            record_count=100,
            fields_written=["id", "name", "price"],
        )
        
        assert result.is_success()
        assert result.record_count == 100
        
        # Test failure case
        error_result = WriteResult(
            success=False,
            index_name="test_index",
            entity_type=EntityType.PROPERTIES,
            record_count=0,
            fields_written=[],
            error_message="Connection failed",
        )
        
        assert not error_result.is_success()
        assert error_result.error_message == "Connection failed"

    def test_schema_transformation_config(self):
        """Test SchemaTransformation configuration."""
        transform = SchemaTransformation(
            convert_decimals=True,
            add_geo_point=True,
            excluded_fields={"internal_field", "temp_field"},
        )
        
        assert transform.convert_decimals
        assert transform.add_geo_point
        assert "internal_field" in transform.excluded_fields


@pytest.mark.integration
class TestDataFrameTransformer:
    """Test DataFrame transformation functionality."""

    @pytest.fixture(scope="class")
    def spark_session(self):
        """Create Spark session for tests."""
        spark = SparkSession.builder \
            .appName("TransformerTest") \
            .master("local[1]") \
            .getOrCreate()
        
        spark.sparkContext.setLogLevel("WARN")
        yield spark
        spark.stop()

    @pytest.fixture
    def transformer(self, spark_session):
        """Create transformer instance."""
        return DataFrameTransformer(spark_session)

    def test_simple_decimal_conversion(self, transformer, spark_session):
        """Test simple decimal to double conversion."""
        from decimal import Decimal
        
        # Create DataFrame with decimal column
        schema = StructType([
            StructField("id", StringType(), True),
            StructField("price", DecimalType(10, 2), True),
            StructField("name", StringType(), True),
        ])
        
        data = [("1", Decimal("100.50"), "Test Property")]
        df = spark_session.createDataFrame(data, schema)
        
        # Transform
        config = SchemaTransformation(convert_decimals=True, add_geo_point=False)
        result_df = transformer.transform_for_elasticsearch(df, config, "id")
        
        # Check that decimal was converted
        price_field = [f for f in result_df.schema.fields if f.name == "price"][0]
        assert isinstance(price_field.dataType, DoubleType)

    def test_geo_point_creation(self, transformer, spark_session):
        """Test geo_point field creation."""
        data = [
            ("1", "Location 1", 37.7749, -122.4194),
            ("2", "Location 2", 37.8044, -122.2712),
        ]
        
        df = spark_session.createDataFrame(data, ["id", "name", "latitude", "longitude"])
        
        # Transform with geo_point
        config = SchemaTransformation(convert_decimals=False, add_geo_point=True)
        result_df = transformer.transform_for_elasticsearch(df, config, "id")
        
        # Check location field was added
        assert "location" in result_df.columns
        
        # Verify structure
        location_data = result_df.select("location").collect()
        for row in location_data:
            if row.location is not None:
                assert hasattr(row.location, "lat")
                assert hasattr(row.location, "lon")

    def test_field_exclusion(self, transformer, spark_session):
        """Test field exclusion functionality."""
        data = [("1", "Test", "secret", "public")]
        df = spark_session.createDataFrame(data, ["id", "name", "internal_field", "description"])
        
        # Transform with field exclusion
        config = SchemaTransformation(
            convert_decimals=False,
            add_geo_point=False,
            excluded_fields={"internal_field"}
        )
        result_df = transformer.transform_for_elasticsearch(df, config, "id")
        
        # Check excluded field is not present
        assert "internal_field" not in result_df.columns
        assert "name" in result_df.columns
        assert "description" in result_df.columns

    def test_id_field_mapping(self, transformer, spark_session):
        """Test ID field mapping."""
        data = [("prop123", "Test Property")]
        df = spark_session.createDataFrame(data, ["listing_id", "name"])
        
        # Transform with ID field mapping
        config = SchemaTransformation(convert_decimals=False, add_geo_point=False)
        result_df = transformer.transform_for_elasticsearch(df, config, "listing_id")
        
        # Check ID field was created
        assert "id" in result_df.columns
        
        # Verify ID values match listing_id
        id_values = [row.id for row in result_df.select("id").collect()]
        listing_id_values = [row.listing_id for row in result_df.select("listing_id").collect()]
        assert id_values == listing_id_values

    def test_transformation_summary(self, transformer, spark_session):
        """Test transformation summary generation."""
        data = [("1", "Test", 37.7749, -122.4194)]
        df = spark_session.createDataFrame(data, ["id", "name", "latitude", "longitude"])
        
        summary = transformer.get_transformation_summary(df)
        
        assert summary["column_count"] == 4
        assert "latitude" in summary["columns"]
        assert summary["has_geo_fields"]
        assert summary["has_id_field"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])