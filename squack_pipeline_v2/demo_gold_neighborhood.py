#!/usr/bin/env python
"""Demo script for Gold layer Wikipedia-Neighborhood enrichment.

This script demonstrates the complete end-to-end enrichment from Silver to Gold layer,
showcasing search facets, quality scoring, and ranking enhancements.
"""

import duckdb
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.gold.wikipedia import WikipediaGoldEnricher


def create_demo_silver_data(conn: duckdb.DuckDBPyConnection) -> None:
    """Create demo Silver layer Wikipedia data with neighborhoods."""
    
    print("📊 Creating demo Silver layer data...")
    
    conn.execute("""
        DROP TABLE IF EXISTS silver_wikipedia_demo;
        CREATE TABLE silver_wikipedia_demo AS
        SELECT * FROM (VALUES
            -- Golden Gate Park - Multiple neighborhoods
            ('id1', 12345, 'loc1', 'Golden Gate Park', 'http://wiki.org/ggp',
             'Parks, Recreation, San Francisco', 37.7694, -122.4862,
             'San Francisco', 'San Francisco County', 'CA', 0.95, 2,
             '2024-01-01', 'ggp.html', 'hash1', 'ggp.jpg', 25, '{}',
             'Urban park spanning 1,017 acres',
             REPEAT('Golden Gate Park is a large urban park consisting of 1,017 acres of public grounds. ', 15),
             'golden gate park | ' || REPEAT('park description ', 20),
             NULL, NULL,
             CAST(['n1', 'n2', 'n3'] AS VARCHAR[]),
             CAST(['Richmond District', 'Sunset District', 'Haight-Ashbury'] AS VARCHAR[]),
             'Richmond District'),
             
            -- Coit Tower - Single neighborhood
            ('id2', 23456, 'loc2', 'Coit Tower', 'http://wiki.org/ct',
             'Towers, Landmarks, San Francisco', 37.8024, -122.4058,
             'San Francisco', 'San Francisco County', 'CA', 0.85, 1,
             '2024-01-01', 'ct.html', 'hash2', 'ct.jpg', 18, '{}',
             '210-foot tower in Telegraph Hill',
             REPEAT('Coit Tower is a 210-foot tower in the Telegraph Hill neighborhood. ', 10),
             'coit tower | ' || REPEAT('tower landmark ', 15),
             NULL, NULL,
             CAST(['n4'] AS VARCHAR[]),
             CAST(['Telegraph Hill'] AS VARCHAR[]),
             'Telegraph Hill'),
             
            -- Bay Bridge - No neighborhood
            ('id3', 34567, 'loc3', 'San Francisco-Oakland Bay Bridge', 'http://wiki.org/bb',
             'Bridges, Infrastructure, Transportation', 37.7983, -122.3778,
             'San Francisco', 'San Francisco County', 'CA', 0.90, 2,
             '2024-01-01', 'bb.html', 'hash3', 'bb.jpg', 30, '{}',
             'Complex of bridges spanning San Francisco Bay',
             REPEAT('The Bay Bridge is a complex of bridges in the San Francisco Bay Area. ', 12),
             'bay bridge | ' || REPEAT('bridge infrastructure ', 18),
             NULL, NULL,
             CAST(NULL AS VARCHAR[]),
             CAST(NULL AS VARCHAR[]),
             NULL),
             
            -- Alcatraz - No neighborhood (island)
            ('id4', 45678, 'loc4', 'Alcatraz Island', 'http://wiki.org/alc',
             'Islands, Prisons, History', 37.8267, -122.4233,
             'San Francisco', 'San Francisco County', 'CA', 0.88, 1,
             '2024-01-01', 'alc.html', 'hash4', 'alc.jpg', 22, '{}',
             'Island with former federal prison',
             REPEAT('Alcatraz Island is located in San Francisco Bay, 1.25 miles offshore. ', 8),
             'alcatraz island | ' || REPEAT('prison history ', 12),
             NULL, NULL,
             CAST(NULL AS VARCHAR[]),
             CAST(NULL AS VARCHAR[]),
             NULL),
             
            -- Mission Dolores - Single neighborhood
            ('id5', 56789, 'loc5', 'Mission San Francisco de Asís', 'http://wiki.org/md',
             'Missions, History, Religion', 37.7642, -122.4270,
             'San Francisco', 'San Francisco County', 'CA', 0.75, 1,
             '2024-01-01', 'md.html', 'hash5', 'md.jpg', 12, '{}',
             'Oldest surviving structure in SF',
             REPEAT('Mission Dolores is the oldest surviving structure in San Francisco. ', 6),
             'mission dolores | ' || REPEAT('historic mission ', 10),
             NULL, NULL,
             CAST(['n5'] AS VARCHAR[]),
             CAST(['Mission District'] AS VARCHAR[]),
             'Mission District')
        ) AS t(id, page_id, location_id, title, url, categories,
              latitude, longitude, city, county, state, relevance_score,
              depth, crawled_at, html_file, file_hash, image_url, links_count,
              infobox_data, short_summary, long_summary, embedding_text,
              embedding_vector, embedding_generated_at, neighborhood_ids,
              neighborhood_names, primary_neighborhood_name)
    """)
    
    print("✅ Silver layer demo data created")


