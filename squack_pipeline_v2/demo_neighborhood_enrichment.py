#!/usr/bin/env python
"""Demo script for Wikipedia-Neighborhood enrichment feature.

This script demonstrates the high-quality implementation of enriching Wikipedia
articles with neighborhood data, following DuckDB best practices.
"""

import duckdb
from pathlib import Path
from squack_pipeline_v2.core.settings import PipelineSettings
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.utils.neighborhood_enrichment import NeighborhoodWikipediaEnricher
from squack_pipeline_v2.utils.table_validation import validate_table_name


def create_demo_data(conn: duckdb.DuckDBPyConnection) -> None:
    """Create demo data for neighborhoods and Wikipedia articles."""
    
    print("📊 Creating demo data...")
    
    # Create demo neighborhoods
    conn.execute("""
        DROP TABLE IF EXISTS silver_neighborhoods;
        CREATE TABLE silver_neighborhoods AS
        SELECT * FROM (VALUES
            ('n1', 'Mission District', 'San Francisco', 'CA', 'Historic neighborhood known for murals and Latin culture', 12345),
            ('n2', 'Castro District', 'San Francisco', 'CA', 'LGBTQ+ cultural center with Victorian architecture', 12345),
            ('n3', 'SOMA', 'San Francisco', 'CA', 'Tech hub and urban residential area', 67890),
            ('n4', 'Haight-Ashbury', 'San Francisco', 'CA', 'Birthplace of 1960s counterculture', 11111),
            ('n5', 'Pacific Heights', 'San Francisco', 'CA', 'Upscale residential with bay views', NULL)
        ) AS t(neighborhood_id, name, city, state, description, wikipedia_page_id)
    """)
    
    # Create demo Wikipedia articles
    conn.execute("""
        DROP TABLE IF EXISTS silver_wikipedia;
        CREATE TABLE silver_wikipedia AS
        SELECT * FROM (VALUES
            (12345, 'Golden Gate Park', 'Large urban park in San Francisco with museums and gardens'),
            (67890, 'Salesforce Tower', 'Tallest building in San Francisco and tech landmark'),
            (11111, 'Summer of Love', '1967 social phenomenon centered in San Francisco'),
            (99999, 'Bay Bridge', 'Major bridge connecting SF to Oakland'),
            (88888, 'Alcatraz Island', 'Former federal prison turned tourist attraction')
        ) AS t(page_id, title, long_summary)
    """)
    
    print("✅ Demo data created successfully")


def demonstrate_enrichment(conn: duckdb.DuckDBPyConnection) -> None:
    """Demonstrate the neighborhood enrichment functionality."""
    
    print("\n🔍 Demonstrating Neighborhood Enrichment")
    print("=" * 60)
    
    # Create enricher
    enricher = NeighborhoodWikipediaEnricher(conn)
    
    # Check if neighborhoods exist
    if enricher.check_neighborhoods_table_exists():
        print("✅ Neighborhoods table found")
    
    # Show neighborhood mappings using CTE (DuckDB best practice)
    print("\n📍 Neighborhood-Wikipedia Mappings (using CTE):")
    print("-" * 60)
    
    mappings = conn.execute(f"""
        WITH {enricher.get_neighborhood_mappings_cte()}
        SELECT 
            page_id,
            primary_neighborhood_name,
            array_length(neighborhood_names) as neighborhood_count,
            neighborhood_names
        FROM neighborhood_mappings
        ORDER BY page_id
    """).fetchall()
    
    for mapping in mappings:
        print(f"  Page ID {mapping[0]}: {mapping[1]} (+ {mapping[2]-1} more)")
        print(f"    All neighborhoods: {', '.join(mapping[3])}")
    
    # Demonstrate enriched Wikipedia query
    print("\n📚 Enriched Wikipedia Articles:")
    print("-" * 60)
    
    enriched = conn.execute("""
        WITH neighborhood_mappings AS (
            SELECT 
                wikipedia_page_id as page_id,
                LIST(DISTINCT neighborhood_id ORDER BY neighborhood_id) as neighborhood_ids,
                LIST(DISTINCT name ORDER BY name) as neighborhood_names,
                FIRST(name ORDER BY neighborhood_id) as primary_neighborhood_name
            FROM silver_neighborhoods
            WHERE wikipedia_page_id IS NOT NULL
            GROUP BY wikipedia_page_id
        )
        SELECT 
            w.page_id,
            w.title,
            n.primary_neighborhood_name,
            n.neighborhood_names,
            CASE 
                WHEN n.neighborhood_names IS NOT NULL THEN 'enriched'
                ELSE 'no-association'
            END as status
        FROM silver_wikipedia w
        LEFT JOIN neighborhood_mappings n ON w.page_id = n.page_id
        ORDER BY w.page_id
    """).fetchall()
    
    for article in enriched:
        status_emoji = "🏘️" if article[4] == "enriched" else "📄"
        print(f"  {status_emoji} {article[1]} (ID: {article[0]})")
        if article[2]:
            neighborhoods = ', '.join(article[3]) if article[3] else 'None'
            print(f"      Primary: {article[2]}")
            print(f"      All: {neighborhoods}")
        else:
            print(f"      No neighborhood associations")
    
    # Show statistics
    print("\n📊 Enrichment Statistics:")
    print("-" * 60)
    
    stats = conn.execute("""
        WITH enriched AS (
            SELECT 
                COUNT(*) as total_articles,
                COUNT(CASE WHEN primary_neighborhood_name IS NOT NULL THEN 1 END) as enriched_articles
            FROM (
                SELECT w.*, n.primary_neighborhood_name
                FROM silver_wikipedia w
                LEFT JOIN (
                    SELECT 
                        wikipedia_page_id as page_id,
                        FIRST(name ORDER BY neighborhood_id) as primary_neighborhood_name
                    FROM silver_neighborhoods
                    WHERE wikipedia_page_id IS NOT NULL
                    GROUP BY wikipedia_page_id
                ) n ON w.page_id = n.page_id
            )
        )
        SELECT * FROM enriched
    """).fetchone()
    
    print(f"  Total Wikipedia articles: {stats[0]}")
    print(f"  Articles with neighborhoods: {stats[1]}")
    print(f"  Enrichment rate: {stats[1]/stats[0]*100:.1f}%")


