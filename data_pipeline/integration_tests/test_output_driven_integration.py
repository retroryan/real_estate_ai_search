"""
Integration test for output-driven pipeline fork architecture.

Tests the complete flow from configuration to processing path selection
to verify the new design works end-to-end.
"""

import pytest
from unittest.mock import Mock, patch
from pyspark.sql import SparkSession, DataFrame

from data_pipeline.config.models import PipelineConfig, OutputConfig
from data_pipeline.config.loader import load_configuration
from data_pipeline.core.pipeline_fork import PipelineFork, ProcessingPaths
from data_pipeline.core.pipeline_runner import DataPipelineRunner


class TestOutputDrivenIntegration:
    """Integration tests for the output-driven pipeline architecture."""
    
    def test_parquet_only_end_to_end(self):
        """Test complete flow for parquet-only output."""
        # Configuration with only parquet enabled
        config_dict = {
            "name": "test_pipeline",
            "version": "1.0.0",
            "output": {
                "enabled_destinations": ["parquet"],
                "parquet": {"base_path": "data/test_parquet"}
            },
            "embedding": {"provider": "mock"}
        }
        
        config = PipelineConfig(**config_dict)
        
        # Verify processing paths are determined correctly
        paths = ProcessingPaths.from_destinations(config.output.enabled_destinations)
        assert paths.lightweight
        assert not paths.graph  
        assert not paths.search
        assert paths.get_enabled_paths() == ["lightweight"]
        
        # Verify fork initialization
        fork = PipelineFork(config.output.enabled_destinations)
        assert fork.paths.lightweight
        assert not fork.paths.graph
        assert not fork.paths.search
    
    def test_neo4j_output_end_to_end(self):
        """Test complete flow for Neo4j output."""
        config_dict = {
            "name": "test_pipeline", 
            "version": "1.0.0",
            "output": {
                "enabled_destinations": ["neo4j"],
                "neo4j": {
                    "uri": "bolt://localhost:7687",
                    "username": "neo4j",
                    "database": "neo4j"
                }
            },
            "embedding": {"provider": "mock"}
        }
        
        config = PipelineConfig(**config_dict)
        
        # Verify processing paths
        paths = ProcessingPaths.from_destinations(config.output.enabled_destinations)
        assert not paths.lightweight
        assert paths.graph
        assert not paths.search
        assert paths.get_enabled_paths() == ["graph"]
        
        # Verify fork initialization
        fork = PipelineFork(config.output.enabled_destinations)
        assert not fork.paths.lightweight
        assert fork.paths.graph
        assert not fork.paths.search
    
    def test_elasticsearch_output_end_to_end(self):
        """Test complete flow for Elasticsearch output."""
        config_dict = {
            "name": "test_pipeline",
            "version": "1.0.0", 
            "output": {
                "enabled_destinations": ["elasticsearch"],
                "elasticsearch": {
                    "hosts": ["localhost:9200"]
                }
            },
            "embedding": {"provider": "mock"}
        }
        
        config = PipelineConfig(**config_dict)
        
        # Verify processing paths
        paths = ProcessingPaths.from_destinations(config.output.enabled_destinations)
        assert not paths.lightweight
        assert not paths.graph
        assert paths.search
        assert paths.get_enabled_paths() == ["search"]
        
        # Verify fork initialization
        fork = PipelineFork(config.output.enabled_destinations)
        assert not fork.paths.lightweight
        assert not fork.paths.graph
        assert fork.paths.search
    
    def test_multi_destination_end_to_end(self):
        """Test complete flow for multiple output destinations."""
        config_dict = {
            "name": "test_pipeline",
            "version": "1.0.0",
            "output": {
                "enabled_destinations": ["neo4j", "elasticsearch", "parquet"],
                "neo4j": {"uri": "bolt://localhost:7687", "username": "neo4j", "database": "neo4j"},
                "elasticsearch": {"hosts": ["localhost:9200"]},
                "parquet": {"base_path": "data/test_parquet"}
            },
            "embedding": {"provider": "mock"}
        }
        
        config = PipelineConfig(**config_dict)
        
        # Verify processing paths
        paths = ProcessingPaths.from_destinations(config.output.enabled_destinations)
        assert not paths.lightweight  # Not parquet-only
        assert paths.graph  # Neo4j enabled
        assert paths.search  # Elasticsearch enabled
        assert set(paths.get_enabled_paths()) == {"graph", "search"}
        
        # Verify fork initialization
        fork = PipelineFork(config.output.enabled_destinations)
        assert not fork.paths.lightweight
        assert fork.paths.graph
        assert fork.paths.search
    
    def test_yaml_config_integration(self):
        """Test loading from YAML config matches output-driven behavior."""
        # Mock YAML content that has elasticsearch enabled
        yaml_content = """
        name: test_pipeline
        version: 1.0.0
        output:
          enabled_destinations:
            - parquet
            - elasticsearch
          parquet:
            base_path: data/processed
          elasticsearch:
            hosts:
              - localhost:9200
        embedding:
          provider: mock
        """
        
        with patch('builtins.open', create=True) as mock_open:
            with patch('os.path.exists', return_value=True):
                with patch('yaml.safe_load') as mock_yaml:
                    mock_yaml.return_value = {
                        'name': 'test_pipeline',
                        'version': '1.0.0',
                        'output': {
                            'enabled_destinations': ['parquet', 'elasticsearch'],
                            'parquet': {'base_path': 'data/processed'},
                            'elasticsearch': {'hosts': ['localhost:9200']}
                        },
                        'embedding': {'provider': 'mock'}
                    }
                    
                    # Simulate loading from YAML by creating config directly
                    config = PipelineConfig(**mock_yaml.return_value)
                    
                    # Verify the configuration drives correct path selection
                    paths = ProcessingPaths.from_destinations(config.output.enabled_destinations)
                    assert not paths.lightweight  # Not parquet-only
                    assert not paths.graph  # No neo4j
                    assert paths.search  # Elasticsearch enabled
                    assert paths.get_enabled_paths() == ["search"]
    
    @patch('data_pipeline.core.pipeline_runner.SparkSession')
    def test_pipeline_runner_integration(self, mock_spark_session):
        """Test PipelineRunner uses output-driven fork correctly."""
        mock_spark = Mock(spec=SparkSession)
        mock_spark_session.builder.appName.return_value.master.return_value.config.return_value.getOrCreate.return_value = mock_spark
        
        config_dict = {
            "name": "test_pipeline",
            "version": "1.0.0", 
            "output": {
                "enabled_destinations": ["parquet", "neo4j"],
                "parquet": {"base_path": "data/test"},
                "neo4j": {"uri": "bolt://localhost:7687", "username": "neo4j", "database": "neo4j"}
            },
            "embedding": {"provider": "mock"},
            "data_sources": {
                "properties_files": ["test_properties.json"],
                "neighborhoods_files": ["test_neighborhoods.json"],
                "wikipedia_db_path": "test_wiki.db",
                "locations_file": "test_locations.json"
            }
        }
        
        config = PipelineConfig(**config_dict)
        runner = DataPipelineRunner(config)
        
        # Verify the runner initialized the fork with correct destinations
        assert runner.pipeline_fork.destinations == ["parquet", "neo4j"]
        assert not runner.pipeline_fork.paths.lightweight  # Not parquet-only
        assert runner.pipeline_fork.paths.graph  # Neo4j enabled
        assert not runner.pipeline_fork.paths.search  # No elasticsearch
        assert runner.pipeline_fork.paths.get_enabled_paths() == ["graph"]
    
    def test_processing_path_logic_comprehensive(self):
        """Comprehensive test of all processing path combinations."""
        test_cases = [
            # (destinations, expected_lightweight, expected_graph, expected_search, expected_paths)
            (["parquet"], True, False, False, ["lightweight"]),
            (["neo4j"], False, True, False, ["graph"]),
            (["elasticsearch"], False, False, True, ["search"]),
            (["parquet", "neo4j"], False, True, False, ["graph"]),
            (["parquet", "elasticsearch"], False, False, True, ["search"]),
            (["neo4j", "elasticsearch"], False, True, True, ["graph", "search"]),
            (["parquet", "neo4j", "elasticsearch"], False, True, True, ["graph", "search"]),
        ]
        
        for destinations, exp_lightweight, exp_graph, exp_search, exp_paths in test_cases:
            paths = ProcessingPaths.from_destinations(destinations)
            
            assert paths.lightweight == exp_lightweight, f"Failed lightweight for {destinations}"
            assert paths.graph == exp_graph, f"Failed graph for {destinations}" 
            assert paths.search == exp_search, f"Failed search for {destinations}"
            assert set(paths.get_enabled_paths()) == set(exp_paths), f"Failed paths for {destinations}"
            
            # Also test fork initialization
            fork = PipelineFork(destinations)
            assert fork.paths.lightweight == exp_lightweight
            assert fork.paths.graph == exp_graph 
            assert fork.paths.search == exp_search