def demonstrate_gold_enrichment(conn: duckdb.DuckDBPyConnection) -> None:
    """Demonstrate Gold layer enrichments with neighborhoods."""
    
    print("\n🏆 Creating Gold Layer View with Neighborhood Enrichments")
    print("=" * 70)
    
    # Create Gold view
    settings = PipelineSettings()
    conn_manager = DuckDBConnectionManager(settings.duckdb)
    enricher = WikipediaGoldEnricher(settings, conn_manager)
    
    enricher._create_enriched_view('silver_wikipedia_demo', 'gold_wikipedia_demo')
    
    print("✅ Gold view created with neighborhood enrichments\n")
    
    # 1. Show Search Facets
    print("📍 Search Facets (Including Neighborhood Filters):")
    print("-" * 70)
    
    facets = conn.execute("""
        SELECT 
            title,
            primary_neighborhood_name,
            search_facets
        FROM gold_wikipedia_demo
        ORDER BY page_id
    """).fetchall()
    
    for article in facets:
        neighborhood = article[1] or "None"
        # Find neighborhood facet
        facet_list = article[2]
        neighborhood_facet = [f for f in facet_list if 'neighborhood' in f][0]
        print(f"  {article[0][:40]:<40} | {neighborhood[:20]:<20} | {neighborhood_facet}")
    
    # 2. Show Quality Scores with Boost
    print("\n📊 Quality Scores (With Neighborhood Boost):")
    print("-" * 70)
    
    quality = conn.execute("""
        SELECT 
            title,
            neighborhood_count,
            article_quality_score,
            article_quality
        FROM gold_wikipedia_demo
        ORDER BY article_quality_score DESC
    """).fetchall()
    
    print(f"  {'Title':<40} | {'Neighborhoods':<13} | {'Score':<7} | Quality")
    print(f"  {'-'*40} | {'-'*13} | {'-'*7} | {'-'*10}")
    for article in quality:
        print(f"  {article[0][:40]:<40} | {article[1]:^13} | {article[2]:<7.3f} | {article[3]}")
    
    # 3. Show Search Ranking
    print("\n🔍 Search Ranking (With Neighborhood Component):")
    print("-" * 70)
    
    ranking = conn.execute("""
        SELECT 
            title,
            has_neighborhood_association,
            search_ranking_score,
            authority_score
        FROM gold_wikipedia_demo
        ORDER BY search_ranking_score DESC
    """).fetchall()
    
    print(f"  {'Title':<40} | {'Has Neighborhood':<16} | {'Rank Score':<10} | Authority")
    print(f"  {'-'*40} | {'-'*16} | {'-'*10} | {'-'*10}")
    for article in ranking:
        has_neighborhood = "✅ Yes" if article[1] else "❌ No"
        print(f"  {article[0][:40]:<40} | {has_neighborhood:<16} | {article[2]:<10.3f} | {article[3]:.1f}")
    
    # 4. Show Aggregated Statistics
    print("\n📈 Aggregated Statistics:")
    print("-" * 70)
    
    stats = conn.execute("""
        WITH stats AS (
            SELECT 
                COUNT(*) as total_articles,
                COUNT(CASE WHEN has_neighborhood_association THEN 1 END) as with_neighborhoods,
                AVG(article_quality_score) as avg_quality_score,
                AVG(CASE WHEN has_neighborhood_association 
                    THEN article_quality_score END) as avg_quality_with_neighborhood,
                AVG(CASE WHEN NOT has_neighborhood_association 
                    THEN article_quality_score END) as avg_quality_without_neighborhood
            FROM gold_wikipedia_demo
        )
        SELECT * FROM stats
    """).fetchone()
    
    print(f"  Total articles: {stats[0]}")
    print(f"  Articles with neighborhoods: {stats[1]} ({stats[1]/stats[0]*100:.0f}%)")
    print(f"  Average quality score (all): {stats[2]:.3f}")
    print(f"  Average quality (with neighborhood): {stats[3]:.3f}")
    print(f"  Average quality (without neighborhood): {stats[4]:.3f}")
    print(f"  Quality boost from neighborhoods: +{(stats[3] - stats[4]):.3f}")
    
    # 5. Show Facet Distribution
    print("\n📊 Facet Distribution:")
    print("-" * 70)
    
    facet_dist = conn.execute("""
        SELECT 
            CASE 
                WHEN 'multi_neighborhood' = ANY(search_facets) THEN 'Multi-Neighborhood'
                WHEN 'has_neighborhood' = ANY(search_facets) THEN 'Single Neighborhood'
                WHEN 'no_neighborhood' = ANY(search_facets) THEN 'No Neighborhood'
            END as neighborhood_type,
            COUNT(*) as count,
            AVG(article_quality_score) as avg_quality,
            AVG(search_ranking_score) as avg_ranking
        FROM gold_wikipedia_demo
        GROUP BY neighborhood_type
        ORDER BY count DESC
    """).fetchall()
    
    print(f"  {'Type':<20} | {'Count':<6} | {'Avg Quality':<11} | Avg Ranking")
    print(f"  {'-'*20} | {'-'*6} | {'-'*11} | {'-'*11}")
    for facet in facet_dist:
        print(f"  {facet[0]:<20} | {facet[1]:^6} | {facet[2]:<11.3f} | {facet[3]:.3f}")


def main():
    """Run the Gold layer neighborhood enrichment demo."""
    print("🚀 Gold Layer Neighborhood Enrichment Demo")
    print("=" * 70)
    print("Demonstrating search facets, quality scoring, and ranking enhancements")
    print("with neighborhood-based enrichments in the Gold layer.")
    print("=" * 70)
    
    # Setup connection
    settings = PipelineSettings()
    conn_manager = DuckDBConnectionManager(settings.duckdb)
    conn = conn_manager.get_connection()
    
    # Run demo
    create_demo_silver_data(conn)
    demonstrate_gold_enrichment(conn)
    
    print("\n✨ Demo completed successfully!")
    print("=" * 70)
    print("\n💡 Key Insights:")
    print("  • Articles with neighborhoods receive quality score boosts")
    print("  • Search facets enable filtering by neighborhood association")
    print("  • Ranking algorithm includes neighborhood presence as a factor")
    print("  • Multi-neighborhood articles get the highest boost")
    print("=" * 70)


if __name__ == "__main__":
    main()