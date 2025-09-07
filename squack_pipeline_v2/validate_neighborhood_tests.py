"""Validate neighborhood-Wikipedia associations through all pipeline layers."""

import json
import duckdb
from pathlib import Path
from typing import Dict, List, Any
from squack_pipeline_v2.core.connection import DuckDBConnectionManager

def validate_source_data() -> Dict[str, Any]:
    """Validate source neighborhood JSON files have Wikipedia correlations."""
    results = {
        'sf_neighborhoods': 0,
        'sf_with_wiki': 0,
        'pc_neighborhoods': 0, 
        'pc_with_wiki': 0,
        'total_page_ids': set()
    }
    
    # Check SF neighborhoods
    sf_path = Path('real_estate_data/neighborhoods_sf.json')
    if sf_path.exists():
        with open(sf_path) as f:
            sf_data = json.load(f)
            results['sf_neighborhoods'] = len(sf_data)
            for n in sf_data:
                wiki = n.get('wikipedia_correlations', {})
                if wiki and wiki.get('primary_wiki_article'):
                    results['sf_with_wiki'] += 1
                    page_id = wiki['primary_wiki_article'].get('page_id')
                    if page_id:
                        results['total_page_ids'].add(page_id)
    
    # Check PC neighborhoods
    pc_path = Path('real_estate_data/neighborhoods_pc.json')
    if pc_path.exists():
        with open(pc_path) as f:
            pc_data = json.load(f)
            results['pc_neighborhoods'] = len(pc_data)
            for n in pc_data:
                wiki = n.get('wikipedia_correlations', {})
                if wiki and wiki.get('primary_wiki_article'):
                    results['pc_with_wiki'] += 1
                    page_id = wiki['primary_wiki_article'].get('page_id')
                    if page_id:
                        results['total_page_ids'].add(page_id)
    
    results['unique_page_ids'] = len(results['total_page_ids'])
    return results


def validate_bronze_layer(conn_manager: DuckDBConnectionManager) -> Dict[str, Any]:
    """Validate Bronze layer neighborhood data has Wikipedia correlations."""
    conn = conn_manager.get_connection()
    results = {}
    
    # Check if bronze_neighborhoods table exists
    table_exists = conn.execute("""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_name = 'bronze_neighborhoods'
    """).fetchone()[0] > 0
    
    if not table_exists:
        results['table_exists'] = False
        return results
    
    results['table_exists'] = True
    
    # Get table info
    results['total_neighborhoods'] = conn.execute(
        "SELECT COUNT(*) FROM bronze_neighborhoods"
    ).fetchone()[0]
    
    # Check for wikipedia_correlations column
    columns = conn.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'bronze_neighborhoods'
    """).fetchall()
    
    results['columns'] = {col[0]: col[1] for col in columns}
    results['has_wiki_column'] = 'wikipedia_correlations' in results['columns']
    
    if results['has_wiki_column']:
        # Count neighborhoods with Wikipedia correlations
        results['with_wiki_correlations'] = conn.execute("""
            SELECT COUNT(*) 
            FROM bronze_neighborhoods 
            WHERE wikipedia_correlations IS NOT NULL
        """).fetchone()[0]
        
        # Sample a few to check structure
        sample = conn.execute("""
            SELECT 
                neighborhood_id, 
                name, 
                wikipedia_correlations.primary_wiki_article.page_id as wiki_page_id,
                wikipedia_correlations.primary_wiki_article.title as wiki_title
            FROM bronze_neighborhoods 
            WHERE wikipedia_correlations IS NOT NULL 
            AND wikipedia_correlations.primary_wiki_article.page_id IS NOT NULL
            LIMIT 5
        """).fetchall()
        
        results['sample_correlations'] = []
        for row in sample:
            results['sample_correlations'].append({
                'neighborhood_id': row[0],
                'name': row[1],
                'has_primary_article': True,
                'page_id': row[2],
                'wiki_title': row[3]
            })
    
    return results


def validate_silver_layer(conn_manager: DuckDBConnectionManager) -> Dict[str, Any]:
    """Validate Silver layer neighborhood enrichment."""
    conn = conn_manager.get_connection()
    results = {}
    
    # Check if silver_neighborhoods table exists
    table_exists = conn.execute("""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_name = 'silver_neighborhoods'
    """).fetchone()[0] > 0
    
    if not table_exists:
        results['table_exists'] = False
        return results
    
    results['table_exists'] = True
    
    # Get table info
    results['total_neighborhoods'] = conn.execute(
        "SELECT COUNT(*) FROM silver_neighborhoods"
    ).fetchone()[0]
    
    # Check for Wikipedia-related columns
    columns = conn.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'silver_neighborhoods'
        AND column_name LIKE '%wiki%'
    """).fetchall()
    
    results['wiki_columns'] = {col[0]: col[1] for col in columns}
    
    # Check for wikipedia_page_id column specifically
    results['has_wiki_page_id'] = conn.execute("""
        SELECT COUNT(*) FROM information_schema.columns 
        WHERE table_name = 'silver_neighborhoods'
        AND column_name = 'wikipedia_page_id'
    """).fetchone()[0] > 0
    
    if results['has_wiki_page_id']:
        # Count neighborhoods with Wikipedia page IDs
        results['with_wiki_page_id'] = conn.execute("""
            SELECT COUNT(*) 
            FROM silver_neighborhoods 
            WHERE wikipedia_page_id IS NOT NULL
        """).fetchone()[0]
        
        # Get sample
        sample = conn.execute("""
            SELECT neighborhood_id, name, wikipedia_page_id 
            FROM silver_neighborhoods 
            WHERE wikipedia_page_id IS NOT NULL
            LIMIT 5
        """).fetchall()
        
        results['sample_page_ids'] = [
            {'neighborhood_id': row[0], 'name': row[1], 'wikipedia_page_id': row[2]}
            for row in sample
        ]
    
    # Check wikipedia_correlations if it exists
    if 'wikipedia_correlations' in results['wiki_columns']:
        results['with_wiki_correlations'] = conn.execute("""
            SELECT COUNT(*) 
            FROM silver_neighborhoods 
            WHERE wikipedia_correlations IS NOT NULL 
            AND wikipedia_correlations != '{}'
            AND wikipedia_correlations != ''
        """).fetchone()[0]
    
    return results


