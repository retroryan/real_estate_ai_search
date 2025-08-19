"""Neo4j database client and utilities"""
import os
from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env', override=True)

def get_neo4j_driver():
    """Create and return Neo4j driver instance"""
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    username = os.getenv('NEO4J_USERNAME', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'password')
    
    driver = GraphDatabase.driver(uri, auth=(username, password))
    return driver

def close_neo4j_driver(driver):
    """Close Neo4j driver connection"""
    if driver:
        driver.close()

def run_query(driver, query: str, params: Optional[Dict[str, Any]] = None, database: Optional[str] = None) -> List[Dict[str, Any]]:
    """Execute a Cypher query and return results"""
    db = database or os.getenv('NEO4J_DATABASE', 'neo4j')
    with driver.session(database=db) as session:
        result = session.run(query, params)
        return [dict(record) for record in result]

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