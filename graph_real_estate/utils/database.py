"""Simple Neo4j database utilities for initialization"""

import os
from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase, Driver
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env', override=True)


def get_neo4j_driver() -> Driver:
    """
    Create and return a Neo4j driver instance
    
    Returns:
        Neo4j Driver instance
    """
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    username = os.getenv('NEO4J_USERNAME', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'password')
    
    driver = GraphDatabase.driver(uri, auth=(username, password))
    return driver


def close_neo4j_driver(driver: Driver) -> None:
    """
    Close Neo4j driver connection
    
    Args:
        driver: Neo4j Driver instance to close
    """
    if driver:
        driver.close()


def run_query(driver: Driver, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Execute a Cypher query and return results
    
    Args:
        driver: Neo4j Driver instance
        query: Cypher query string
        params: Optional query parameters
        
    Returns:
        List of result records as dictionaries
    """
    results = []
    
    with driver.session() as session:
        try:
            # Determine if this is a write operation
            write_keywords = ['CREATE', 'DELETE', 'SET', 'MERGE', 'REMOVE', 'DETACH']
            is_write = any(keyword in query.upper() for keyword in write_keywords)
            
            if is_write:
                # Use write transaction
                def write_tx(tx):
                    result = tx.run(query, **(params or {}))
                    return list(result)
                
                records = session.execute_write(write_tx)
            else:
                # Use read transaction
                def read_tx(tx):
                    result = tx.run(query, **(params or {}))
                    return list(result)
                
                records = session.execute_read(read_tx)
            
            # Convert records to dictionaries
            for record in records:
                results.append(dict(record))
                
        except Exception as e:
            print(f"Query execution error: {e}")
            raise
    
    return results


def clear_database(driver: Driver) -> None:
    """
    Clear all nodes and relationships from database
    
    Args:
        driver: Neo4j Driver instance
    """
    query = "MATCH (n) DETACH DELETE n"
    run_query(driver, query)
    print("✓ All data cleared from database")