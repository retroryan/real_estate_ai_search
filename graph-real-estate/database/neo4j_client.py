"""Neo4j database client and utilities"""
from typing import Dict, List, Any, Optional
from ..config.settings import get_settings

# Import from new connection module
from .connection import get_neo4j_driver, close_neo4j_driver
from .transaction_manager import TransactionManager


def run_query(driver, query: str, params: Optional[Dict[str, Any]] = None, database: Optional[str] = None) -> List[Dict[str, Any]]:
    """Execute a Cypher query and return results with retry logic"""
    settings = get_settings()
    db = database or settings.database.database
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
        "Wikipedia Articles": "MATCH (w:WikipediaArticle) RETURN COUNT(w) as count",
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
        "Primary Wikipedia articles": "MATCH (w:WikipediaArticle) WHERE w.relationship_type = 'primary' RETURN COUNT(w) as count",
        "Related Wikipedia articles": "MATCH (w:WikipediaArticle) WHERE w.relationship_type IN ['related', 'neighborhood', 'park', 'landmark', 'county', 'city', 'recreation', 'reference'] RETURN COUNT(w) as count"
    }
    
    print("\n--- Wikipedia Integration ---")
    for label, query in wiki_stats_queries.items():
        result = run_query(driver, query)
        count = result[0]['count'] if result else 0
        print(f"{label}: {count}")
    
    # Relationship type statistics
    rel_types_query = """
    MATCH ()-[r]->()
    RETURN TYPE(r) as relationship_type, COUNT(r) as count
    ORDER BY count DESC
    """
    
    print("\n--- Relationship Types ---")
    results = run_query(driver, rel_types_query)
    for result in results:
        print(f"{result['relationship_type']}: {result['count']}")

# Export functions
__all__ = [
    'get_neo4j_driver',
    'close_neo4j_driver', 
    'run_query',
    'clear_database',
    'print_stats'
]