"""Interface definitions for dependency injection"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Protocol
from pathlib import Path
from neo4j import Driver


class IQueryExecutor(Protocol):
    """Interface for executing database queries"""
    
    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results"""
        ...
    
    def batch_execute(self, query: str, batch_data: List[Dict], batch_size: int = 1000) -> int:
        """Execute query in batches"""
        ...
    
    def execute_write(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a write transaction"""
        ...
    
    def execute_read(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a read transaction"""
        ...


class ITransactionManager(Protocol):
    """Interface for managing database transactions"""
    
    def execute_with_retry(self, query: str, params: Dict[str, Any], write: bool = False) -> List[Dict[str, Any]]:
        """Execute query with retry logic"""
        ...


class IDataSource(ABC):
    """Abstract interface for data sources"""
    
    @abstractmethod
    def exists(self) -> bool:
        """Check if data source exists"""
        pass
    
    @abstractmethod
    def load(self) -> Any:
        """Load data from source"""
        pass


class IPropertyDataSource(IDataSource):
    """Interface for property data sources"""
    
    @abstractmethod
    def load_properties(self, city: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load property data"""
        pass
    
    @abstractmethod
    def load_neighborhoods(self, city: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load neighborhood data"""
        pass


class IWikipediaDataSource(IDataSource):
    """Interface for Wikipedia data sources"""
    
    @abstractmethod
    def load_articles(self) -> List[Dict[str, Any]]:
        """Load Wikipedia articles"""
        pass
    
    @abstractmethod
    def load_summaries(self) -> List[Dict[str, Any]]:
        """Load Wikipedia summaries"""
        pass


class IGeographicDataSource(IDataSource):
    """Interface for geographic data sources"""
    
    @abstractmethod
    def load_states(self) -> List[Dict[str, Any]]:
        """Load state data"""
        pass
    
    @abstractmethod
    def load_counties(self) -> List[Dict[str, Any]]:
        """Load county data"""
        pass
    
    @abstractmethod
    def load_cities(self) -> List[Dict[str, Any]]:
        """Load city data"""
        pass


class IVectorManager(Protocol):
    """Interface for vector operations"""
    
    def create_embedding(self, text: str) -> List[float]:
        """Create embedding for text"""
        ...
    
    def vector_search(self, embedding: List[float], top_k: int = 10, min_score: float = 0.0) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        ...
    
    def store_embedding(self, node_id: str, embedding: List[float], metadata: Dict[str, Any]) -> bool:
        """Store embedding in database"""
        ...