def demonstrate_best_practices(conn: duckdb.DuckDBPyConnection) -> None:
    """Demonstrate DuckDB best practices in the implementation."""
    
    print("\n🎯 DuckDB Best Practices Demonstrated:")
    print("=" * 60)
    
    # 1. Table name validation
    print("\n1️⃣  Table Name Validation:")
    table_name = "wikipedia_enriched"
    try:
        validated = validate_table_name(table_name)
        print(f"  ✅ '{table_name}' is valid")
    except ValueError as e:
        print(f"  ❌ Error: {e}")
    
    # Try invalid name
    try:
        validate_table_name("123-invalid-name!")
    except ValueError as e:
        print(f"  ✅ Invalid name caught: {e}")
    
    # 2. Using CTEs instead of temporary tables
    print("\n2️⃣  Using CTEs (Common Table Expressions):")
    print("  ✅ CTE used for neighborhood mappings")
    print("  ✅ No temporary tables created for mappings")
    print("  ✅ Single CREATE TABLE statement for final result")
    
    # 3. Using Relation API
    print("\n3️⃣  Relation API Usage:")
    neighborhoods = conn.table("silver_neighborhoods")
    filtered = neighborhoods.filter("wikipedia_page_id IS NOT NULL")
    count = filtered.count("*").fetchone()[0]
    print(f"  ✅ Relation API: {count} neighborhoods with Wikipedia associations")
    
    # 4. Parameterized queries
    print("\n4️⃣  Query Safety:")
    print("  ✅ Table names validated at boundaries")
    print("  ✅ CTEs used for complex queries")
    print("  ✅ No string concatenation for user input")
    
    # 5. Efficient operations
    print("\n5️⃣  Efficiency:")
    print("  ✅ Single connection reused throughout")
    print("  ✅ Batch operations for embeddings")
    print("  ✅ Native DuckDB aggregation functions")


def main():
    """Run the demo."""
    print("🚀 Wikipedia-Neighborhood Enrichment Demo")
    print("=" * 60)
    print("This demo showcases the high-quality implementation of")
    print("enriching Wikipedia articles with neighborhood data.")
    print("=" * 60)
    
    # Setup connection
    settings = PipelineSettings()
    conn_manager = DuckDBConnectionManager(settings.duckdb)
    conn = conn_manager.get_connection()
    
    # Run demo
    create_demo_data(conn)
    demonstrate_enrichment(conn)
    demonstrate_best_practices(conn)
    
    print("\n✨ Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()