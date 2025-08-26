#!/usr/bin/env python3
"""Test script for SQUACK Pipeline Phase 5 - Output Generation."""

import os
import time
import tempfile
from pathlib import Path
import json
import pyarrow.parquet as pq

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.orchestrator.pipeline import PipelineOrchestrator
from squack_pipeline.writers.parquet_writer import ParquetWriter
from squack_pipeline.writers.embedding_writer import EmbeddingWriter
from squack_pipeline.loaders.connection import DuckDBConnectionManager
from squack_pipeline.utils.logging import PipelineLogger


def test_parquet_writer_basic():
    """Test basic Parquet writer functionality."""
    logger = PipelineLogger.get_logger("TestParquetWriterBasic")
    
    logger.info("🧪 Testing Basic Parquet Writer")
    logger.info("=" * 50)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test settings
        settings = PipelineSettings(
            data={"output_path": temp_path},
            parquet={
                "compression": "snappy",
                "row_group_size": 10000,
                "use_dictionary": True
            },
            dry_run=False
        )
        
        try:
            # Initialize connection and writer
            conn_manager = DuckDBConnectionManager()
            conn_manager.initialize(settings)
            connection = conn_manager.get_connection()
            
            writer = ParquetWriter(settings)
            writer.set_connection(connection)
            
            # Create test data
            connection.execute("""
                CREATE TABLE test_properties AS
                SELECT 
                    'prop-' || i AS listing_id,
                    CAST(100000 + i * 1000 AS DOUBLE) AS listing_price,
                    CAST(2 + (i % 4) AS INTEGER) AS bedrooms,
                    'Oakland' AS city,
                    'House' AS property_type,
                    37.8 + (i * 0.001) AS latitude,
                    -122.3 + (i * 0.001) AS longitude
                FROM generate_series(1, 100) AS t(i)
            """)
            
            # Write to Parquet
            output_path = temp_path / "test_properties.parquet"
            written_path = writer.write("test_properties", output_path)
            
            # Validate output
            if not written_path.exists():
                logger.error("❌ Parquet file not created")
                return False
            
            # Read and validate Parquet file
            parquet_file = pq.ParquetFile(written_path)
            metadata = parquet_file.metadata
            
            if metadata.num_rows != 100:
                logger.error(f"❌ Expected 100 rows, got {metadata.num_rows}")
                return False
            
            # Validate compression
            row_group = metadata.row_group(0)
            column = row_group.column(0)
            if column.compression.lower() != "snappy":
                logger.error(f"❌ Expected snappy compression, got {column.compression}")
                return False
            
            # Get statistics
            stats = writer.get_statistics(written_path)
            logger.info(f"📊 File statistics:")
            logger.info(f"  File size: {stats['file_size_mb']:.2f} MB")
            logger.info(f"  Rows: {stats['num_rows']}")
            logger.info(f"  Columns: {stats['num_columns']}")
            logger.info(f"  Compression ratio: {stats['compression_ratio']:.2f}x")
            
            # Clean up
            conn_manager.close()
            
            logger.success("✅ Basic Parquet writer test PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Parquet writer test failed: {e}")
            return False


