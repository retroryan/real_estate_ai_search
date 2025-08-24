# Neo4j Spark Connector Setup Guide

This guide explains how to build and configure the Neo4j Spark Connector for use with the data_pipeline multi-destination writer.

## Prerequisites

- Java 8 or 11 (required for building the connector)
- Maven 3.6+ (for building from source)
- Apache Spark 3.x installed
- Neo4j 4.x or 5.x instance (local or cloud)
- Python 3.8+ with PySpark

## Option 1: Using Pre-built JAR (Recommended)

### Download from Maven Central

The easiest way is to download the pre-built JAR from Maven Central:

```bash
# For Spark 3.x with Scala 2.12
wget https://repo1.maven.org/maven2/org/neo4j/neo4j-connector-apache-spark_2.12/5.3.0_for_spark_3/neo4j-connector-apache-spark_2.12-5.3.0_for_spark_3.jar

# Place in Spark jars directory
cp neo4j-connector-apache-spark_2.12-5.3.0_for_spark_3.jar $SPARK_HOME/jars/
```

### Or use with spark-submit

```bash
spark-submit \
  --packages org.neo4j:neo4j-connector-apache-spark_2.12:5.3.0_for_spark_3 \
  your_application.py
```

## Option 2: Building from Source

### Clone the Repository

```bash
# Navigate to the temporal directory
cd /Users/ryanknight/projects/temporal

# The neo4j-spark directory should already exist
cd neo4j-spark/neo4j-spark-connector
```

### Build the JAR

```bash
# Build for Spark 3 with Scala 2.12
./maven-release.sh package 2.12

# The JAR will be created at:
# spark-3/target/neo4j-connector-apache-spark_2.12-<version>_for_spark_3.jar
```

### Install to Local Maven Repository

```bash
# Install to local Maven repository for easier use
mvn install:install-file \
  -Dfile=spark-3/target/neo4j-connector-apache-spark_2.12-5.3.0_for_spark_3.jar \
  -DgroupId=org.neo4j \
  -DartifactId=neo4j-connector-apache-spark_2.12 \
  -Dversion=5.3.0_for_spark_3 \
  -Dpackaging=jar
```

## Setting Up for the Data Pipeline

### 1. Configure Spark Session

Add the JAR to your Spark configuration in `data_pipeline/config.yaml`:

```yaml
spark:
  app_name: "RealEstateDataPipeline"
  master: "local[*]"
  config:
    spark.jars: "/path/to/neo4j-connector-apache-spark_2.12-5.3.0_for_spark_3.jar"
    # Or use Maven coordinates
    spark.jars.packages: "org.neo4j:neo4j-connector-apache-spark_2.12:5.3.0_for_spark_3"
```

### 2. Set Up Neo4j Database

#### Local Neo4j Instance

```bash
# Using Docker
docker run \
  --name neo4j-demo \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  -e NEO4J_PLUGINS='["apoc"]' \
  neo4j:5-community

# Or using Neo4j Desktop
# Download from: https://neo4j.com/download/
```

#### Neo4j Aura (Cloud)

1. Create a free instance at https://neo4j.com/cloud/aura-free/
2. Note the connection URI (e.g., `neo4j+s://xxxxxxxx.databases.neo4j.io`)
3. Save the generated password

### 3. Configure Pipeline for Neo4j

Update `data_pipeline/config.yaml`:

```yaml
output_destinations:
  enabled_destinations:
    - "parquet"
    - "neo4j"  # Enable Neo4j writer
  
  neo4j:
    enabled: true
    uri: "bolt://localhost:7687"  # For local
    # uri: "neo4j+s://xxxxxxxx.databases.neo4j.io"  # For Aura
    username: "neo4j"
    password: "${NEO4J_PASSWORD}"
    database: "neo4j"
    transaction_size: 1000
    clear_before_write: true
```

### 4. Set Environment Variables

```bash
# Create or update the parent .env file at /Users/ryanknight/projects/temporal/.env
# This file is shared across all projects in the temporal directory
cat >> /Users/ryanknight/projects/temporal/.env << EOF
# Neo4j Configuration
NEO4J_PASSWORD=your-password-here

# Elasticsearch Configuration (if using)
ES_PASSWORD=your-es-password-here

# Other API Keys
OPENAI_API_KEY=your-openai-key
VOYAGE_API_KEY=your-voyage-key
EOF

# For development/testing
export SPARK_HOME="/path/to/spark"
export PYTHONPATH="$PYTHONPATH:/Users/ryanknight/projects/temporal/real_estate_ai_search"
```

**Note**: The data_pipeline automatically loads environment variables from the parent `/Users/ryanknight/projects/temporal/.env` file, allowing credential sharing across all temporal projects.

