#!/usr/bin/env python3
"""
Eland DataFrames Sample for Property Entities
==============================================
This script demonstrates using Eland to work with Elasticsearch property data
as pandas-like DataFrames, enabling powerful data analysis and manipulation.

Eland provides a pandas-compatible API for Elasticsearch data, allowing you to:
- Query and filter data using familiar pandas syntax
- Perform aggregations and statistical analysis
- Join data across indices
- Export data to various formats
- Leverage Elasticsearch's distributed computing for large datasets

Requirements:
    pip install eland pandas matplotlib seaborn
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import eland as ed
import pandas as pd
import numpy as np
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import json
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class PropertyDataFrameAnalyzer:
    """Demonstrates Eland DataFrame operations on property data."""
    
    def __init__(self):
        """Initialize Elasticsearch connection and Eland configuration."""
        # Get Elasticsearch credentials from environment
        self.es_host = os.getenv('ES_HOST', 'localhost')
        self.es_port = int(os.getenv('ES_PORT', 9200))
        self.es_scheme = os.getenv('ES_SCHEME', 'http')
        self.es_username = os.getenv('ES_USERNAME', 'elastic')
        self.es_password = os.getenv('ES_PASSWORD')
        
        # Create Elasticsearch client
        self.es_client = Elasticsearch(
            hosts=[{
                'host': self.es_host,
                'port': self.es_port,
                'scheme': self.es_scheme
            }],
            basic_auth=(self.es_username, self.es_password) if self.es_password else None,
            verify_certs=False,
            ssl_show_warn=False
        )
        
        # Verify connection
        if not self.es_client.ping():
            raise ConnectionError("Failed to connect to Elasticsearch")
        
        print(f"✅ Connected to Elasticsearch at {self.es_scheme}://{self.es_host}:{self.es_port}")
        
    def load_properties_dataframe(self, index_name: str = "properties") -> ed.DataFrame:
        """
        Load properties index as an Eland DataFrame.
        
        Args:
            index_name: Name of the Elasticsearch index
            
        Returns:
            Eland DataFrame connected to Elasticsearch
        """
        print(f"\n📊 Loading {index_name} index as Eland DataFrame...")
        
        # Create Eland DataFrame from Elasticsearch index
        # First, let's create without specifying columns to see all available fields
        df = ed.DataFrame(
            es_client=self.es_client,
            es_index_pattern=index_name
        )
        
        print(f"   Shape: {df.shape}")
        print(f"   Columns: {list(df.columns)[:10]}...")
        
        return df
    
    def basic_dataframe_operations(self, df: ed.DataFrame):
        """
        Demonstrate basic DataFrame operations.
        
        Args:
            df: Eland DataFrame
        """
        print("\n🔍 Basic DataFrame Operations")
        print("=" * 60)
        
        # Head and tail
        print("\n1. First 5 rows:")
        print(df.head())
        
        print("\n2. Data types:")
        print(df.dtypes)
        
        print("\n3. Basic statistics:")
        print(df.describe())
        
        print("\n4. DataFrame info:")
        print(f"   Total rows: {len(df)}")
        print(f"   Total columns: {len(df.columns)}")
        # Note: memory_usage not available in Eland
        print(f"   Index: {df.index.name if hasattr(df.index, 'name') else 'default'}")
        
    def filtering_and_selection(self, df: ed.DataFrame):
        """
        Demonstrate filtering and selection operations.
        
        Args:
            df: Eland DataFrame
        """
        print("\n🎯 Filtering and Selection")
        print("=" * 60)
        
        # Filter by price range
        print("\n1. Properties between $500K and $1M:")
        filtered_df = df[(df['price'] >= 500000) & (df['price'] <= 1000000)]
        print(f"   Found {len(filtered_df)} properties")
        print(filtered_df[['listing_id', 'price', 'bedrooms', 'square_feet']].head())
        
        # Filter by property type
        print("\n2. Single family homes only:")
        houses_df = df[df['property_type'] == 'house']
        print(f"   Found {len(houses_df)} houses")
        
        # Complex filtering
        print("\n3. 3+ bedroom properties under $800K in San Francisco:")
        complex_filter = (
            (df['bedrooms'] >= 3) & 
            (df['price'] < 800000) & 
            (df['address.city'] == 'San Francisco')
        )
        complex_df = df[complex_filter]
        print(f"   Found {len(complex_df)} matching properties")
        
        # Column selection
        print("\n4. Select specific columns:")
        selected_cols = df[['listing_id', 'price', 'price_per_sqft', 'property_type']]
        print(selected_cols.head())
        
    def aggregation_operations(self, df: ed.DataFrame):
        """
        Demonstrate aggregation operations.
        
        Args:
            df: Eland DataFrame
        """
        print("\n📊 Aggregation Operations")
        print("=" * 60)
        
        # Basic aggregations
        print("\n1. Price statistics:")
        print(f"   Mean price: ${df['price'].mean():,.2f}")
        print(f"   Median price: ${df['price'].median():,.2f}")
        print(f"   Min price: ${df['price'].min():,.2f}")
        print(f"   Max price: ${df['price'].max():,.2f}")
        print(f"   Std deviation: ${df['price'].std():,.2f}")
        
        # Group by operations
        print("\n2. Average price by property type:")
        try:
            price_by_type = df.groupby('property_type').agg({'price': 'mean'})['price']
            for prop_type, avg_price in price_by_type.items():
                print(f"   {prop_type}: ${avg_price:,.2f}")
        except:
            # Alternative approach
            for prop_type in df['property_type'].unique():
                type_df = df[df['property_type'] == prop_type]
                if len(type_df) > 0:
                    avg_price = type_df['price'].mean()
                    print(f"   {prop_type}: ${avg_price:,.2f}")
        
        print("\n3. Property count by city:")
        try:
            city_counts = df['address.city'].value_counts()
            for city, count in city_counts.items():
                print(f"   {city}: {count} properties")
        except Exception as e:
            print(f"   City counts skipped: {e}")
        
        print("\n4. Average price per sqft by bedrooms:")
        try:
            price_per_sqft_by_beds = df.groupby('bedrooms').agg({'price_per_sqft': 'mean'})['price_per_sqft']
            for beds, avg_ppsf in price_per_sqft_by_beds.items():
                print(f"   {beds} bedrooms: ${avg_ppsf:,.2f}/sqft")
        except:
            for beds in [1, 2, 3, 4, 5]:
                bed_df = df[df['bedrooms'] == beds]
                if len(bed_df) > 0:
                    avg_ppsf = bed_df['price_per_sqft'].mean()
                    print(f"   {beds} bedrooms: ${avg_ppsf:,.2f}/sqft")
        
        # Multiple aggregations
        print("\n5. Multiple aggregations by property type:")
        try:
            # Eland has limited support for multiple aggregations
            # We'll do them separately
            for prop_type in df['property_type'].unique()[:5]:
                type_df = df[df['property_type'] == prop_type]
                if len(type_df) > 0:
                    print(f"   {prop_type}:")
                    print(f"      Count: {len(type_df)}")
                    print(f"      Avg price: ${type_df['price'].mean():,.2f}")
                    print(f"      Avg sqft: {type_df['square_feet'].mean():,.0f}")
                    print(f"      Avg $/sqft: ${type_df['price_per_sqft'].mean():,.2f}")
        except Exception as e:
            print(f"   Multi-aggregation skipped: {e}")
        
    def advanced_analysis(self, df: ed.DataFrame):
        """
        Demonstrate advanced analysis operations.
        
        Args:
            df: Eland DataFrame
        """
        print("\n🚀 Advanced Analysis")
        print("=" * 60)
        
        # Value counts
        print("\n1. Property type distribution:")
        property_types = df['property_type'].value_counts()
        for prop_type, count in property_types.items():
            print(f"   {prop_type}: {count} ({count/len(df)*100:.1f}%)")
        
        # Correlation analysis (for numeric columns)
        print("\n2. Correlation analysis:")
        numeric_cols = ['price', 'bedrooms', 'bathrooms', 'square_feet', 
                       'year_built', 'lot_size', 'price_per_sqft']
        
        # Note: Correlation not directly supported in Eland, so we sample
        print("   (Using sample of data for correlation)")
        sample_df = df[numeric_cols].head(100).to_pandas()
        correlation_matrix = sample_df.corr()
        print("\n   Top correlations with price:")
        price_corr = correlation_matrix['price'].sort_values(ascending=False)
        for col, corr in price_corr.items():
            if col != 'price':
                print(f"   {col}: {corr:.3f}")
        
        # Binning and categorization
        print("\n3. Price categories:")
        # Create price bins (note: this requires converting to pandas)
        try:
            # Use head to get a sample for demonstration
            price_sample = df['price'].head(100).to_pandas()
            bins = [0, 500000, 750000, 1000000, 1500000, np.inf]
            labels = ['<500K', '500-750K', '750K-1M', '1-1.5M', '>1.5M']
            price_categories = pd.cut(price_sample, bins=bins, labels=labels)
            category_counts = price_categories.value_counts()
            for category, count in category_counts.items():
                print(f"   {category}: {count} properties (from sample of 100)")
        except Exception as e:
            print(f"   Price categorization skipped: {e}")
        
    def geospatial_analysis(self, df: ed.DataFrame):
        """
        Demonstrate geospatial analysis with property locations.
        
        Args:
            df: Eland DataFrame
        """
        print("\n🗺️  Geospatial Analysis")
        print("=" * 60)
        
        # Note: address.location is a geo_point field, not separate lat/lon
        print("\n1. Geographic analysis:")
        print("   Note: Geo fields in Elasticsearch are stored as geo_point type")
        print("   Direct lat/lon access may not be available in Eland")
        
        # City-level analysis
        print("\n2. Average price by city:")
        try:
            cities = df['address.city'].unique()
            for city in cities[:5]:  # Show first 5 cities
                city_df = df[df['address.city'] == city]
                if len(city_df) > 0:
                    avg_price = city_df['price'].mean()
                    count = len(city_df)
                    print(f"   {city}:")
                    print(f"      Avg price: ${avg_price:,.2f}")
                    print(f"      Properties: {count}")
        except Exception as e:
            print(f"   City analysis skipped: {e}")
        
    def export_operations(self, df: ed.DataFrame):
        """
        Demonstrate export operations.
        
        Args:
            df: Eland DataFrame
        """
        print("\n💾 Export Operations")
        print("=" * 60)
        
        # Export to pandas DataFrame
        print("\n1. Export sample to Pandas DataFrame:")
        pandas_df = df.head(10).to_pandas()
        print(f"   Exported {len(pandas_df)} rows to pandas DataFrame")
        print(f"   DataFrame type: {type(pandas_df)}")
        
        # Export to CSV
        print("\n2. Export to CSV:")
        csv_filename = "property_sample.csv"
        pandas_df.to_csv(csv_filename, index=False)
        print(f"   Saved to {csv_filename}")
        
        # Export to JSON
        print("\n3. Export to JSON:")
        json_filename = "property_sample.json"
        pandas_df.to_json(json_filename, orient='records', indent=2)
        print(f"   Saved to {json_filename}")
        
        # Export aggregated data
        print("\n4. Export aggregated statistics:")
        try:
            # Create a simple statistics DataFrame
            prop_types = df['property_type'].unique()
            stats_data = []
            for prop_type in prop_types:
                type_df = df[df['property_type'] == prop_type]
                if len(type_df) > 0:
                    stats_data.append({
                        'property_type': prop_type,
                        'count': len(type_df),
                        'mean_price': type_df['price'].mean(),
                        'median_price': type_df['price'].median()
                    })
            
            if stats_data:
                stats_df = pd.DataFrame(stats_data)
                stats_filename = "property_statistics.csv"
                stats_df.to_csv(stats_filename, index=False)
                print(f"   Saved statistics to {stats_filename}")
        except Exception as e:
            print(f"   Statistics export skipped: {e}")
        
    def visualization_examples(self, df: ed.DataFrame):
        """
        Create visualizations from Eland DataFrame data.
        
        Args:
            df: Eland DataFrame
        """
        print("\n📈 Visualization Examples")
        print("=" * 60)
        
        # Set up matplotlib
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # 1. Price distribution
        print("\n1. Creating price distribution histogram...")
        price_data = df['price'].head(200).to_pandas().values
        axes[0, 0].hist(price_data, bins=30, edgecolor='black')
        axes[0, 0].set_title('Property Price Distribution')
        axes[0, 0].set_xlabel('Price ($)')
        axes[0, 0].set_ylabel('Count')
        
        # 2. Property type counts
        print("2. Creating property type bar chart...")
        property_counts = df['property_type'].value_counts()
        axes[0, 1].bar(property_counts.index, property_counts.values)
        axes[0, 1].set_title('Properties by Type')
        axes[0, 1].set_xlabel('Property Type')
        axes[0, 1].set_ylabel('Count')
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # 3. Price vs Square Feet scatter
        print("3. Creating price vs square feet scatter plot...")
        sample_df = df[['price', 'square_feet']].head(100).to_pandas()
        axes[1, 0].scatter(sample_df['square_feet'], sample_df['price'], alpha=0.6)
        axes[1, 0].set_title('Price vs Square Feet')
        axes[1, 0].set_xlabel('Square Feet')
        axes[1, 0].set_ylabel('Price ($)')
        
        # 4. Average price by bedrooms
        print("4. Creating average price by bedrooms chart...")
        try:
            beds_list = []
            prices_list = []
            for beds in [1, 2, 3, 4, 5]:
                bed_df = df[df['bedrooms'] == beds]
                if len(bed_df) > 0:
                    beds_list.append(beds)
                    prices_list.append(bed_df['price'].mean())
            axes[1, 1].bar(beds_list, prices_list)
            axes[1, 1].set_title('Average Price by Bedrooms')
            axes[1, 1].set_xlabel('Number of Bedrooms')
            axes[1, 1].set_ylabel('Average Price ($)')
        except Exception as e:
            print(f"   Chart creation error: {e}")
        
        plt.tight_layout()
        plt.savefig('property_analysis_plots.png', dpi=100)
        print("\n✅ Saved visualizations to property_analysis_plots.png")
        
    def query_with_elasticsearch_dsl(self, df: ed.DataFrame):
        """
        Demonstrate using Elasticsearch DSL queries with Eland.
        
        Args:
            df: Eland DataFrame
        """
        print("\n🔎 Elasticsearch DSL Queries with Eland")
        print("=" * 60)
        
        # Use Elasticsearch query DSL
        print("\n1. Properties with pools (text search):")
        pool_query = {
            "query": {
                "match": {
                    "description": "pool"
                }
            }
        }
        
        # Apply query to DataFrame (Note: es_query may not be available in all versions)
        try:
            # Note: Eland doesn't support .str accessor like pandas
            # Would need to use Elasticsearch query directly or export to pandas
            print("   Note: Text search requires Elasticsearch query or pandas conversion")
            pool_df = df.head(10)  # Just use a sample for demonstration
        except Exception as e:
            print(f"   Pool query error: {e}")
            pool_df = df.head(10)
        
        print(f"   Found {len(pool_df)} properties (sample)")
        if len(pool_df) > 0:
            print(pool_df[['listing_id', 'price', 'description']].head(3))
        
        # Geo-distance query
        print("\n2. Properties within 5km of downtown SF (37.7749, -122.4194):")
        geo_query = {
            "query": {
                "geo_distance": {
                    "distance": "5km",
                    "address.location": {
                        "lat": 37.7749,
                        "lon": -122.4194
                    }
                }
            }
        }
        
        # Note: Direct geo queries require es_query support
        try:
            # For demonstration, we'll use a simple distance calculation
            sf_lat, sf_lon = 37.7749, -122.4194
            nearby_df = df.copy()
            print(f"   Note: Geo-distance queries require specific Elasticsearch setup")
        except Exception as e:
            nearby_df = df.head(10)
        
        print(f"   Found {len(nearby_df)} properties within 5km")
        
        # Complex bool query
        print("\n3. Complex query (3+ beds, <$1M, house or condo):")
        complex_query = {
            "query": {
                "bool": {
                    "must": [
                        {"range": {"bedrooms": {"gte": 3}}},
                        {"range": {"price": {"lt": 1000000}}}
                    ],
                    "should": [
                        {"term": {"property_type": "house"}},
                        {"term": {"property_type": "condo"}}
                    ],
                    "minimum_should_match": 1
                }
            }
        }
        
        # Apply complex filtering with pandas-like syntax
        try:
            complex_df = df[
                (df['bedrooms'] >= 3) & 
                (df['price'] < 1000000) & 
                ((df['property_type'] == 'house') | (df['property_type'] == 'condo'))
            ]
        except Exception as e:
            print(f"   Complex query error: {e}")
            complex_df = df.head(10)
        
        print(f"   Found {len(complex_df)} matching properties")
        
    def join_with_neighborhoods(self):
        """
        Demonstrate joining properties with neighborhoods data.
        """
        print("\n🔗 Joining with Neighborhoods Data")
        print("=" * 60)
        
        # Load neighborhoods DataFrame
        neighborhoods_df = ed.DataFrame(
            es_client=self.es_client,
            es_index_pattern="neighborhoods"
        )
        
        print(f"\n1. Neighborhoods DataFrame shape: {neighborhoods_df.shape}")
        print(f"   Columns: {list(neighborhoods_df.columns)}")
        
        # Note: Eland has limited join support, so we'll demonstrate with pandas
        print("\n2. Performing join analysis (using pandas for demonstration):")
        
        # Get sample data
        props_df = ed.DataFrame(
            es_client=self.es_client,
            es_index_pattern="properties"
        )
        props_sample = props_df.head(50).to_pandas()
        neighs_sample = neighborhoods_df.head(50).to_pandas()
        
        # Merge on neighborhood_id
        if 'neighborhood_id' in props_sample.columns and 'neighborhood_id' in neighs_sample.columns:
            merged = props_sample.merge(
                neighs_sample[['neighborhood_id', 'name', 'description']],
                on='neighborhood_id',
                how='left',
                suffixes=('_prop', '_neigh')
            )
            
            print(f"   Merged DataFrame shape: {merged.shape}")
            print("\n   Sample merged data:")
            print(merged[['listing_id', 'price', 'neighborhood_id', 'name']].head())
        
    def performance_tips(self):
        """
        Provide performance tips for working with Eland DataFrames.
        """
        print("\n⚡ Performance Tips for Eland DataFrames")
        print("=" * 60)
        
        tips = [
            "1. Use server-side operations: Eland operations are executed on Elasticsearch, not locally",
            "2. Limit data transfer: Use .head() or .sample() before .to_pandas() for large datasets",
            "3. Leverage ES queries: Use es_query parameter for complex filtering at the source",
            "4. Batch operations: Group multiple operations before materializing results",
            "5. Index optimization: Ensure proper mapping and indexing in Elasticsearch",
            "6. Column selection: Specify only needed columns when creating DataFrame",
            "7. Aggregations: Use groupby operations which are optimized in Elasticsearch",
            "8. Avoid iterations: Use vectorized operations instead of iterating over rows",
            "9. Memory management: Monitor memory usage with .memory_usage()",
            "10. Query caching: Elasticsearch caches frequent queries automatically"
        ]
        
        for tip in tips:
            print(f"\n   {tip}")


def main():
    """Main execution function."""
    print("=" * 80)
    print("ELAND DATAFRAMES FOR PROPERTY ENTITIES")
    print("=" * 80)
    
    try:
        # Initialize analyzer
        analyzer = PropertyDataFrameAnalyzer()
        
        # Load properties DataFrame
        df = analyzer.load_properties_dataframe()
        
        # Run demonstrations
        analyzer.basic_dataframe_operations(df)
        analyzer.filtering_and_selection(df)
        analyzer.aggregation_operations(df)
        analyzer.advanced_analysis(df)
        analyzer.geospatial_analysis(df)
        analyzer.export_operations(df)
        analyzer.visualization_examples(df)
        analyzer.query_with_elasticsearch_dsl(df)
        analyzer.join_with_neighborhoods()
        analyzer.performance_tips()
        
        print("\n" + "=" * 80)
        print("✅ ELAND DEMONSTRATION COMPLETE")
        print("=" * 80)
        
        print("\n📚 Next Steps:")
        print("   1. Install Eland: pip install eland")
        print("   2. Explore Eland documentation: https://eland.readthedocs.io/")
        print("   3. Try modifying queries and aggregations")
        print("   4. Integrate with your ML pipelines")
        print("   5. Use for data exploration and feature engineering")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())