#!/usr/bin/env python3
"""
Simple Eland DataFrames Demo for Property Data
==============================================
A concise demonstration of using Eland with Elasticsearch property data.
"""

import os
import sys
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import eland as ed
import pandas as pd
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

def connect_to_elasticsearch():
    """Create Elasticsearch connection."""
    es_client = Elasticsearch(
        hosts=[{
            'host': os.getenv('ES_HOST', 'localhost'),
            'port': int(os.getenv('ES_PORT', 9200)),
            'scheme': os.getenv('ES_SCHEME', 'http')
        }],
        basic_auth=(os.getenv('ES_USERNAME'), os.getenv('ES_PASSWORD')) if os.getenv('ES_PASSWORD') else None,
        verify_certs=False,
        ssl_show_warn=False
    )
    
    if not es_client.ping():
        raise ConnectionError("Failed to connect to Elasticsearch")
    
    print("✅ Connected to Elasticsearch")
    return es_client

def main():
    """Run Eland demonstrations."""
    print("=" * 60)
    print("ELAND DATAFRAMES DEMO - REAL ESTATE PROPERTIES")
    print("=" * 60)
    
    # Connect to Elasticsearch
    es_client = connect_to_elasticsearch()
    
    # 1. Load Properties DataFrame
    print("\n📊 1. LOADING DATA")
    print("-" * 40)
    
    df = ed.DataFrame(
        es_client=es_client,
        es_index_pattern="properties"
    )
    
    print(f"Properties DataFrame loaded:")
    print(f"  • Shape: {df.shape}")
    print(f"  • Columns: {len(df.columns)} total")
    print(f"  • Sample columns: {list(df.columns)[:5]}")
    
    # 2. Basic Operations
    print("\n📋 2. BASIC OPERATIONS")
    print("-" * 40)
    
    print("\nFirst 3 properties:")
    print(df[['listing_id', 'price', 'bedrooms', 'square_feet']].head(3))
    
    print("\nData types (sample):")
    for col in ['price', 'bedrooms', 'property_type']:
        print(f"  • {col}: {df[col].dtype}")
    
    print("\nBasic statistics for price:")
    print(f"  • Mean: ${df['price'].mean():,.2f}")
    print(f"  • Median: ${df['price'].median():,.2f}")
    print(f"  • Min: ${df['price'].min():,.2f}")
    print(f"  • Max: ${df['price'].max():,.2f}")
    
    # 3. Filtering
    print("\n🔍 3. FILTERING DATA")
    print("-" * 40)
    
    # Filter by price range
    filtered = df[(df['price'] >= 500000) & (df['price'] <= 1000000)]
    print(f"\nProperties between $500K-$1M: {len(filtered)}")
    
    # Filter by bedrooms
    three_bed = df[df['bedrooms'] >= 3]
    print(f"Properties with 3+ bedrooms: {len(three_bed)}")
    
    # Complex filter
    luxury = df[(df['price'] > 2000000) & (df['square_feet'] > 2000)]
    print(f"Luxury properties (>$2M, >2000 sqft): {len(luxury)}")
    
    # 4. Aggregations
    print("\n📊 4. AGGREGATIONS")
    print("-" * 40)
    
    print("\nProperty count by type:")
    type_counts = df['property_type'].value_counts()
    for prop_type, count in type_counts.items():
        print(f"  • {prop_type}: {count}")
    
    print("\nAverage price by bedrooms:")
    try:
        avg_by_beds = df.groupby('bedrooms').agg({'price': 'mean'})['price']
        for beds, price in avg_by_beds.items():
            print(f"  • {beds} bedrooms: ${price:,.2f}")
    except:
        # Alternative approach
        for beds in [1, 2, 3, 4, 5]:
            bed_props = df[df['bedrooms'] == beds]
            if len(bed_props) > 0:
                avg_price = bed_props['price'].mean()
                print(f"  • {beds} bedrooms: ${avg_price:,.2f}")
    
    # 5. Sorting (Note: sort_values not available in Eland, using workaround)
    print("\n🔢 5. SORTING")
    print("-" * 40)
    
    print("\nNote: Direct sorting not available in Eland.")
    print("Export to pandas first for sorting operations.")
    
    # 6. Value Counts
    print("\n📈 6. VALUE COUNTS")
    print("-" * 40)
    
    print("\nBedroom distribution:")
    bedroom_counts = df['bedrooms'].value_counts()
    for beds, count in bedroom_counts.items():
        print(f"  • {beds} bedrooms: {count} properties")
    
    # 7. Export to Pandas
    print("\n💾 7. EXPORT TO PANDAS")
    print("-" * 40)
    
    # Export sample to pandas
    sample_df = df.head(10).to_pandas()
    print(f"\nExported {len(sample_df)} rows to pandas DataFrame")
    print(f"Pandas DataFrame columns: {sample_df.columns.tolist()[:5]}...")
    
    # Save to CSV
    csv_file = "property_sample.csv"
    sample_df[['listing_id', 'price', 'bedrooms', 'bathrooms', 'square_feet']].to_csv(csv_file, index=False)
    print(f"Saved sample to {csv_file}")
    
    # 8. Elasticsearch Query DSL
    print("\n🔎 8. ELASTICSEARCH QUERIES")
    print("-" * 40)
    
    # Note: es_query parameter may not be available in all Eland versions
    print("\nNote: Direct ES query integration varies by Eland version.")
    print("For complex queries, use Elasticsearch client directly.")
    
    # 9. Neighborhoods Join Example
    print("\n🔗 9. WORKING WITH MULTIPLE INDICES")
    print("-" * 40)
    
    neighborhoods_df = ed.DataFrame(
        es_client=es_client,
        es_index_pattern="neighborhoods"
    )
    
    print(f"\nNeighborhoods DataFrame:")
    print(f"  • Shape: {neighborhoods_df.shape}")
    print(f"  • Columns: {list(neighborhoods_df.columns)[:5]}")
    
    # Export samples for joining in pandas
    props_sample = df.head(20).to_pandas()
    neighs_sample = neighborhoods_df.to_pandas()
    
    if 'neighborhood_id' in props_sample.columns:
        # Merge dataframes
        merged = props_sample.merge(
            neighs_sample[['neighborhood_id', 'name']],
            on='neighborhood_id',
            how='left'
        )
        print(f"\nMerged data sample:")
        print(merged[['listing_id', 'price', 'neighborhood_id', 'name']].head(3))
    
    print("\n" + "=" * 60)
    print("✅ DEMO COMPLETE")
    print("=" * 60)
    
    print("\n📚 Key Takeaways:")
    print("  • Eland provides pandas-like API for Elasticsearch")
    print("  • Operations execute on server, not locally")
    print("  • Great for large-scale data analysis")
    print("  • Seamless integration with pandas when needed")
    print("  • Supports complex Elasticsearch queries")
    
    print("\n🔗 Resources:")
    print("  • Eland Docs: https://eland.readthedocs.io/")
    print("  • Elastic Docs: https://www.elastic.co/guide/en/elasticsearch/client/eland/current/")
    print("  • GitHub: https://github.com/elastic/eland")

if __name__ == "__main__":
    main()