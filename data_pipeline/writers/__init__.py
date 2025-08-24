"""
Data pipeline writers package.

This package provides modular, entity-specific writers organized by destination:
- neo4j/: Neo4j graph database writers
- elasticsearch/: Elasticsearch search engine writers  
- chromadb/: ChromaDB vector database writers

Each writer type follows standardized naming: {destination}_{entity}
"""

# Import orchestrators for easy access
from .neo4j import Neo4jOrchestrator
from .elasticsearch import ElasticsearchOrchestrator
from .chromadb import ChromadbOrchestrator

# Import entity-specific writers
from .neo4j import PropertyNeo4jWriter, NeighborhoodNeo4jWriter, WikipediaNeo4jWriter
from .elasticsearch import PropertyElasticsearchWriter, NeighborhoodElasticsearchWriter, WikipediaElasticsearchWriter
from .chromadb import PropertyChromadbWriter, NeighborhoodChromadbWriter, WikipediaChromadbWriter

# Import base classes
from .base import DataWriter, WriterConfig

# Import remaining writers
from .orchestrator import WriterOrchestrator
from .parquet_writer import ParquetWriter

__all__ = [
    # Orchestrators
    "Neo4jOrchestrator",
    "ElasticsearchOrchestrator", 
    "ChromadbOrchestrator",
    "WriterOrchestrator",
    
    # Neo4j writers
    "PropertyNeo4jWriter",
    "NeighborhoodNeo4jWriter", 
    "WikipediaNeo4jWriter",
    
    # Elasticsearch writers
    "PropertyElasticsearchWriter",
    "NeighborhoodElasticsearchWriter",
    "WikipediaElasticsearchWriter",
    
    # ChromaDB writers
    "PropertyChromadbWriter",
    "NeighborhoodChromadbWriter", 
    "WikipediaChromadbWriter",
    
    # Base and utility writers
    "DataWriter",
    "WriterConfig", 
    "ParquetWriter"
]