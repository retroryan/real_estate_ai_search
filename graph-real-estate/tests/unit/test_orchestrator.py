"""Unit tests for GraphOrchestrator with mocked dependencies"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from orchestrator import GraphOrchestrator
from core.dependencies import LoaderDependencies
from loaders.validator import ValidationResult
from models.geographic import GeographicLoadResult
from models.wikipedia import WikipediaLoadResult
from models.neighborhood import NeighborhoodLoadResult
from models.property import PropertyLoadResult
from models.similarity import SimilarityLoadResult


class TestGraphOrchestrator:
    """Test GraphOrchestrator with mocked dependencies"""
    
    @pytest.fixture
    def mock_validator(self):
        """Create mock validator"""
        mock = Mock()
        result = ValidationResult()
        result.is_valid = True
        result.add_passed("Neo4j connectivity")
        mock.validate_all.return_value = result
        return mock
    
    @pytest.fixture
    def mock_geographic_loader(self):
        """Create mock geographic loader"""
        mock = Mock()
        result = GeographicLoadResult()
        result.success = True
        result.total_states = 2
        result.total_counties = 5
        result.total_cities = 10
        mock.load.return_value = result
        return mock
    
    @pytest.fixture
    def mock_wikipedia_loader(self):
        """Create mock Wikipedia loader"""
        mock = Mock()
        result = WikipediaLoadResult()
        result.success = True
        result.articles_loaded = 50
        result.topics_extracted = 100
        mock.load.return_value = result
        return mock
    
    @pytest.fixture
    def mock_neighborhood_loader(self):
        """Create mock neighborhood loader"""
        mock = Mock()
        result = NeighborhoodLoadResult()
        result.success = True
        result.neighborhoods_loaded = 20
        result.wikipedia_correlations = 15
        result.avg_knowledge_score = 0.75
        mock.load.return_value = result
        return mock
    
    @pytest.fixture
    def mock_property_loader(self):
        """Create mock property loader"""
        mock = Mock()
        result = PropertyLoadResult()
        result.success = True
        result.properties_loaded = 100
        result.unique_features = 50
        result.neighborhood_relationships = 80
        mock.load.return_value = result
        return mock
    
    @pytest.fixture
    def mock_similarity_loader(self):
        """Create mock similarity loader"""
        mock = Mock()
        result = SimilarityLoadResult()
        result.success = True
        result.property_similarities_created = 200
        result.neighborhood_connections_created = 30
        result.topic_clusters_created = 25
        mock.load.return_value = result
        return mock
    
    @pytest.fixture
    def mock_loaders(self, mock_validator, mock_geographic_loader, mock_wikipedia_loader,
                    mock_neighborhood_loader, mock_property_loader, mock_similarity_loader):
        """Create mock LoaderDependencies"""
        loaders = Mock(spec=LoaderDependencies)
        loaders.validator = mock_validator
        loaders.geographic_loader = mock_geographic_loader
        loaders.wikipedia_loader = mock_wikipedia_loader
        loaders.neighborhood_loader = mock_neighborhood_loader
        loaders.property_loader = mock_property_loader
        loaders.similarity_loader = mock_similarity_loader
        return loaders
    
    @pytest.fixture
    def orchestrator(self, mock_loaders):
        """Create GraphOrchestrator with mocked dependencies"""
        return GraphOrchestrator(mock_loaders)
    
    def test_initialization(self, orchestrator, mock_loaders):
        """Test orchestrator is initialized with injected dependencies"""
        assert orchestrator.loaders == mock_loaders
        assert orchestrator.validator == mock_loaders.validator
        assert orchestrator.geographic_loader == mock_loaders.geographic_loader
        assert orchestrator.wikipedia_loader == mock_loaders.wikipedia_loader
        assert orchestrator.neighborhood_loader == mock_loaders.neighborhood_loader
        assert orchestrator.property_loader == mock_loaders.property_loader
        assert orchestrator.similarity_loader == mock_loaders.similarity_loader
    
    def test_run_phase_1_validation_success(self, orchestrator, mock_validator):
        """Test Phase 1 validation when successful"""
        result = orchestrator.run_phase_1_validation()
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid == True
        assert len(result.checks_passed) == 1
        mock_validator.validate_all.assert_called_once()
    
    def test_run_phase_1_validation_failure(self, orchestrator, mock_validator):
        """Test Phase 1 validation when failed"""
        result = ValidationResult()
        result.add_error("Database connection failed")
        mock_validator.validate_all.return_value = result
        
        result = orchestrator.run_phase_1_validation()
        
        assert result.is_valid == False
        assert len(result.errors) == 1
        assert "Database connection failed" in result.errors[0]
    
    def test_run_phase_2_geographic(self, orchestrator, mock_geographic_loader):
        """Test Phase 2 geographic loading"""
        result = orchestrator.run_phase_2_geographic()
        
        assert isinstance(result, GeographicLoadResult)
        assert result.success == True
        assert result.total_states == 2
        assert result.total_counties == 5
        assert result.total_cities == 10
        mock_geographic_loader.load.assert_called_once()
    
    def test_run_phase_3_wikipedia(self, orchestrator, mock_wikipedia_loader):
        """Test Phase 3 Wikipedia loading"""
        result = orchestrator.run_phase_3_wikipedia()
        
        assert isinstance(result, WikipediaLoadResult)
        assert result.success == True
        assert result.articles_loaded == 50
        assert result.topics_extracted == 100
        mock_wikipedia_loader.load.assert_called_once()
    
    def test_run_phase_4_neighborhoods(self, orchestrator, mock_neighborhood_loader):
        """Test Phase 4 neighborhood loading"""
        result = orchestrator.run_phase_4_neighborhoods()
        
        assert isinstance(result, NeighborhoodLoadResult)
        assert result.success == True
        assert result.neighborhoods_loaded == 20
        assert result.wikipedia_correlations == 15
        assert result.avg_knowledge_score == 0.75
        mock_neighborhood_loader.load.assert_called_once()
    
    def test_run_phase_5_properties(self, orchestrator, mock_property_loader):
        """Test Phase 5 property loading"""
        result = orchestrator.run_phase_5_properties()
        
        assert isinstance(result, PropertyLoadResult)
        assert result.success == True
        assert result.properties_loaded == 100
        assert result.unique_features == 50
        assert result.neighborhood_relationships == 80
        mock_property_loader.load.assert_called_once()
    
    def test_run_phase_6_similarity(self, orchestrator, mock_similarity_loader):
        """Test Phase 6 similarity calculation"""
        result = orchestrator.run_phase_6_similarity()
        
        assert isinstance(result, SimilarityLoadResult)
        assert result.success == True
        assert result.property_similarities_created == 200
        assert result.neighborhood_connections_created == 30
        assert result.topic_clusters_created == 25
        mock_similarity_loader.load.assert_called_once()
    
    def test_run_all_phases_success(self, orchestrator, mock_loaders):
        """Test running all phases successfully"""
        success = orchestrator.run_all_phases()
        
        assert success == True
        
        # Verify all phases were called
        mock_loaders.validator.validate_all.assert_called_once()
        mock_loaders.geographic_loader.load.assert_called_once()
        mock_loaders.wikipedia_loader.load.assert_called_once()
        mock_loaders.neighborhood_loader.load.assert_called_once()
        mock_loaders.property_loader.load.assert_called_once()
        mock_loaders.similarity_loader.load.assert_called_once()
    
    def test_run_all_phases_stops_on_failure(self, orchestrator, mock_loaders):
        """Test that all phases stops when one fails"""
        # Make phase 3 fail
        result = WikipediaLoadResult()
        result.success = False
        result.add_error("Wikipedia data not found")
        mock_loaders.wikipedia_loader.load.return_value = result
        
        success = orchestrator.run_all_phases()
        
        assert success == False
        
        # Phases 1 and 2 should be called
        mock_loaders.validator.validate_all.assert_called_once()
        mock_loaders.geographic_loader.load.assert_called_once()
        mock_loaders.wikipedia_loader.load.assert_called_once()
        
        # Phases 4, 5, and 6 should NOT be called
        mock_loaders.neighborhood_loader.load.assert_not_called()
        mock_loaders.property_loader.load.assert_not_called()
        mock_loaders.similarity_loader.load.assert_not_called()
    
    def test_run_all_phases_validation_failure(self, orchestrator, mock_loaders):
        """Test that all phases stops on validation failure"""
        # Make validation fail
        result = ValidationResult()
        result.add_error("No database connection")
        mock_loaders.validator.validate_all.return_value = result
        
        success = orchestrator.run_all_phases()
        
        assert success == False
        
        # Only validation should be called
        mock_loaders.validator.validate_all.assert_called_once()
        
        # No other phases should be called
        mock_loaders.geographic_loader.load.assert_not_called()
        mock_loaders.wikipedia_loader.load.assert_not_called()
        mock_loaders.neighborhood_loader.load.assert_not_called()
        mock_loaders.property_loader.load.assert_not_called()
        mock_loaders.similarity_loader.load.assert_not_called()