### 5. Add to requirements.txt (if needed)

```txt
# Add to data_pipeline/requirements.txt
pyspark>=3.0.0
```

## Running the Pipeline with Neo4j

### Test Configuration

```bash
# Test configuration loading
python -m data_pipeline.examples.test_configuration
```

### Run Pipeline

```bash
# The pipeline will automatically load credentials from /Users/ryanknight/projects/temporal/.env
python -m data_pipeline

# Or override with environment variable
NEO4J_PASSWORD=different-password python -m data_pipeline
```

### Verify in Neo4j

After running the pipeline, verify the data in Neo4j:

```cypher
// Count nodes by label
MATCH (n:Property) RETURN count(n) as property_count;
MATCH (n:Neighborhood) RETURN count(n) as neighborhood_count;
MATCH (n:WikipediaArticle) RETURN count(n) as wikipedia_count;

// Sample property nodes
MATCH (p:Property) 
RETURN p 
LIMIT 10;

// Check all labels
CALL db.labels() YIELD label
RETURN label;
```

## Troubleshooting

### JAR Not Found

If Spark cannot find the Neo4j connector JAR:

```bash
# Check SPARK_HOME is set
echo $SPARK_HOME

# Verify JAR is in classpath
ls -la $SPARK_HOME/jars/ | grep neo4j

# Or explicitly add to spark-submit
spark-submit --jars /path/to/neo4j-connector.jar ...
```

### Connection Issues

```python
# Test connection in PySpark shell
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("Neo4j Test") \
    .config("spark.jars.packages", "org.neo4j:neo4j-connector-apache-spark_2.12:5.3.0_for_spark_3") \
    .getOrCreate()

# Test read
df = spark.read \
    .format("org.neo4j.spark.DataSource") \
    .option("url", "bolt://localhost:7687") \
    .option("authentication.basic.username", "neo4j") \
    .option("authentication.basic.password", "password123") \
    .option("query", "RETURN 1 as test") \
    .load()

df.show()
```

### Version Compatibility

| Spark Version | Scala Version | Neo4j Connector Version |
|--------------|---------------|-------------------------|
| 3.5.x        | 2.12          | 5.3.0_for_spark_3      |
| 3.4.x        | 2.12          | 5.2.0_for_spark_3      |
| 3.3.x        | 2.12          | 5.1.0_for_spark_3      |

### Memory Issues

For large datasets, adjust Spark memory settings:

```yaml
# In config.yaml
spark:
  memory: "8g"
  executor_memory: "4g"
  config:
    spark.driver.maxResultSize: "2g"
    spark.sql.shuffle.partitions: 100
```

## Additional Resources

- [Neo4j Spark Connector Documentation](https://neo4j.com/docs/spark/current/)
- [Neo4j Spark Connector GitHub](https://github.com/neo4j/neo4j-spark-connector)
- [PySpark with Neo4j Examples](https://github.com/neo4j/neo4j-spark-connector/tree/main/examples)
- [Neo4j Aura Free Tier](https://neo4j.com/cloud/aura-free/)

## Quick Test Script

Save as `test_neo4j_spark.py`:

```python
from pyspark.sql import SparkSession
import os

# Create Spark session with Neo4j connector
spark = SparkSession.builder \
    .appName("Neo4j Test") \
    .config("spark.jars.packages", "org.neo4j:neo4j-connector-apache-spark_2.12:5.3.0_for_spark_3") \
    .getOrCreate()

# Test data
data = [
    (1, "Property", "123 Main St", 500000),
    (2, "Property", "456 Oak Ave", 750000),
    (3, "Property", "789 Pine Rd", 600000)
]
columns = ["id", "entity_type", "address", "price"]

df = spark.createDataFrame(data, columns)

# Write to Neo4j
df.write \
    .format("org.neo4j.spark.DataSource") \
    .mode("overwrite") \
    .option("url", "bolt://localhost:7687") \
    .option("authentication.basic.username", "neo4j") \
    .option("authentication.basic.password", os.getenv("NEO4J_PASSWORD", "password123")) \
    .option("labels", ":TestProperty") \
    .option("node.keys", "id") \
    .save()

print("✅ Successfully wrote test data to Neo4j")

# Read back from Neo4j
result_df = spark.read \
    .format("org.neo4j.spark.DataSource") \
    .option("url", "bolt://localhost:7687") \
    .option("authentication.basic.username", "neo4j") \
    .option("authentication.basic.password", os.getenv("NEO4J_PASSWORD", "password123")) \
    .option("labels", "TestProperty") \
    .load()

print(f"✅ Read {result_df.count()} nodes from Neo4j")
result_df.show()

spark.stop()
```

Run with:
```bash
python test_neo4j_spark.py
```