def validate_silver_wikipedia(conn_manager: DuckDBConnectionManager) -> Dict[str, Any]:
    """Validate Silver layer Wikipedia data has neighborhood associations."""
    conn = conn_manager.get_connection()
    results = {}
    
    # Check if silver_wikipedia table exists
    table_exists = conn.execute("""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_name = 'silver_wikipedia'
    """).fetchone()[0] > 0
    
    if not table_exists:
        results['table_exists'] = False
        return results
    
    results['table_exists'] = True
    
    # Get total Wikipedia articles
    results['total_articles'] = conn.execute(
        "SELECT COUNT(*) FROM silver_wikipedia"
    ).fetchone()[0]
    
    # Check for neighborhood-related columns
    columns = conn.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'silver_wikipedia'
        AND column_name LIKE '%neighborhood%'
    """).fetchall()
    
    results['neighborhood_columns'] = {col[0]: col[1] for col in columns}
    
    # Check specific neighborhood columns
    for col in ['neighborhood_ids', 'neighborhood_names', 'primary_neighborhood_name']:
        has_col = conn.execute(f"""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'silver_wikipedia'
            AND column_name = '{col}'
        """).fetchone()[0] > 0
        
        results[f'has_{col}'] = has_col
        
        if has_col:
            # Count articles with this field populated
            if 'ids' in col or 'names' in col:
                # Array columns
                results[f'with_{col}'] = conn.execute(f"""
                    SELECT COUNT(*) 
                    FROM silver_wikipedia 
                    WHERE {col} IS NOT NULL 
                    AND ARRAY_LENGTH({col}) > 0
                """).fetchone()[0]
            else:
                # String column
                results[f'with_{col}'] = conn.execute(f"""
                    SELECT COUNT(*) 
                    FROM silver_wikipedia 
                    WHERE {col} IS NOT NULL 
                    AND {col} != ''
                """).fetchone()[0]
    
    # Get sample of articles with neighborhood associations
    if results.get('has_neighborhood_ids'):
        sample = conn.execute("""
            SELECT page_id, title, neighborhood_ids, neighborhood_names 
            FROM silver_wikipedia 
            WHERE neighborhood_ids IS NOT NULL 
            AND ARRAY_LENGTH(neighborhood_ids) > 0
            LIMIT 5
        """).fetchall()
        
        results['sample_with_neighborhoods'] = [
            {
                'page_id': row[0],
                'title': row[1],
                'neighborhood_ids': row[2],
                'neighborhood_names': row[3]
            }
            for row in sample
        ]
    
    return results


def validate_gold_layer(conn_manager: DuckDBConnectionManager) -> Dict[str, Any]:
    """Validate Gold layer Wikipedia data has neighborhood associations."""
    conn = conn_manager.get_connection()
    results = {}
    
    # Check if gold_wikipedia table exists
    table_exists = conn.execute("""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_name = 'gold_wikipedia'
    """).fetchone()[0] > 0
    
    if not table_exists:
        results['table_exists'] = False
        return results
    
    results['table_exists'] = True
    
    # Get total Wikipedia articles
    results['total_articles'] = conn.execute(
        "SELECT COUNT(*) FROM gold_wikipedia"
    ).fetchone()[0]
    
    # Check for neighborhood columns
    neighborhood_cols = ['neighborhood_ids', 'neighborhood_names', 'primary_neighborhood_name', 
                        'neighborhood_count', 'has_neighborhood_association']
    
    for col in neighborhood_cols:
        has_col = conn.execute(f"""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'gold_wikipedia'
            AND column_name = '{col}'
        """).fetchone()[0] > 0
        
        results[f'has_{col}'] = has_col
    
    # Count articles with neighborhood associations
    if results.get('has_has_neighborhood_association'):
        results['with_associations'] = conn.execute("""
            SELECT COUNT(*) 
            FROM gold_wikipedia 
            WHERE has_neighborhood_association = true
        """).fetchone()[0]
        
        # Get sample
        sample = conn.execute("""
            SELECT page_id, title, neighborhood_ids, neighborhood_names, neighborhood_count
            FROM gold_wikipedia 
            WHERE has_neighborhood_association = true
            LIMIT 10
        """).fetchall()
        
        results['sample_with_associations'] = [
            {
                'page_id': row[0],
                'title': row[1],
                'neighborhood_ids': row[2],
                'neighborhood_names': row[3],
                'neighborhood_count': row[4]
            }
            for row in sample
        ]
    
    return results


def main():
    """Run validation tests across all layers."""
    print("=" * 80)
    print("VALIDATING NEIGHBORHOOD-WIKIPEDIA ASSOCIATIONS")
    print("=" * 80)
    
    # 1. Validate source data
    print("\n1. SOURCE DATA VALIDATION")
    print("-" * 40)
    source_results = validate_source_data()
    print(f"SF Neighborhoods: {source_results['sf_neighborhoods']} total, {source_results['sf_with_wiki']} with Wikipedia")
    print(f"PC Neighborhoods: {source_results['pc_neighborhoods']} total, {source_results['pc_with_wiki']} with Wikipedia")
    print(f"Unique Wikipedia page IDs: {source_results['unique_page_ids']}")
    print(f"Expected page IDs: {sorted(list(source_results['total_page_ids']))[:10]}...")
    
    # Initialize connection manager
    conn_manager = DuckDBConnectionManager()
    
    # 2. Validate Bronze layer
    print("\n2. BRONZE LAYER VALIDATION")
    print("-" * 40)
    bronze_results = validate_bronze_layer(conn_manager)
    if not bronze_results.get('table_exists'):
        print("❌ bronze_neighborhoods table does not exist!")
    else:
        print(f"✓ Table exists with {bronze_results['total_neighborhoods']} neighborhoods")
        print(f"Has wikipedia_correlations column: {bronze_results.get('has_wiki_column')}")
        if bronze_results.get('has_wiki_column'):
            print(f"Neighborhoods with Wikipedia correlations: {bronze_results.get('with_wiki_correlations', 0)}")
            if bronze_results.get('sample_correlations'):
                print("Sample correlations:")
                for sample in bronze_results['sample_correlations']:
                    print(f"  - {sample['name']}: page_id={sample.get('page_id')}")
    
    # 3. Validate Silver neighborhoods
    print("\n3. SILVER LAYER - NEIGHBORHOODS")
    print("-" * 40)
    silver_neigh_results = validate_silver_layer(conn_manager)
    if not silver_neigh_results.get('table_exists'):
        print("❌ silver_neighborhoods table does not exist!")
    else:
        print(f"✓ Table exists with {silver_neigh_results['total_neighborhoods']} neighborhoods")
        print(f"Wikipedia-related columns: {silver_neigh_results.get('wiki_columns', {})}")
        print(f"Has wikipedia_page_id column: {silver_neigh_results.get('has_wiki_page_id')}")
        if silver_neigh_results.get('has_wiki_page_id'):
            print(f"Neighborhoods with Wikipedia page IDs: {silver_neigh_results.get('with_wiki_page_id', 0)}")
            if silver_neigh_results.get('sample_page_ids'):
                print("Sample page IDs:")
                for sample in silver_neigh_results['sample_page_ids'][:3]:
                    print(f"  - {sample['name']}: {sample['wikipedia_page_id']}")
    
    # 4. Validate Silver Wikipedia
    print("\n4. SILVER LAYER - WIKIPEDIA")
    print("-" * 40)
    silver_wiki_results = validate_silver_wikipedia(conn_manager)
    if not silver_wiki_results.get('table_exists'):
        print("❌ silver_wikipedia table does not exist!")
    else:
        print(f"✓ Table exists with {silver_wiki_results['total_articles']} articles")
        print(f"Neighborhood columns: {silver_wiki_results.get('neighborhood_columns', {})}")
        for col in ['neighborhood_ids', 'neighborhood_names', 'primary_neighborhood_name']:
            if silver_wiki_results.get(f'has_{col}'):
                print(f"✓ Has {col}: {silver_wiki_results.get(f'with_{col}', 0)} articles with data")
            else:
                print(f"❌ Missing {col} column")
        
        if silver_wiki_results.get('sample_with_neighborhoods'):
            print("Sample articles with neighborhoods:")
            for sample in silver_wiki_results['sample_with_neighborhoods'][:3]:
                print(f"  - {sample['title']}: {sample['neighborhood_names']}")
    
    # 5. Validate Gold layer
    print("\n5. GOLD LAYER VALIDATION")
    print("-" * 40)
    gold_results = validate_gold_layer(conn_manager)
    if not gold_results.get('table_exists'):
        print("❌ gold_wikipedia table does not exist!")
    else:
        print(f"✓ Table exists with {gold_results['total_articles']} articles")
        neighborhood_cols = ['neighborhood_ids', 'neighborhood_names', 'primary_neighborhood_name', 
                           'neighborhood_count', 'has_neighborhood_association']
        for col in neighborhood_cols:
            print(f"Has {col}: {gold_results.get(f'has_{col}')}")
        
        if gold_results.get('has_has_neighborhood_association'):
            print(f"\nArticles with neighborhood associations: {gold_results.get('with_associations', 0)}")
            if gold_results.get('sample_with_associations'):
                print("Sample articles with associations:")
                for sample in gold_results['sample_with_associations'][:5]:
                    print(f"  - {sample['title']}: {sample['neighborhood_names']} (count: {sample['neighborhood_count']})")
    
    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
    
    # Summary
    expected_associations = source_results['sf_with_wiki'] + source_results['pc_with_wiki']
    actual_associations = gold_results.get('with_associations', 0) if gold_results.get('table_exists') else 0
    
    print(f"\nEXPECTED: {expected_associations} neighborhoods with Wikipedia associations")
    print(f"ACTUAL: {actual_associations} Wikipedia articles with neighborhood associations")
    
    if actual_associations < expected_associations:
        print(f"\n❌ MISSING {expected_associations - actual_associations} associations!")
        print("The associations are being lost somewhere in the pipeline.")
    elif actual_associations == expected_associations:
        print("\n✓ All expected associations are present!")
    else:
        print(f"\n⚠️ More associations than expected (might be due to multiple neighborhoods per article)")
    
    return {
        'source': source_results,
        'bronze': bronze_results,
        'silver_neighborhoods': silver_neigh_results,
        'silver_wikipedia': silver_wiki_results,
        'gold': gold_results
    }


if __name__ == "__main__":
    results = main()