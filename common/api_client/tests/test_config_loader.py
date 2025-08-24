"""Tests for ConfigLoader."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from ..config import APIClientConfig
from ..config_loader import ConfigLoader
from ..exceptions import ValidationError


class TestConfigLoader:
    """Tests for ConfigLoader."""
    
    def test_load_from_yaml_success(self):
        """Test successful loading from YAML file."""
        config_data = {
            "test_api": {
                "base_url": "http://test.example.com",
                "timeout": 60,
                "default_headers": {"User-Agent": "test"}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            config = ConfigLoader.load_from_yaml(temp_path, "test_api")
            
            assert str(config.base_url) == "http://test.example.com/"
            assert config.timeout == 60
            assert config.default_headers == {"User-Agent": "test"}
        finally:
            temp_path.unlink()
    
    def test_load_from_yaml_file_not_found(self):
        """Test loading from non-existent YAML file."""
        with pytest.raises(FileNotFoundError):
            ConfigLoader.load_from_yaml(Path("non_existent.yaml"), "test_api")
    
    def test_load_from_yaml_invalid_yaml(self):
        """Test loading invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: {\n")  # Invalid YAML syntax
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValidationError, match="Invalid YAML"):
                ConfigLoader.load_from_yaml(temp_path, "test_api")
        finally:
            temp_path.unlink()
    
    def test_load_from_yaml_missing_client_config(self):
        """Test loading when client config is missing."""
        config_data = {"other_api": {"base_url": "http://other.com"}}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValidationError, match="No configuration found for client"):
                ConfigLoader.load_from_yaml(temp_path, "test_api")
        finally:
            temp_path.unlink()
    
    def test_load_from_yaml_invalid_config(self):
        """Test loading invalid configuration."""
        config_data = {
            "test_api": {
                "timeout": -1  # Invalid timeout
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValidationError, match="Invalid configuration"):
                ConfigLoader.load_from_yaml(temp_path, "test_api")
        finally:
            temp_path.unlink()
    
    @patch.dict(os.environ, {"TEST_API_BASE_URL": "http://env.example.com", "TEST_API_TIMEOUT": "45"})
    def test_load_from_yaml_with_env_overrides(self):
        """Test loading with environment variable overrides."""
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
            config = ConfigLoader.load_from_yaml(temp_path, "test_api", env_prefix="TEST_API")
            
            assert str(config.base_url) == "http://env.example.com/"
            assert config.timeout == 45
        finally:
            temp_path.unlink()
    
    @patch.dict(os.environ, {"TEST_API_TIMEOUT": "invalid"})
    def test_load_from_yaml_with_invalid_env_override(self):
        """Test loading with invalid environment variable override."""
        config_data = {
            "test_api": {
                "base_url": "http://test.example.com",
                "timeout": 30
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            config = ConfigLoader.load_from_yaml(temp_path, "test_api", env_prefix="TEST_API")
            
            # Should use original timeout since env value is invalid
            assert config.timeout == 30
        finally:
            temp_path.unlink()
    
    def test_load_from_dict_success(self):
        """Test successful loading from dictionary."""
        config_data = {
            "base_url": "http://test.example.com",
            "timeout": 45
        }
        
        config = ConfigLoader.load_from_dict(config_data)
        
        assert str(config.base_url) == "http://test.example.com/"
        assert config.timeout == 45
    
    def test_load_from_dict_invalid_config(self):
        """Test loading invalid configuration from dictionary."""
        config_data = {
            "timeout": -1  # Missing base_url, invalid timeout
        }
        
        with pytest.raises(ValidationError, match="Invalid configuration"):
            ConfigLoader.load_from_dict(config_data)
    
    def test_apply_env_overrides(self):
        """Test _apply_env_overrides method."""
        original_config = {
            "base_url": "http://original.com",
            "timeout": 30
        }
        
        with patch.dict(os.environ, {"TEST_BASE_URL": "http://overridden.com", "TEST_TIMEOUT": "60"}):
            result = ConfigLoader._apply_env_overrides(original_config, "TEST")
            
            assert result["base_url"] == "http://overridden.com"
            assert result["timeout"] == 60
            
            # Original config should be unchanged
            assert original_config["base_url"] == "http://original.com"
            assert original_config["timeout"] == 30