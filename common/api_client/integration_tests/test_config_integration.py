"""Integration tests for configuration loading and environment overrides."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from ..config import APIClientConfig
from ..config_loader import ConfigLoader
from ..property_client import PropertyAPIClient
from ..wikipedia_client import WikipediaAPIClient
from ..exceptions import ValidationError


class TestConfigIntegration:
    """Integration tests for configuration management."""
    
    def test_yaml_config_loading_with_real_clients(self, integration_logger):
        """Test loading YAML configuration and creating real clients."""
        # Create a temporary YAML config file
        config_data = {
            "property_api": {
                "base_url": "http://localhost:8000/api/v1",
                "timeout": 45,
                "default_headers": {"User-Agent": "PropertyClient/1.0"}
            },
            "wikipedia_api": {
                "base_url": "http://localhost:8000/api/v1/wikipedia", 
                "timeout": 60
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            # Load property API config
            property_config = ConfigLoader.load_from_yaml(temp_path, "property_api")
            property_client = PropertyAPIClient(property_config, integration_logger)
            
            assert str(property_client.config.base_url).rstrip('/') == "http://localhost:8000/api/v1"
            assert property_client.config.timeout == 45
            assert property_client.config.default_headers == {"User-Agent": "PropertyClient/1.0"}
            
            # Load Wikipedia API config
            wikipedia_config = ConfigLoader.load_from_yaml(temp_path, "wikipedia_api")
            wikipedia_client = WikipediaAPIClient(wikipedia_config, integration_logger)
            
            assert str(wikipedia_client.config.base_url).rstrip('/') == "http://localhost:8000/api/v1/wikipedia"
            assert wikipedia_client.config.timeout == 60
            assert wikipedia_client.config.default_headers is None
            
        finally:
            temp_path.unlink()
    
    def test_environment_variable_overrides(self, integration_logger):
        """Test configuration override via environment variables."""
        # Create base YAML config
        config_data = {
            "test_api": {
                "base_url": "http://original.example.com",
                "timeout": 30
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            # Test with environment overrides
            with patch.dict(os.environ, {
                "TEST_API_BASE_URL": "http://overridden.example.com",
                "TEST_API_TIMEOUT": "60"
            }):
                config = ConfigLoader.load_from_yaml(
                    temp_path, 
                    "test_api", 
                    env_prefix="TEST_API"
                )
                
                assert str(config.base_url) == "http://overridden.example.com/"
                assert config.timeout == 60
            
            # Test without environment overrides
            config = ConfigLoader.load_from_yaml(temp_path, "test_api")
            assert str(config.base_url) == "http://original.example.com/"
            assert config.timeout == 30
            
        finally:
            temp_path.unlink()
    
    def test_config_validation_with_invalid_data(self):
        """Test configuration validation with various invalid inputs."""
        # Test missing required fields
        with pytest.raises(ValidationError):
            ConfigLoader.load_from_dict({"timeout": 30})  # Missing base_url
        
        # Test invalid base URL format
        with pytest.raises(ValidationError):
            ConfigLoader.load_from_dict({
                "base_url": "not-a-valid-url",
                "timeout": 30
            })
        
        # Test invalid timeout
        with pytest.raises(ValidationError):
            ConfigLoader.load_from_dict({
                "base_url": "http://example.com",
                "timeout": -1
            })
        
        # Test extra forbidden fields
        with pytest.raises(ValidationError):
            ConfigLoader.load_from_dict({
                "base_url": "http://example.com",
                "timeout": 30,
                "invalid_field": "not allowed"
            })
    
    def test_config_with_default_headers(self, integration_logger):
        """Test configuration with custom default headers."""
        config_data = {
            "base_url": "http://test.example.com",
            "timeout": 30,
            "default_headers": {
                "User-Agent": "TestClient/1.0",
                "Accept": "application/json",
                "X-Custom-Header": "test-value"
            }
        }
        
        config = ConfigLoader.load_from_dict(config_data)
        client = PropertyAPIClient(config, integration_logger)
        
        assert client.config.default_headers["User-Agent"] == "TestClient/1.0"
        assert client.config.default_headers["Accept"] == "application/json"
        assert client.config.default_headers["X-Custom-Header"] == "test-value"
    
    def test_multiple_client_configs_from_single_file(self, integration_logger):
        """Test loading multiple client configurations from single YAML file."""
        config_data = {
            "property_api": {
                "base_url": "http://localhost:8000/api/v1",
                "timeout": 30
            },
            "wikipedia_api": {
                "base_url": "http://localhost:8000/api/v1/wikipedia",
                "timeout": 45
            },
            "another_service": {
                "base_url": "http://another.service.com",
                "timeout": 60,
                "default_headers": {"Service": "Another"}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            # Load all configurations
            property_config = ConfigLoader.load_from_yaml(temp_path, "property_api")
            wikipedia_config = ConfigLoader.load_from_yaml(temp_path, "wikipedia_api")
            another_config = ConfigLoader.load_from_yaml(temp_path, "another_service")
            
            # Create clients
            property_client = PropertyAPIClient(property_config, integration_logger)
            wikipedia_client = WikipediaAPIClient(wikipedia_config, integration_logger)
            
            # Verify each has correct configuration
            assert str(property_client.config.base_url).rstrip('/') == "http://localhost:8000/api/v1"
            assert property_client.config.timeout == 30
            
            assert str(wikipedia_client.config.base_url).rstrip('/') == "http://localhost:8000/api/v1/wikipedia"
            assert wikipedia_client.config.timeout == 45
            
            assert str(another_config.base_url) == "http://another.service.com/"
            assert another_config.timeout == 60
            assert another_config.default_headers == {"Service": "Another"}
            
        finally:
            temp_path.unlink()
    
    def test_config_url_normalization(self):
        """Test that base URLs are properly normalized."""
        # Test URL without trailing slash
        config = ConfigLoader.load_from_dict({
            "base_url": "http://example.com/api/v1",
            "timeout": 30
        })
        assert str(config.base_url) == "http://example.com/api/v1"
        
        # Test URL with trailing slash (slash should be preserved)
        config = ConfigLoader.load_from_dict({
            "base_url": "http://example.com/api/v1/",
            "timeout": 30
        })
        assert str(config.base_url) == "http://example.com/api/v1/"
    
    def test_config_with_missing_yaml_file(self):
        """Test error handling when YAML file doesn't exist."""
        non_existent_path = Path("/tmp/does_not_exist.yaml")
        
        with pytest.raises(FileNotFoundError):
            ConfigLoader.load_from_yaml(non_existent_path, "test_api")
    
    def test_config_with_malformed_yaml(self):
        """Test error handling with malformed YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: {\n")  # Malformed YAML
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValidationError, match="Invalid YAML"):
                ConfigLoader.load_from_yaml(temp_path, "test_api")
        finally:
            temp_path.unlink()
    
    def test_config_with_empty_yaml(self):
        """Test handling of empty YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")  # Empty file
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValidationError, match="No configuration found"):
                ConfigLoader.load_from_yaml(temp_path, "test_api")
        finally:
            temp_path.unlink()
    
    @patch.dict(os.environ, {"TEST_TIMEOUT": "invalid_number"})
    def test_invalid_environment_override(self):
        """Test handling of invalid environment variable overrides."""
        config_data = {
            "test_api": {
                "base_url": "http://example.com",
                "timeout": 30
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            # Should use original timeout since env override is invalid
            config = ConfigLoader.load_from_yaml(temp_path, "test_api", env_prefix="TEST")
            assert config.timeout == 30  # Original value, not the invalid env override
            
        finally:
            temp_path.unlink()