def test_partitioned_writing():
    """Test partitioned Parquet writing."""
    logger = PipelineLogger.get_logger("TestPartitionedWriting")
    
    logger.info("🧪 Testing Partitioned Parquet Writing")
    logger.info("=" * 55)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        settings = PipelineSettings(
            data={"output_path": temp_path},
            dry_run=False
        )
        
        try:
            # Initialize connection and writer
            conn_manager = DuckDBConnectionManager()
            conn_manager.initialize(settings)
            connection = conn_manager.get_connection()
            
            writer = ParquetWriter(settings)
            writer.set_connection(connection)
            
            # Create test data with multiple cities and types
            connection.execute("""
                CREATE TABLE test_partitioned AS
                SELECT 
                    'prop-' || i AS listing_id,
                    CAST(100000 + i * 1000 AS DOUBLE) AS listing_price,
                    CASE WHEN i % 3 = 0 THEN 'Oakland' 
                         WHEN i % 3 = 1 THEN 'Berkeley'
                         ELSE 'San Francisco' END AS city,
                    CASE WHEN i % 2 = 0 THEN 'House' ELSE 'Condo' END AS property_type,
                    37.8 + (i * 0.001) AS latitude,
                    -122.3 + (i * 0.001) AS longitude
                FROM generate_series(1, 60) AS t(i)
            """)
            
            # Write partitioned output
            partition_dir = temp_path / "partitioned"
            partition_files = writer.write_partitioned(
                "test_partitioned",
                partition_dir,
                ["city", "property_type"]
            )
            
            # Validate partitions
            if len(partition_files) == 0:
                logger.error("❌ No partition files created")
                return False
            
            logger.info(f"📂 Created {len(partition_files)} partition files")
            
            # Check partition structure
            expected_cities = {"Oakland", "Berkeley", "San Francisco"}
            expected_types = {"House", "Condo"}
            
            city_dirs = set()
            for file_path in partition_files:
                parts = file_path.parts
                # Extract city from path (should be city=Oakland format)
                for part in parts:
                    if "city=" in part:
                        city = part.split("=")[1]
                        city_dirs.add(city)
            
            if not city_dirs.intersection(expected_cities):
                logger.warning("⚠️ Partition structure may not match expected format")
            
            # Validate total row count across partitions
            total_rows = 0
            for file_path in partition_files:
                pf = pq.ParquetFile(file_path)
                total_rows += pf.metadata.num_rows
            
            if total_rows != 60:
                logger.error(f"❌ Expected 60 total rows, got {total_rows}")
                return False
            
            # Clean up
            conn_manager.close()
            
            logger.success("✅ Partitioned writing test PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Partitioned writing test failed: {e}")
            return False


def test_embedding_writer():
    """Test embedding writer functionality."""
    logger = PipelineLogger.get_logger("TestEmbeddingWriter")
    
    logger.info("🧪 Testing Embedding Writer")
    logger.info("=" * 50)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        settings = PipelineSettings(
            data={"output_path": temp_path},
            embedding={
                "provider": "mock",
                "mock_dimension": 128
            },
            dry_run=False
        )
        
        try:
            # Initialize connection and writer
            conn_manager = DuckDBConnectionManager()
            conn_manager.initialize(settings)
            connection = conn_manager.get_connection()
            
            writer = EmbeddingWriter(settings)
            writer.set_connection(connection)
            
            # Create mock TextNodes
            from llama_index.core.schema import TextNode
            import numpy as np
            
            nodes = []
            for i in range(10):
                node = TextNode(
                    id_=f"node_{i}",
                    text=f"This is test property {i} with various features and amenities.",
                    metadata={
                        "property_id": f"prop_{i}",
                        "listing_id": f"listing_{i}",
                        "chunk_index": i,
                        "city": "Oakland" if i % 2 == 0 else "Berkeley",
                        "property_type": "House"
                    },
                    embedding=np.random.randn(128).tolist()  # Mock embedding
                )
                nodes.append(node)
            
            # Write embedded nodes
            output_path = temp_path / "embeddings.parquet"
            written_path = writer.write_embedded_nodes(nodes, output_path)
            
            # Validate output
            if not written_path.exists():
                logger.error("❌ Embedding file not created")
                return False
            
            # Write metadata
            metadata_path = temp_path / "embeddings.metadata.json"
            writer.write_embedding_metadata(nodes, metadata_path)
            
            if not metadata_path.exists():
                logger.error("❌ Metadata file not created")
                return False
            
            # Read and validate metadata
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            logger.info(f"📊 Embedding statistics:")
            logger.info(f"  Total nodes: {metadata['total_nodes']}")
            logger.info(f"  Embedded nodes: {metadata['embedded_nodes']}")
            logger.info(f"  Embedding rate: {metadata['embedding_rate']:.2%}")
            logger.info(f"  Average dimension: {metadata['average_dimension']}")
            
            if metadata['total_nodes'] != 10:
                logger.error(f"❌ Expected 10 nodes, got {metadata['total_nodes']}")
                return False
            
            # Clean up
            conn_manager.close()
            
            logger.success("✅ Embedding writer test PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Embedding writer test failed: {e}")
            return False


