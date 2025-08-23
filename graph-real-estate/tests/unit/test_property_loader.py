"""Unit tests for PropertyLoader with mocked dependencies"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.loaders.property_loader import PropertyLoader
from src.core.query_executor import QueryExecutor
from src.core.config import PropertyConfig, LoaderConfig
from src.data_sources import PropertyFileDataSource
from src.models.property import PropertyLoadResult


class TestPropertyLoader:
    """Test PropertyLoader with mocked dependencies"""
    
    @pytest.fixture
    def mock_query_executor(self):
        """Create mock query executor"""
        mock = Mock(spec=QueryExecutor)
        mock.batch_execute.return_value = 10
        mock.execute_write.return_value = [{'count': 5}]
        mock.execute_read.return_value = []
        mock.create_constraint.return_value = True
        mock.create_index.return_value = True
        mock.count_nodes.return_value = 10
        return mock
    
    @pytest.fixture
    def mock_config(self):
        """Create mock property config"""
        config = Mock(spec=PropertyConfig)
        config.data_path = Mock()
        return config
    
    @pytest.fixture
    def mock_loader_config(self):
        """Create mock loader config"""
        config = Mock(spec=LoaderConfig)
        config.default_batch_size = 100
        config.property_batch_size = 50
        config.feature_batch_size = 200
        return config
    
    @pytest.fixture
    def mock_data_source(self):
        """Create mock property data source"""
        mock = Mock(spec=PropertyFileDataSource)
        mock.load_properties.return_value = [
            {
                'listing_id': 'prop1',
                'neighborhood_id': 'n1',
                'listing_price': 500000,
                'features': ['pool', 'garage'],
                'address': {
                    'street': '123 Main St',
                    'city': 'San Francisco',
                    'state': 'CA',
                    'zip': '94102'
                },
                'property_details': {
                    'bedrooms': 3,
                    'bathrooms': 2,
                    'square_feet': 1500,
                    'property_type': 'single-family'
                },
                'coordinates': {
                    'latitude': 37.7749,
                    'longitude': -122.4194
                }
            }
        ]
        return mock
    
    @pytest.fixture
    def property_loader(self, mock_query_executor, mock_config, mock_loader_config, mock_data_source):
        """Create PropertyLoader with mocked dependencies"""
        return PropertyLoader(
            query_executor=mock_query_executor,
            config=mock_config,
            loader_config=mock_loader_config,
            data_source=mock_data_source
        )
    
    def test_initialization(self, property_loader, mock_query_executor):
        """Test PropertyLoader is initialized with injected dependencies"""
        assert property_loader.query_executor == mock_query_executor
        assert property_loader.config is not None
        assert property_loader.loader_config is not None
        assert property_loader.data_source is not None
        assert len(property_loader.unique_features) == 0
        assert len(property_loader.unique_property_types) == 0
    
    def test_load_properties_from_data_source(self, property_loader, mock_data_source):
        """Test loading properties from data source"""
        properties = property_loader._load_and_validate_properties()
        
        assert len(properties) == 1
        assert properties[0].listing_id == 'prop1'
        assert properties[0].neighborhood_id == 'n1'
        assert properties[0].listing_price == 500000
        assert len(property_loader.unique_features) == 2  # pool, garage
        assert 'single-family' in property_loader.unique_property_types
        
        mock_data_source.load_properties.assert_called_once()
    
    def test_create_constraints_and_indexes(self, property_loader, mock_query_executor):
        """Test constraint and index creation"""
        property_loader._create_constraints_and_indexes()
        
        # Should create 4 constraints
        assert mock_query_executor.create_constraint.call_count == 4
        
        # Should create multiple indexes
        assert mock_query_executor.create_index.call_count >= 6
    
    def test_create_price_range_nodes(self, property_loader, mock_query_executor):
        """Test price range node creation"""
        property_loader._create_price_range_nodes()
        
        # Should batch execute with price ranges
        mock_query_executor.batch_execute.assert_called_once()
        call_args = mock_query_executor.batch_execute.call_args
        assert len(call_args[0][1]) == 6  # 6 standard price ranges
        assert property_loader.load_result.price_range_nodes == 10
    
    def test_create_feature_nodes(self, property_loader, mock_query_executor):
        """Test feature node creation"""
        property_loader.unique_features = {'pool', 'garage', 'fireplace'}
        property_loader._create_feature_nodes()
        
        mock_query_executor.batch_execute.assert_called_once()
        call_args = mock_query_executor.batch_execute.call_args
        batch_data = call_args[0][1]
        
        assert len(batch_data) == 3
        assert any(item['feature_id'] == 'pool' for item in batch_data)
        assert any(item['category'] == 'Outdoor' for item in batch_data)  # pool -> Outdoor
        assert any(item['category'] == 'Parking' for item in batch_data)  # garage -> Parking
    
    def test_categorize_feature(self, property_loader):
        """Test feature categorization"""
        assert property_loader._categorize_feature('swimming pool') == 'Outdoor'
        assert property_loader._categorize_feature('garage') == 'Parking'
        assert property_loader._categorize_feature('fireplace') == 'Interior'
        assert property_loader._categorize_feature('smart home') == 'Technology'
        assert property_loader._categorize_feature('unknown') == 'Other'
    
    def test_create_property_nodes(self, property_loader, mock_query_executor, mock_data_source):
        """Test property node creation"""
        properties = property_loader._load_and_validate_properties()
        nodes_created = property_loader._create_property_nodes(properties)
        
        assert nodes_created == 10  # mock returns 10
        mock_query_executor.batch_execute.assert_called_once()
        
        call_args = mock_query_executor.batch_execute.call_args
        batch_data = call_args[0][1]
        
        assert len(batch_data) == 1
        assert batch_data[0]['listing_id'] == 'prop1'
        assert batch_data[0]['city'] == 'San Francisco'
        assert batch_data[0]['bedrooms'] == 3
    
    def test_create_geographic_relationships(self, property_loader, mock_query_executor):
        """Test geographic relationship creation"""
        mock_query_executor.execute_write.side_effect = [
            [{'count': 5}],  # neighborhoods
            [{'count': 3}],  # cities
        ]
        
        property_loader._create_geographic_relationships()
        
        assert property_loader.load_result.neighborhood_relationships == 5
        assert property_loader.load_result.city_relationships == 3
        assert mock_query_executor.execute_write.call_count == 2
    
    def test_full_load_process(self, property_loader, mock_query_executor, mock_data_source):
        """Test complete load process"""
        result = property_loader.load()
        
        assert isinstance(result, PropertyLoadResult)
        assert result.success == True
        assert result.properties_loaded == 1
        assert result.property_nodes == 10
        assert result.duration_seconds > 0
        
        # Verify all steps were called
        mock_data_source.load_properties.assert_called()
        assert mock_query_executor.create_constraint.called
        assert mock_query_executor.create_index.called
        assert mock_query_executor.batch_execute.called
    
    def test_error_handling(self, property_loader, mock_data_source):
        """Test error handling during load"""
        mock_data_source.load_properties.side_effect = Exception("Data source error")
        
        result = property_loader.load()
        
        assert result.success == False
        assert len(result.errors) > 0
        assert "Data source error" in result.errors[0]