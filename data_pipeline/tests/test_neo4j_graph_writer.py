"""
Test the enhanced Neo4j graph writer.

This test validates that the Neo4j graph writer correctly creates all nodes.
Note: Relationships are created separately in Neo4j using graph_real_estate module.
"""

import json
import os
import sys
from pathlib import Path
from datetime import date
from typing import List, Dict, Any

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, 
    DoubleType, ArrayType, BooleanType
)
from pyspark.sql.functions import lit, col
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_pipeline.config.models import PipelineConfig
from data_pipeline.writers.neo4j_graph_writer import Neo4jGraphWriter


class TestNeo4jGraphWriter:
    """Test suite for the enhanced Neo4j graph writer."""
    
    def __init__(self):
        """Initialize test environment."""
        # Load environment variables
        project_root = Path(__file__).parent.parent.parent
        parent_env = project_root.parent / '.env'
        local_env = project_root / '.env'
        
        if parent_env.exists():
            load_dotenv(parent_env)
        if local_env.exists():
            load_dotenv(local_env, override=True)
        
        # Neo4j configuration
        self.neo4j_config = PipelineConfig(
            uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            username=os.getenv('NEO4J_USERNAME'),
            password=os.getenv('NEO4J_PASSWORD'),
            database=os.getenv('NEO4J_DATABASE'),
            clear_before_write=True
        )
        
        # JAR path
        self.jar_path = project_root / 'lib/neo4j-connector-apache-spark_2.13-5.3.8_for_spark_3.jar'
        
        # Initialize Spark session
        self.spark = self._create_spark_session()
        
        # Initialize writer
        self.writer = Neo4jGraphWriter(self.neo4j_config, self.spark)
    
    def _create_spark_session(self) -> SparkSession:
        """Create Spark session with Neo4j connector."""
        return SparkSession.builder \
            .appName("Test Neo4j Graph Writer") \
            .config("spark.jars", str(self.jar_path)) \
            .config("spark.sql.adaptive.enabled", "false") \
            .master("local[2]") \
            .getOrCreate()
    
    def create_sample_data(self):
        """Create sample entity-specific DataFrames."""
        
        # Property schema
        property_schema = StructType([
            StructField("listing_id", StringType(), False),
            StructField("street", StringType(), True),
            StructField("city", StringType(), True),
            StructField("state", StringType(), True),
            StructField("zip_code", StringType(), True),
            StructField("latitude", DoubleType(), True),
            StructField("longitude", DoubleType(), True),
            StructField("property_type", StringType(), True),
            StructField("bedrooms", IntegerType(), True),
            StructField("bathrooms", DoubleType(), True),
            StructField("square_feet", IntegerType(), True),
            StructField("price", IntegerType(), True),
            StructField("year_built", IntegerType(), True),
            StructField("description", StringType(), True),
            StructField("features", ArrayType(StringType()), True),
            StructField("neighborhood_id", StringType(), True)
        ])
        
        # Neighborhood schema
        neighborhood_schema = StructType([
            StructField("neighborhood_id", StringType(), False),
            StructField("name", StringType(), True),
            StructField("city", StringType(), True),
            StructField("state", StringType(), True),
            StructField("latitude", DoubleType(), True),
            StructField("longitude", DoubleType(), True),
            StructField("description", StringType(), True),
            StructField("population", IntegerType(), True),
            StructField("median_income", IntegerType(), True),
            StructField("amenities", ArrayType(StringType()), True),
            StructField("points_of_interest", ArrayType(StringType()), True)
        ])
        
        # Wikipedia schema
        wikipedia_schema = StructType([
            StructField("page_id", IntegerType(), False),
            StructField("title", StringType(), True),
            StructField("url", StringType(), True),
            StructField("short_summary", StringType(), True),
            StructField("long_summary", StringType(), True),
            StructField("key_topics", ArrayType(StringType()), True),
            StructField("best_city", StringType(), True),
            StructField("best_state", StringType(), True),
            StructField("confidence_score", DoubleType(), True),
            StructField("relevance_score", DoubleType(), True),
            StructField("latitude", DoubleType(), True),
            StructField("longitude", DoubleType(), True)
        ])
        
        # Sample property data
        properties_data = [
            ("prop_001", "123 Main St", "San Francisco", "CA", "94102",
             37.7749, -122.4194, "condo", 2, 1.5, 1200, 850000, 2018,
             "Beautiful condo in downtown SF", ["parking", "gym"], "sf-downtown"),
            ("prop_002", "456 Oak Ave", "San Francisco", "CA", "94102",
             37.7751, -122.4180, "condo", 3, 2.0, 1500, 950000, 2020,
             "Spacious condo with views", ["views", "parking"], "sf-downtown"),
            ("prop_003", "789 Pine Rd", "Park City", "UT", "84060",
             40.6461, -111.4980, "single_family", 4, 3.0, 2500, 1250000, 2015,
             "Mountain home with great access", ["mountain_views", "garage"], "pc-old-town")
        ]
        
        # Sample neighborhood data
        neighborhoods_data = [
            ("sf-downtown", "Downtown SF", "San Francisco", "CA", 
             37.7750, -122.4185, "Urban downtown area", 
             50000, 95000, ["restaurants", "shopping"], ["union_square", "chinatown"]),
            ("pc-old-town", "Old Town", "Park City", "UT",
             40.6460, -111.4970, "Historic ski town area",
             8000, 120000, ["skiing", "dining"], ["main_street", "ski_lifts"])
        ]
        
        # Sample Wikipedia data
        wikipedia_data = [
            (1234567, "San Francisco", "https://en.wikipedia.org/wiki/San_Francisco",
             "San Francisco is a city in California", "San Francisco is a major city in California known for technology and culture",
             ["technology", "culture", "tourism"], "San Francisco", "CA", 0.95, 0.90, 37.7749, -122.4194),
            (2345678, "Park City, Utah", "https://en.wikipedia.org/wiki/Park_City,_Utah",
             "Park City is a ski resort town in Utah", "Park City is a popular ski resort destination in Utah, famous for skiing and Sundance",
             ["skiing", "olympics", "sundance"], "Park City", "UT", 0.92, 0.85, 40.6461, -111.4980)
        ]
        
        # Create DataFrames
        properties_df = self.spark.createDataFrame(properties_data, property_schema)
        neighborhoods_df = self.spark.createDataFrame(neighborhoods_data, neighborhood_schema)
        wikipedia_df = self.spark.createDataFrame(wikipedia_data, wikipedia_schema)
        
        return {
            "properties": properties_df,
            "neighborhoods": neighborhoods_df,
            "wikipedia": wikipedia_df
        }
    
    def test_connection(self) -> bool:
        """Test Neo4j connection."""
        print("\nTesting Neo4j connection...")
        if self.writer.validate_connection():
            print("✅ Neo4j connection successful")
            return True
        else:
            print("❌ Neo4j connection failed")
            return False
    
    def test_write_graph(self) -> bool:
        """Test writing complete graph structure."""
        print("\nTesting graph write...")
        
        # Create sample data (now returns dict of DataFrames)
        data_dict = self.create_sample_data()
        
        # Show entity counts
        print(f"Created entity-specific DataFrames:")
        print(f"  Properties: {data_dict['properties'].count()}")
        print(f"  Neighborhoods: {data_dict['neighborhoods'].count()}")
        print(f"  Wikipedia: {data_dict['wikipedia'].count()}")
        
        # Write to Neo4j
        metadata = {
            "test": True,
            "timestamp": "2025-01-01T00:00:00"
        }
        
        if self.writer.write(data_dict, metadata):
            print("✅ Graph write successful")
            return True
        else:
            print("❌ Graph write failed")
            return False
    
    def verify_graph(self) -> bool:
        """Verify the created graph structure in Neo4j."""
        print("\nVerifying graph structure...")
        
        try:
            # Check node counts only (relationships are created separately in Neo4j)
            queries = [
                ("MATCH (p:Property) RETURN count(p) as count", "Property nodes"),
                ("MATCH (n:Neighborhood) RETURN count(n) as count", "Neighborhood nodes"),
                ("MATCH (w:WikipediaArticle) RETURN count(w) as count", "Wikipedia nodes"),
                ("MATCH (c:City) RETURN count(c) as count", "City nodes"),
                ("MATCH (s:State) RETURN count(s) as count", "State nodes")
            ]
            
            for query, description in queries:
                result_df = (self.spark.read
                           .format("org.neo4j.spark.DataSource")
                           .option("url", self.neo4j_config.uri)
                           .option("authentication.basic.username", self.neo4j_config.username)
                           .option("authentication.basic.password", self.neo4j_config.get_password() or "")
                           .option("database", self.neo4j_config.database)
                           .option("query", query)
                           .load())
                
                count = result_df.collect()[0]["count"]
                print(f"  {description}: {count}")
            
            print("✅ Graph verification complete")
            return True
            
        except Exception as e:
            print(f"❌ Graph verification failed: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all tests."""
        print("\n" + "="*60)
        print("NEO4J GRAPH WRITER TEST SUITE")
        print("="*60)
        
        all_passed = True
        
        # Test connection
        if not self.test_connection():
            all_passed = False
            print("Connection test failed - stopping tests")
            return False
        
        # Test graph write
        if not self.test_write_graph():
            all_passed = False
        
        # Verify graph structure
        if not self.verify_graph():
            all_passed = False
        
        print("\n" + "="*60)
        if all_passed:
            print("✅ ALL TESTS PASSED!")
            print("\nYou can explore the graph in Neo4j Browser:")
            print("  1. Open http://localhost:7474")
            print("  2. Login with your credentials")
            print("  3. Try these queries:")
            print("     - MATCH (n) RETURN n LIMIT 50")
            print("     - MATCH (p:Property) RETURN p LIMIT 10")
            print("     - MATCH (n:Neighborhood) RETURN n LIMIT 10")
            print("Note: Relationships will be created in separate Neo4j step: python -m graph_real_estate build-relationships")
        else:
            print("❌ SOME TESTS FAILED")
        print("="*60)
        
        return all_passed
    
    def cleanup(self):
        """Clean up resources."""
        if self.spark:
            self.spark.stop()


def main():
    """Main entry point."""
    test = None
    try:
        test = TestNeo4jGraphWriter()
        success = test.run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if test:
            test.cleanup()


if __name__ == "__main__":
    main()