"""Verify the graph after Phases 1-3"""
from src.database import get_neo4j_driver, run_query, close_neo4j_driver

def verify_graph():
    """Verify the complete graph state"""
    driver = get_neo4j_driver()
    
    print("="*60)
    print("GRAPH VERIFICATION SUMMARY")
    print("="*60)
    
    # Node counts
    print("\n📊 NODE COUNTS:")
    node_queries = [
        ("States", "MATCH (s:State) RETURN count(s) as count"),
        ("Counties", "MATCH (c:County) RETURN count(c) as count"),
        ("Cities", "MATCH (c:City) RETURN count(c) as count"),
        ("Wikipedia Articles", "MATCH (w:WikipediaArticle) RETURN count(w) as count"),
    ]
    
    for name, query in node_queries:
        result = run_query(driver, query)
        count = result[0]['count'] if result else 0
        print(f"  {name}: {count}")
    
    # Relationship counts
    print("\n🔗 RELATIONSHIP COUNTS:")
    rel_queries = [
        ("County→State", "MATCH ()-[r:IN_STATE]->(:State) RETURN count(r) as count"),
        ("City→County", "MATCH ()-[r:IN_COUNTY]->(:County) RETURN count(r) as count"),
        ("Wikipedia→State", "MATCH (:WikipediaArticle)-[r:IN_STATE]->() RETURN count(r) as count"),
        ("Wikipedia→County", "MATCH (:WikipediaArticle)-[r:IN_COUNTY]->() RETURN count(r) as count"),
        ("Wikipedia→City", "MATCH (:WikipediaArticle)-[r:DESCRIBES_LOCATION_IN]->() RETURN count(r) as count"),
    ]
    
    for name, query in rel_queries:
        result = run_query(driver, query)
        count = result[0]['count'] if result else 0
        print(f"  {name}: {count}")
    
    # Sample queries
    print("\n🔍 SAMPLE DATA:")
    
    # Cities with most Wikipedia articles
    query = """
    MATCH (w:WikipediaArticle)-[:DESCRIBES_LOCATION_IN]->(c:City)
    RETURN c.city_name as city, count(w) as wiki_count
    ORDER BY wiki_count DESC
    LIMIT 5
    """
    result = run_query(driver, query)
    if result:
        print("\n  Cities with most Wikipedia articles:")
        for row in result:
            print(f"    - {row['city']}: {row['wiki_count']} articles")
    
    # Topics sample
    query = """
    MATCH (w:WikipediaArticle)
    WHERE size(w.key_topics) > 3
    RETURN w.title as title, w.key_topics[0..3] as topics
    LIMIT 3
    """
    result = run_query(driver, query)
    if result:
        print("\n  Sample Wikipedia topics:")
        for row in result:
            if row.get('title') and row.get('topics'):
                print(f"    - {row['title']}: {', '.join(row['topics'])}")
    
    # Geographic paths
    query = """
    MATCH path = (c:City)-[:IN_COUNTY]->(co:County)-[:IN_STATE]->(s:State)
    RETURN count(path) as complete_paths
    """
    result = run_query(driver, query)
    if result:
        print(f"\n  Complete geographic paths (City→County→State): {result[0]['complete_paths']}")
    
    print("\n" + "="*60)
    print("✅ GRAPH VERIFICATION COMPLETE")
    print("="*60)
    
    close_neo4j_driver(driver)

if __name__ == "__main__":
    verify_graph()