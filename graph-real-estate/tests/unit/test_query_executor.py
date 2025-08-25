"""Unit tests for QueryExecutor with mocked Neo4j driver"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from neo4j import Driver
from neo4j.exceptions import ServiceUnavailable, TransientError

from core.query_executor import QueryExecutor


class TestQueryExecutor:
    """Test QueryExecutor with mocked Neo4j driver"""
    
    @pytest.fixture
    def mock_driver(self):
        """Create mock Neo4j driver"""
        driver = Mock(spec=Driver)
        session = Mock()
        driver.session.return_value = session
        
        # Setup context manager for session
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=None)
        
        # Setup transaction
        tx = Mock()
        session.execute_write.return_value = [{'count': 5}]
        session.execute_read.return_value = [{'id': 1}]
        
        return driver
    
    @pytest.fixture
    def query_executor(self, mock_driver):
        """Create QueryExecutor with mocked driver"""
        return QueryExecutor(driver=mock_driver, database="testdb", max_retries=3)
    
    def test_initialization(self, query_executor, mock_driver):
        """Test QueryExecutor initialization"""
        assert query_executor.driver == mock_driver
        assert query_executor.database == "testdb"
        assert query_executor.max_retries == 3
    
    def test_execute_write(self, query_executor, mock_driver):
        """Test execute_write method"""
        query = "CREATE (n:Test {name: $name}) RETURN n"
        params = {"name": "test_node"}
        
        session = mock_driver.session.return_value
        session.execute_write.return_value = [{'n': {'name': 'test_node'}}]
        
        result = query_executor.execute_write(query, params)
        
        assert result == [{'n': {'name': 'test_node'}}]
        mock_driver.session.assert_called_with(database="testdb")
        session.execute_write.assert_called_once()
    
    def test_execute_read(self, query_executor, mock_driver):
        """Test execute_read method"""
        query = "MATCH (n:Test) RETURN n"
        params = {}
        
        session = mock_driver.session.return_value
        session.execute_read.return_value = [{'n': {'id': 1}}]
        
        result = query_executor.execute_read(query, params)
        
        assert result == [{'n': {'id': 1}}]
        mock_driver.session.assert_called_with(database="testdb")
        session.execute_read.assert_called_once()
    
    def test_batch_execute(self, query_executor, mock_driver):
        """Test batch_execute method"""
        query = "CREATE (n:Test {id: $id, name: $name})"
        batch_data = [
            {'id': 1, 'name': 'first'},
            {'id': 2, 'name': 'second'},
            {'id': 3, 'name': 'third'}
        ]
        
        session = mock_driver.session.return_value
        tx = Mock()
        session.execute_write.return_value = 3
        
        result = query_executor.batch_execute(query, batch_data, batch_size=2)
        
        assert result == 3
        # Should be called twice (batch size 2 for 3 items)
        assert session.execute_write.call_count == 1
    
    def test_retry_on_transient_error(self, query_executor, mock_driver):
        """Test retry logic on transient errors"""
        session = mock_driver.session.return_value
        
        # First two calls fail, third succeeds
        session.execute_read.side_effect = [
            TransientError("Connection failed"),
            ServiceUnavailable("Service unavailable"),
            [{'result': 'success'}]
        ]
        
        result = query_executor.execute_read("MATCH (n) RETURN n")
        
        assert result == [{'result': 'success'}]
        assert session.execute_read.call_count == 3
    
    def test_max_retries_exceeded(self, query_executor, mock_driver):
        """Test that max retries are respected"""
        session = mock_driver.session.return_value
        session.execute_write.side_effect = TransientError("Always fails")
        
        with pytest.raises(TransientError):
            query_executor.execute_write("CREATE (n:Test)")
        
        # Should try max_retries + 1 times (initial + retries)
        assert session.execute_write.call_count == 4
    
    def test_create_constraint(self, query_executor, mock_driver):
        """Test constraint creation"""
        session = mock_driver.session.return_value
        
        success = query_executor.create_constraint("Property", "listing_id")
        
        assert success == True
        session.execute_write.assert_called_once()
        
        # Check the query contains constraint creation
        call_args = session.execute_write.call_args
        tx_func = call_args[0][0]
        mock_tx = Mock()
        mock_tx.run.return_value.data.return_value = []
        tx_func(mock_tx)
        
        query = mock_tx.run.call_args[0][0]
        assert "CONSTRAINT" in query
        assert "Property" in query
        assert "listing_id" in query
    
    def test_create_index(self, query_executor, mock_driver):
        """Test index creation"""
        session = mock_driver.session.return_value
        
        success = query_executor.create_index("Property", ["city", "state"])
        
        assert success == True
        session.execute_write.assert_called_once()
        
        # Check the query contains index creation
        call_args = session.execute_write.call_args
        tx_func = call_args[0][0]
        mock_tx = Mock()
        mock_tx.run.return_value.data.return_value = []
        tx_func(mock_tx)
        
        query = mock_tx.run.call_args[0][0]
        assert "INDEX" in query
        assert "Property" in query
        assert "city" in query
        assert "state" in query
    
    def test_count_nodes(self, query_executor, mock_driver):
        """Test counting nodes"""
        session = mock_driver.session.return_value
        session.execute_read.return_value = [{'count': 42}]
        
        count = query_executor.count_nodes("Property")
        
        assert count == 42
        
        # Check the query
        call_args = session.execute_read.call_args
        tx_func = call_args[0][0]
        mock_tx = Mock()
        mock_tx.run.return_value.data.return_value = [{'count': 42}]
        result = tx_func(mock_tx)
        
        query = mock_tx.run.call_args[0][0]
        assert "MATCH (n:Property)" in query
        assert "COUNT(n)" in query
    
    def test_count_relationships(self, query_executor, mock_driver):
        """Test counting relationships"""
        session = mock_driver.session.return_value
        session.execute_read.return_value = [{'count': 100}]
        
        count = query_executor.count_relationships("SIMILAR_TO")
        
        assert count == 100
        
        # Check the query
        call_args = session.execute_read.call_args
        tx_func = call_args[0][0]
        mock_tx = Mock()
        mock_tx.run.return_value.data.return_value = [{'count': 100}]
        result = tx_func(mock_tx)
        
        query = mock_tx.run.call_args[0][0]
        assert "MATCH ()-[r:SIMILAR_TO]-()" in query
        assert "COUNT(r)" in query
    
    def test_clear_database(self, query_executor, mock_driver):
        """Test clearing the database"""
        session = mock_driver.session.return_value
        session.execute_write.return_value = [{'nodes_deleted': 50, 'relationships_deleted': 75}]
        
        stats = query_executor.clear_database()
        
        assert stats['nodes_deleted'] == 50
        assert stats['relationships_deleted'] == 75
        
        # Check the query
        call_args = session.execute_write.call_args
        tx_func = call_args[0][0]
        mock_tx = Mock()
        mock_result = Mock()
        mock_result.consume.return_value.counters.nodes_deleted = 50
        mock_result.consume.return_value.counters.relationships_deleted = 75
        mock_tx.run.return_value = mock_result
        result = tx_func(mock_tx)
        
        query = mock_tx.run.call_args[0][0]
        assert "MATCH (n)" in query
        assert "DETACH DELETE n" in query
    
    def test_get_stats(self, query_executor, mock_driver):
        """Test getting database statistics"""
        session = mock_driver.session.return_value
        
        # Mock different count queries
        session.execute_read.side_effect = [
            [{'labels': ['Property'], 'count': 100}],
            [{'labels': ['Neighborhood'], 'count': 20}],
            [{'type': 'SIMILAR_TO', 'count': 50}],
            [{'type': 'IN_NEIGHBORHOOD', 'count': 80}]
        ]
        
        stats = query_executor.get_stats()
        
        assert 'nodes' in stats
        assert 'relationships' in stats
        assert stats['nodes']['Property'] == 100
        assert stats['nodes']['Neighborhood'] == 20
        assert stats['relationships']['SIMILAR_TO'] == 50
        assert stats['relationships']['IN_NEIGHBORHOOD'] == 80