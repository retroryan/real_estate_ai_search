"""
Basic Neo4j connection test with sample property data.
This is a simple, clean implementation for Phase 1 of Neo4j integration.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType
from dotenv import load_dotenv


class Neo4jBasicTest:
    """Simple test class for Neo4j connection and basic property writes."""
    
    def __init__(self):
        """Initialize test with environment variables and Spark session."""
        # Load environment from parent directory
        parent_env = Path('/Users/ryanknight/projects/temporal/.env')
        local_env = Path('/Users/ryanknight/projects/temporal/real_estate_ai_search/.env')
        
        # Load both env files, local overrides parent
        if parent_env.exists():
            load_dotenv(parent_env)
        if local_env.exists():
            load_dotenv(local_env, override=True)
        
        # Get Neo4j configuration
        self.neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.neo4j_username = os.getenv('NEO4J_USERNAME', 'neo4j')
        self.neo4j_password = os.getenv('NEO4J_PASSWORD', 'scott_tiger')
        self.neo4j_database = os.getenv('NEO4J_DATABASE', 'neo4j')
        
        # Path to Neo4j connector JAR (Scala 2.13 for Spark 4.0)
        self.jar_path = Path('/Users/ryanknight/projects/temporal/real_estate_ai_search/lib/neo4j-connector-apache-spark_2.13-5.3.8_for_spark_3.jar')
        
        # Initialize Spark session
        self.spark = self._create_spark_session()
    
    def _create_spark_session(self) -> SparkSession:
        """Create Spark session with Neo4j connector configured."""
        return SparkSession.builder \
            .appName("Neo4j Basic Test") \
            .config("spark.jars", str(self.jar_path)) \
            .config("spark.sql.adaptive.enabled", "false") \
            .master("local[1]") \
            .getOrCreate()
    
    def create_sample_properties(self) -> DataFrame:
        """Create sample property data for testing."""
        # Define schema for properties
        schema = StructType([
            StructField("id", StringType(), False),
            StructField("address", StringType(), False),
            StructField("city", StringType(), False),
            StructField("state", StringType(), False),
            StructField("price", IntegerType(), False),
            StructField("bedrooms", IntegerType(), False),
            StructField("bathrooms", DoubleType(), False),
            StructField("sqft", IntegerType(), False),
            StructField("latitude", DoubleType(), False),
            StructField("longitude", DoubleType(), False)
        ])
        
        # Sample property data
        data = [
            ("prop_001", "123 Main St", "San Francisco", "CA", 850000, 2, 1.5, 1200, 37.7749, -122.4194),
            ("prop_002", "456 Oak Ave", "San Francisco", "CA", 1250000, 3, 2.0, 1800, 37.7751, -122.4180),
            ("prop_003", "789 Pine Rd", "Park City", "UT", 950000, 3, 2.5, 2200, 40.6461, -111.4980),
            ("prop_004", "321 Elm Dr", "Park City", "UT", 1750000, 4, 3.5, 3500, 40.6463, -111.4975),
            ("prop_005", "654 Market St", "San Francisco", "CA", 2100000, 3, 2.0, 2400, 37.7745, -122.4189)
        ]
        
        return self.spark.createDataFrame(data, schema)
    
    def clear_database(self) -> bool:
        """Clear all nodes and relationships from Neo4j (demo database only)."""
        try:
            # Create a simple DataFrame for executing Cypher query
            clear_df = self.spark.createDataFrame([("clear",)], ["action"])
            
            # Use query option to delete all nodes and relationships
            clear_df.write \
                .format("org.neo4j.spark.DataSource") \
                .mode("overwrite") \
                .option("url", self.neo4j_uri) \
                .option("authentication.basic.username", self.neo4j_username) \
                .option("authentication.basic.password", self.neo4j_password) \
                .option("database", self.neo4j_database) \
                .option("query", "MATCH (n) DETACH DELETE n RETURN count(n) as deleted") \
                .save()
            
            print("✅ Database cleared successfully")
            return True
        except Exception as e:
            print(f"⚠️  Warning: Could not clear database: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test basic connection to Neo4j."""
        try:
            # Create test DataFrame
            test_df = self.spark.createDataFrame([(1, "test")], ["id", "data"])
            
            # Test connection with a simple query
            result_df = self.spark.read \
                .format("org.neo4j.spark.DataSource") \
                .option("url", self.neo4j_uri) \
                .option("authentication.basic.username", self.neo4j_username) \
                .option("authentication.basic.password", self.neo4j_password) \
                .option("database", self.neo4j_database) \
                .option("query", "RETURN 1 as test") \
                .load()
            
            result = result_df.collect()
            if result and result[0]["test"] == 1:
                print("✅ Neo4j connection successful")
                return True
            return False
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def write_properties(self, properties_df: DataFrame) -> bool:
        """Write property nodes to Neo4j."""
        try:
            # Write properties as nodes
            properties_df.write \
                .format("org.neo4j.spark.DataSource") \
                .mode("overwrite") \
                .option("url", self.neo4j_uri) \
                .option("authentication.basic.username", self.neo4j_username) \
                .option("authentication.basic.password", self.neo4j_password) \
                .option("database", self.neo4j_database) \
                .option("labels", ":Property") \
                .option("node.keys", "id") \
                .save()
            
            print(f"✅ Successfully wrote {properties_df.count()} property nodes")
            return True
        except Exception as e:
            print(f"❌ Failed to write properties: {e}")
            return False
    
    def verify_properties(self) -> bool:
        """Read back and verify property nodes from Neo4j."""
        try:
            # Read properties back from Neo4j
            result_df = self.spark.read \
                .format("org.neo4j.spark.DataSource") \
                .option("url", self.neo4j_uri) \
                .option("authentication.basic.username", self.neo4j_username) \
                .option("authentication.basic.password", self.neo4j_password) \
                .option("database", self.neo4j_database) \
                .option("labels", "Property") \
                .load()
            
            count = result_df.count()
            print(f"✅ Read {count} property nodes from Neo4j")
            
            # Show sample data
            print("\nSample properties in Neo4j:")
            result_df.select("id", "address", "city", "price").show(5, truncate=False)
            
            return count == 5
        except Exception as e:
            print(f"❌ Failed to verify properties: {e}")
            return False
    
    def run_test(self) -> bool:
        """Run complete test sequence."""
        print("\n" + "="*60)
        print("NEO4J BASIC CONNECTION TEST - PHASE 1")
        print("="*60)
        
        # Test sequence
        steps = [
            ("Testing connection", self.test_connection),
            ("Clearing database", self.clear_database),
            ("Creating sample properties", lambda: self.create_sample_properties() is not None),
            ("Writing properties to Neo4j", lambda: self.write_properties(self.create_sample_properties())),
            ("Verifying properties", self.verify_properties)
        ]
        
        all_passed = True
        for step_name, step_func in steps:
            print(f"\n{step_name}...")
            if not step_func():
                all_passed = False
                print(f"  ❌ {step_name} failed")
                break
            print(f"  ✅ {step_name} passed")
        
        print("\n" + "="*60)
        if all_passed:
            print("✅ ALL TESTS PASSED - Phase 1 Complete!")
            print("\nYou can now view the properties in Neo4j Browser:")
            print("  1. Open http://localhost:7474")
            print("  2. Login with neo4j/scott_tiger")
            print("  3. Run: MATCH (p:Property) RETURN p LIMIT 10")
        else:
            print("❌ TESTS FAILED - Please check the errors above")
        print("="*60)
        
        return all_passed
    
    def cleanup(self):
        """Clean up Spark session."""
        if self.spark:
            self.spark.stop()


def main():
    """Main entry point for the test."""
    test = None
    try:
        test = Neo4jBasicTest()
        success = test.run_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)
    finally:
        if test:
            test.cleanup()


if __name__ == "__main__":
    main()