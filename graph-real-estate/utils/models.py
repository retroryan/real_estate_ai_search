"""Pydantic models for graph-real-estate module"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator


class DemoConfig(BaseModel):
    """Configuration for demo execution"""
    
    demo_number: int = Field(..., ge=1, le=7, description="Demo number to run (1-7)")
    verbose: bool = Field(default=False, description="Enable verbose output")
    
    @validator('demo_number')
    def validate_demo_number(cls, v):
        """Validate demo number is within valid range"""
        if v not in range(1, 8):
            raise ValueError(f"Demo {v} does not exist. Valid demos are 1-7")
        return v
    
    class Config:
        """Pydantic configuration"""
        validate_assignment = True


class DatabaseConfig(BaseModel):
    """Configuration for database connection"""
    
    uri: str = Field(default="bolt://localhost:7687", description="Neo4j URI")
    username: str = Field(default="neo4j", description="Neo4j username")
    password: str = Field(default="password", description="Neo4j password")
    database: Optional[str] = Field(default="neo4j", description="Database name")
    
    class Config:
        """Pydantic configuration"""
        validate_assignment = True


class QueryResult(BaseModel):
    """Model for query results"""
    
    query_name: str = Field(..., description="Name of the query")
    description: str = Field(..., description="Query description")
    result_count: int = Field(..., ge=0, description="Number of results")
    results: List[dict] = Field(default_factory=list, description="Query results")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")
    
    class Config:
        """Pydantic configuration"""
        validate_assignment = True