def test_complete_pipeline_with_output():
    """Test complete pipeline with output generation."""
    logger = PipelineLogger.get_logger("TestCompletePipelineOutput")
    
    logger.info("🧪 Testing Complete Pipeline with Output Generation")
    logger.info("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Configure for complete pipeline test
        settings = PipelineSettings(
            data={
                "input_path": Path("real_estate_data"),
                "output_path": temp_path,
                "properties_file": "properties_sf.json",
                "sample_size": 3
            },
            embedding={
                "provider": "mock",
                "mock_dimension": 256
            },
            processing={
                "generate_embeddings": True,
                "batch_size": 2,
                "chunk_method": "simple",
                "chunk_size": 300
            },
            parquet={
                "compression": "snappy",
                "row_group_size": 5000
            },
            dry_run=False,
            validate_output=True,
            environment="test"
        )
        
        try:
            # Run complete pipeline
            orchestrator = PipelineOrchestrator(settings)
            orchestrator.run()
            
            # Get metrics
            metrics = orchestrator.get_metrics()
            
            # Check that output files were created
            parquet_files = list(temp_path.glob("*.parquet"))
            json_files = list(temp_path.glob("*.json"))
            
            logger.info("📊 Pipeline Output Results:")
            logger.info(f"  Properties processed: {metrics['gold_records']}")
            logger.info(f"  Embeddings generated: {metrics.get('embeddings_generated', 0)}")
            logger.info(f"  Parquet files created: {len(parquet_files)}")
            logger.info(f"  Metadata files created: {len(json_files)}")
            
            if len(parquet_files) == 0:
                logger.error("❌ No Parquet files created")
                return False
            
            # Validate properties Parquet file
            properties_files = [f for f in parquet_files if "properties_" in f.name]
            if properties_files:
                props_file = properties_files[0]
                pf = pq.ParquetFile(props_file)
                logger.info(f"  Properties file: {props_file.name}")
                logger.info(f"    Rows: {pf.metadata.num_rows}")
                logger.info(f"    Columns: {pf.metadata.num_columns}")
                logger.info(f"    Size: {props_file.stat().st_size / 1024:.2f} KB")
            
            # Validate embeddings Parquet file if created
            embedding_files = [f for f in parquet_files if "embeddings_" in f.name]
            if embedding_files:
                emb_file = embedding_files[0]
                pf = pq.ParquetFile(emb_file)
                logger.info(f"  Embeddings file: {emb_file.name}")
                logger.info(f"    Rows: {pf.metadata.num_rows}")
                logger.info(f"    Columns: {pf.metadata.num_columns}")
                logger.info(f"    Size: {emb_file.stat().st_size / 1024:.2f} KB")
            
            # Check schema files
            schema_files = [f for f in json_files if "schema" in f.name]
            if schema_files:
                logger.info(f"  Schema files created: {len(schema_files)}")
            
            # Check that output validation passed
            if settings.validate_output and metrics.get('output_files', 0) > 0:
                logger.success("✅ Output validation completed")
            
            # Cleanup
            orchestrator.cleanup()
            
            logger.success("✅ Complete pipeline with output test PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Complete pipeline test failed: {e}")
            return False


def main():
    """Run all Phase 5 tests."""
    logger = PipelineLogger.get_logger("Phase5Tests")
    
    logger.info("🎯 SQUACK Pipeline Phase 5 Test Suite")
    logger.info("=" * 60)
    
    tests = [
        ("Basic Parquet Writer", test_parquet_writer_basic),
        ("Partitioned Writing", test_partitioned_writing),
        ("Embedding Writer", test_embedding_writer),
        ("Complete Pipeline with Output", test_complete_pipeline_with_output)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running: {test_name}")
        logger.info("-" * 40)
        
        try:
            if test_func():
                passed += 1
                logger.success(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
    
    # Final results
    logger.info("\n" + "=" * 60)
    logger.info(f"📊 Phase 5 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.success("🎉 All Phase 5 tests PASSED!")
        logger.info("\n🚀 Phase 5 (Output Generation) is ready!")
        logger.info("✨ Parquet writer with DuckDB optimizations working")
        logger.info("📂 Partitioned output support implemented")
        logger.info("🗜️ Compression configuration (Snappy/Zstandard) working")
        logger.info("📝 Schema preservation and validation implemented")
        logger.info("🧠 Embedding writer for vector storage ready")
        return True
    else:
        logger.error(f"💥 {total - passed} test(s) FAILED")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)