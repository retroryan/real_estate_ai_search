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
    """Print comprehensive database statistics including Wikipedia data"""
    queries = {
        "Total Nodes": "MATCH (n) RETURN COUNT(n) as count",
        "Properties": "MATCH (p:Property) RETURN COUNT(p) as count",
        "Neighborhoods": "MATCH (n:Neighborhood) RETURN COUNT(n) as count",
        "Cities": "MATCH (c:City) RETURN COUNT(c) as count",
        "Features": "MATCH (f:Feature) RETURN COUNT(f) as count",
        "Wikipedia Articles": "MATCH (w:Wikipedia) RETURN COUNT(w) as count",
        "Relationships": "MATCH ()-[r]->() RETURN COUNT(r) as count"
    }
    
    print("\n=== Database Statistics ===")
    for label, query in queries.items():
        result = run_query(driver, query)
        count = result[0]['count'] if result else 0
        print(f"{label}: {count}")
    
    # Wikipedia-specific statistics
    wiki_stats_queries = {
        "Wikipedia DESCRIBES relationships": "MATCH ()-[r:DESCRIBES]->() RETURN COUNT(r) as count",
        "Primary Wikipedia articles": "MATCH (w:Wikipedia) WHERE w.relationship_type = 'primary' RETURN COUNT(w) as count",
        "Related Wikipedia articles": "MATCH (w:Wikipedia) WHERE w.relationship_type IN ['related', 'neighborhood', 'park', 'landmark', 'county', 'city', 'recreation', 'reference'] RETURN COUNT(w) as count"
    }
    
    print("\n--- Wikipedia Integration ---")
    for label, query in wiki_stats_queries.items():
        result = run_query(driver, query)
        count = result[0]['count'] if result else 0
        print(f"{label}: {count}")
    
    # Wikipedia article types distribution
    type_query = """
    MATCH (w:Wikipedia) 
    RETURN w.relationship_type as type, COUNT(w) as count 
    ORDER BY count DESC
    """
    type_result = run_query(driver, type_query)
    if type_result:
        print("\n--- Wikipedia Article Types ---")
        for record in type_result:
            article_type = record['type'] or 'unknown'
            count = record['count']
            print(f"{article_type}: {count}")
    
    # Neighborhoods with Wikipedia coverage
    coverage_query = """
    MATCH (n:Neighborhood)
    OPTIONAL MATCH (w:Wikipedia)-[:DESCRIBES]->(n)
    WITH n.name as neighborhood, COUNT(w) as wiki_count
    WHERE wiki_count > 0
    RETURN neighborhood, wiki_count
    ORDER BY wiki_count DESC
    """
    coverage_result = run_query(driver, coverage_query)
    if coverage_result:
        print(f"\n--- Wikipedia Coverage by Neighborhood ---")
        for record in coverage_result[:10]:  # Top 10
            neighborhood = record['neighborhood']
            wiki_count = record['wiki_count']
            print(f"{neighborhood}: {wiki_count} articles")
    
    print("===========================\n")