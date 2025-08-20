"""Neo4j database client and utilities"""
import os
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Import from new connection module
from .connection import get_neo4j_driver, close_neo4j_driver
from .transaction_manager import TransactionManager

# Load environment variables
load_dotenv('.env', override=True)

def run_query(driver, query: str, params: Optional[Dict[str, Any]] = None, database: Optional[str] = None) -> List[Dict[str, Any]]:
    """Execute a Cypher query and return results with retry logic"""
    db = database or os.getenv('NEO4J_DATABASE', 'neo4j')
    manager = TransactionManager(driver)
    
    # Determine if this is a write operation based on query keywords
    write_keywords = ['CREATE', 'DELETE', 'SET', 'MERGE', 'REMOVE', 'DETACH']
    is_write = any(keyword in query.upper() for keyword in write_keywords)
    
    if is_write:
        return manager.execute_write(query, **(params or {}))
    else:
        return manager.execute_read(query, **(params or {}))

def clear_database(driver):
    """Clear all nodes and relationships from database"""
    query = "MATCH (n) DETACH DELETE n"
    run_query(driver, query)
    print("Database cleared")

def print_stats(driver):
    """Print basic database statistics"""
    queries = {
        "Total Nodes": "MATCH (n) RETURN COUNT(n) as count",
        "Properties": "MATCH (p:Property) RETURN COUNT(p) as count",
        "Neighborhoods": "MATCH (n:Neighborhood) RETURN COUNT(n) as count",
        "Cities": "MATCH (c:City) RETURN COUNT(c) as count",
        "Features": "MATCH (f:Feature) RETURN COUNT(f) as count",
        "Relationships": "MATCH ()-[r]->() RETURN COUNT(r) as count"
    }
    
    print("\n=== Database Statistics ===")
    for label, query in queries.items():
        result = run_query(driver, query)
        count = result[0]['count'] if result else 0
        print(f"{label}: {count}")
    print("===========================\n")