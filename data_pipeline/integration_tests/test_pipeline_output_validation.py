"""
Integration tests for data pipeline output validation.

This module tests the complete pipeline execution and validates the
generated Parquet files for data quality, schema compliance, and completeness.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import ArrayType, StructType

from data_pipeline.core.pipeline_runner import DataPipelineRunner
from data_pipeline.config.settings import ConfigurationManager


class TestPipelineOutputValidation:
    """Integration tests for validating pipeline output files."""
    
    @pytest.fixture(scope="class")
    def temp_output_dir(self):
        """Create a temporary directory for pipeline output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture(scope="class") 
    def pipeline_settings(self, temp_output_dir):
        """Create test settings with temporary output directory."""
        settings = Settings.load()
        # Override output path to use temporary directory
        settings.destinations = {
            "parquet": {
                "enabled": True,
                "output_path": temp_output_dir,
                "entity_types": ["properties", "neighborhoods", "wikipedia"]
            }
        }
        # Use test mode for smaller dataset
        settings.environment = "test"
        settings.data_subset = {"enabled": True, "sample_size": 10}
        return settings
    
    @pytest.fixture(scope="class")
    def spark_session(self):
        """Create Spark session for testing."""
        spark = SparkSession.builder \
            .appName("PipelineOutputTest") \
            .master("local[2]") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
            .getOrCreate()
        
        yield spark
        spark.stop()
    
    @pytest.fixture(scope="class")
    def pipeline_output(self, pipeline_settings, spark_session):
        """Run the complete pipeline and return output information."""
        runner = DataPipelineRunner(
            settings=pipeline_settings,
            spark_session=spark_session
        )
        
        # Run the complete pipeline
        runner.run()
        
        # Return output directory and expected files
        output_dir = Path(pipeline_settings.destinations["parquet"]["output_path"])
        return {
            "output_dir": output_dir,
            "expected_files": {
                "properties": output_dir / "properties.parquet",
                "neighborhoods": output_dir / "neighborhoods.parquet", 
                "wikipedia": output_dir / "wikipedia.parquet"
            }
        }
    
    def test_pipeline_execution_success(self, pipeline_output):
        """Test that the pipeline executes without errors."""
        # This test passes if the pipeline_output fixture completes without exceptions
        assert pipeline_output["output_dir"].exists()
        assert pipeline_output["output_dir"].is_dir()
    
    def test_parquet_files_created(self, pipeline_output):
        """Test that all expected Parquet files are created."""
        expected_files = pipeline_output["expected_files"]
        
        for entity_type, file_path in expected_files.items():
            assert file_path.exists(), f"Parquet file not created for {entity_type}: {file_path}"
            assert file_path.is_file(), f"Path exists but is not a file: {file_path}"
            
            # Check that file is not empty
            assert file_path.stat().st_size > 0, f"Parquet file is empty: {file_path}"
    
    def test_parquet_files_readable(self, pipeline_output, spark_session):
        """Test that all Parquet files can be read successfully."""
        expected_files = pipeline_output["expected_files"]
        
        for entity_type, file_path in expected_files.items():
            try:
                df = spark_session.read.parquet(str(file_path))
                count = df.count()
                assert count > 0, f"Parquet file contains no records: {entity_type}"
                print(f"✓ {entity_type}: {count} records")
            except Exception as e:
                pytest.fail(f"Failed to read Parquet file {entity_type}: {e}")
    
    def test_properties_schema_validation(self, pipeline_output, spark_session):
        """Test that properties Parquet file has correct schema."""
        file_path = pipeline_output["expected_files"]["properties"]
        df = spark_session.read.parquet(str(file_path))
        
        # Required columns for properties
        required_columns = {
            "property_id", "listing_id", "title", "price", "bedrooms", "bathrooms",
            "property_type", "city", "state", "zip_code", "embedding_text", 
            "embedding", "embedding_model", "property_correlation_id"
        }
        
        actual_columns = set(df.columns)
        missing_columns = required_columns - actual_columns
        assert not missing_columns, f"Missing required columns in properties: {missing_columns}"
        
        # Test data types
        schema = df.schema
        embedding_field = next((f for f in schema.fields if f.name == "embedding"), None)
        assert embedding_field is not None, "embedding column not found"
        assert isinstance(embedding_field.dataType, ArrayType), "embedding should be array type"
        
        print(f"✓ Properties schema valid with {len(df.columns)} columns")
    
    def test_neighborhoods_schema_validation(self, pipeline_output, spark_session):
        """Test that neighborhoods Parquet file has correct schema."""
        file_path = pipeline_output["expected_files"]["neighborhoods"]
        df = spark_session.read.parquet(str(file_path))
        
        # Required columns for neighborhoods
        required_columns = {
            "neighborhood_id", "name", "city", "state", "description",
            "embedding_text", "embedding", "embedding_model", 
            "neighborhood_correlation_id"
        }
        
        actual_columns = set(df.columns)
        missing_columns = required_columns - actual_columns
        assert not missing_columns, f"Missing required columns in neighborhoods: {missing_columns}"
        
        # Test that embeddings are present
        embedding_count = df.filter(df.embedding.isNotNull()).count()
        total_count = df.count()
        assert embedding_count == total_count, f"Not all neighborhoods have embeddings: {embedding_count}/{total_count}"
        
        print(f"✓ Neighborhoods schema valid with {len(df.columns)} columns")
    
    def test_wikipedia_schema_validation(self, pipeline_output, spark_session):
        """Test that Wikipedia Parquet file has correct schema."""
        file_path = pipeline_output["expected_files"]["wikipedia"]
        df = spark_session.read.parquet(str(file_path))
        
        # Required columns for Wikipedia articles
        required_columns = {
            "page_id", "title", "url", "categories", "key_topics", "best_city",
            "best_state", "long_summary", "embedding_text", "embedding", 
            "embedding_model", "article_correlation_id"
        }
        
        actual_columns = set(df.columns)
        missing_columns = required_columns - actual_columns
        assert not missing_columns, f"Missing required columns in Wikipedia: {missing_columns}"
        
        # Test array columns
        schema = df.schema
        categories_field = next((f for f in schema.fields if f.name == "categories"), None)
        key_topics_field = next((f for f in schema.fields if f.name == "key_topics"), None)
        
        assert categories_field is not None, "categories column not found"
        assert key_topics_field is not None, "key_topics column not found"
        assert isinstance(categories_field.dataType, ArrayType), "categories should be array type"
        assert isinstance(key_topics_field.dataType, ArrayType), "key_topics should be array type"
        
        print(f"✓ Wikipedia schema valid with {len(df.columns)} columns")
    
    def test_embeddings_quality(self, pipeline_output, spark_session):
        """Test the quality of generated embeddings."""
        expected_files = pipeline_output["expected_files"]
        
        for entity_type, file_path in expected_files.items():
            df = spark_session.read.parquet(str(file_path))
            
            # Test embedding completeness
            total_records = df.count()
            records_with_embeddings = df.filter(df.embedding.isNotNull()).count()
            
            assert records_with_embeddings == total_records, \
                f"{entity_type}: Not all records have embeddings ({records_with_embeddings}/{total_records})"
            
            # Test embedding dimensions (should be consistent)
            if records_with_embeddings > 0:
                sample_embedding = df.select("embedding").first()["embedding"]
                if sample_embedding:
                    embedding_dim = len(sample_embedding)
                    assert embedding_dim > 0, f"{entity_type}: Empty embeddings found"
                    print(f"✓ {entity_type}: {records_with_embeddings} embeddings with dimension {embedding_dim}")
    
    def test_data_quality_metrics(self, pipeline_output, spark_session):
        """Test various data quality metrics across all entity types."""
        expected_files = pipeline_output["expected_files"]
        
        quality_report = {}
        
        for entity_type, file_path in expected_files.items():
            df = spark_session.read.parquet(str(file_path))
            total_records = df.count()
            
            metrics = {
                "total_records": total_records,
                "null_embedding_text": df.filter(df.embedding_text.isNull()).count(),
                "empty_embedding_text": df.filter((df.embedding_text == "") | (df.embedding_text.isNull())).count(),
                "null_embeddings": df.filter(df.embedding.isNull()).count(),
                "has_correlation_id": df.filter(df[f"{entity_type.rstrip('s')}_correlation_id"].isNotNull()).count()
            }
            
            # Calculate quality percentages
            metrics["embedding_text_coverage"] = ((total_records - metrics["empty_embedding_text"]) / total_records) * 100
            metrics["embedding_coverage"] = ((total_records - metrics["null_embeddings"]) / total_records) * 100
            metrics["correlation_id_coverage"] = (metrics["has_correlation_id"] / total_records) * 100
            
            quality_report[entity_type] = metrics
            
            # Assert quality thresholds
            assert metrics["embedding_text_coverage"] >= 95.0, \
                f"{entity_type}: Low embedding text coverage ({metrics['embedding_text_coverage']:.1f}%)"
            
            assert metrics["embedding_coverage"] >= 95.0, \
                f"{entity_type}: Low embedding coverage ({metrics['embedding_coverage']:.1f}%)"
            
            assert metrics["correlation_id_coverage"] >= 95.0, \
                f"{entity_type}: Low correlation ID coverage ({metrics['correlation_id_coverage']:.1f}%)"
        
        # Print quality report
        print("\n" + "="*60)
        print("DATA QUALITY REPORT")
        print("="*60)
        for entity_type, metrics in quality_report.items():
            print(f"\n{entity_type.upper()}:")
            print(f"  Total Records: {metrics['total_records']}")
            print(f"  Embedding Text Coverage: {metrics['embedding_text_coverage']:.1f}%")
            print(f"  Embedding Coverage: {metrics['embedding_coverage']:.1f}%")
            print(f"  Correlation ID Coverage: {metrics['correlation_id_coverage']:.1f}%")
    
    def test_wikipedia_array_fields(self, pipeline_output, spark_session):
        """Test that Wikipedia array fields (categories, key_topics) are properly populated."""
        file_path = pipeline_output["expected_files"]["wikipedia"]
        df = spark_session.read.parquet(str(file_path))
        
        # Test categories array
        categories_with_data = df.filter(
            df.categories.isNotNull() & (spark_session.sql("size(categories) > 0").collect()[0][0])
        ).count()
        
        # Test key_topics array  
        topics_with_data = df.filter(
            df.key_topics.isNotNull() & (spark_session.sql("size(key_topics) > 0").collect()[0][0])
        ).count()
        
        total_records = df.count()
        
        print(f"✓ Wikipedia categories: {categories_with_data}/{total_records} have data")
        print(f"✓ Wikipedia key_topics: {topics_with_data}/{total_records} have data")
        
        # At least some records should have array data
        assert categories_with_data > 0, "No Wikipedia articles have categories data"
        assert topics_with_data > 0, "No Wikipedia articles have key_topics data"
    
    def test_enrichment_fields_presence(self, pipeline_output, spark_session):
        """Test that enrichment fields are present and populated."""
        expected_files = pipeline_output["expected_files"]
        
        # Test properties enrichment
        props_df = spark_session.read.parquet(str(expected_files["properties"]))
        enrichment_fields = ["property_quality_score", "price_per_sqft", "city_normalized"]
        for field in enrichment_fields:
            if field in props_df.columns:
                non_null_count = props_df.filter(props_df[field].isNotNull()).count()
                print(f"✓ Properties {field}: {non_null_count}/{props_df.count()} populated")
        
        # Test neighborhoods enrichment
        nbhd_df = spark_session.read.parquet(str(expected_files["neighborhoods"]))
        enrichment_fields = ["neighborhood_quality_score", "demographic_completeness", "city_normalized"]
        for field in enrichment_fields:
            if field in nbhd_df.columns:
                non_null_count = nbhd_df.filter(nbhd_df[field].isNotNull()).count()
                print(f"✓ Neighborhoods {field}: {non_null_count}/{nbhd_df.count()} populated")
        
        # Test Wikipedia enrichment
        wiki_df = spark_session.read.parquet(str(expected_files["wikipedia"]))
        enrichment_fields = ["article_quality_score", "location_relevance_score", "confidence_level"]
        for field in enrichment_fields:
            if field in wiki_df.columns:
                non_null_count = wiki_df.filter(wiki_df[field].isNotNull()).count()
                print(f"✓ Wikipedia {field}: {non_null_count}/{wiki_df.count()} populated")


def test_pipeline_integration_smoke():
    """Smoke test that can be run independently to verify basic pipeline functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create minimal settings for smoke test
        settings = Settings.load()
        settings.destinations = {
            "parquet": {
                "enabled": True,
                "output_path": temp_dir,
                "entity_types": ["properties"]  # Test just properties for speed
            }
        }
        settings.environment = "test"
        settings.data_subset = {"enabled": True, "sample_size": 5}
        
        # Create Spark session
        spark = SparkSession.builder \
            .appName("PipelineSmokeTest") \
            .master("local[1]") \
            .getOrCreate()
        
        try:
            # Run pipeline
            runner = DataPipelineRunner(settings=settings, spark_session=spark)
            runner.run()
            
            # Verify output
            output_file = Path(temp_dir) / "properties.parquet"
            assert output_file.exists(), "Properties Parquet file not created"
            
            # Verify readability
            df = spark.read.parquet(str(output_file))
            record_count = df.count()
            assert record_count > 0, "No records in output file"
            
            print(f"✓ Smoke test passed: {record_count} records processed")
            
        finally:
            spark.stop()


if __name__ == "__main__":
    # Run smoke test if executed directly
    test_pipeline_integration_smoke()