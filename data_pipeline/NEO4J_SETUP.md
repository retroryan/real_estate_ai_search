# Neo4j Spark Connector Setup

## Issue
The pipeline is configured for Neo4j but requires the Neo4j Spark Connector JAR file to work properly.

## Solution
To enable Neo4j writing from the Spark pipeline, you need to:

### 1. Download the Neo4j Spark Connector
```bash
# Download the Neo4j Spark Connector (for Spark 3.5+)
wget https://github.com/neo4j/neo4j-spark-connector/releases/download/5.2.0/neo4j-connector-apache-spark_2.12-5.2.0_for_spark_3.jar
```

### 2. Place the JAR in the Spark jars directory
```bash
# Option A: Place in data_pipeline/jars/ directory
mkdir -p data_pipeline/jars
mv neo4j-connector-apache-spark_2.12-5.2.0_for_spark_3.jar data_pipeline/jars/

# Option B: Place in Spark's jars directory
# Find your Spark installation: 
# pip show pyspark | grep Location
# Then copy to: <pyspark_location>/pyspark/jars/
```

### 3. Update Spark Configuration
Add to `data_pipeline/core/spark_session.py` in the SparkConfig:

```python
# Add JAR to Spark config
spark_config.config["spark.jars"] = "data_pipeline/jars/neo4j-connector-apache-spark_2.12-5.2.0_for_spark_3.jar"
```

## Current Status
- ✅ Neo4j Python driver installed (`neo4j==5.28.1`)
- ✅ Neo4j configuration created (`data_pipeline/configs/neo4j_config.yaml`)
- ✅ Neo4j writer code implemented
- ✅ Pipeline configuration updated
- ❌ Neo4j Spark Connector JAR missing

## Alternative: Direct Neo4j Writing
Instead of using the Spark connector, you can write directly to Neo4j using the Python driver:

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", 
                            auth=("neo4j", "scott_tiger"))

def write_to_neo4j(df):
    """Write DataFrame to Neo4j using Python driver."""
    records = df.collect()
    
    with driver.session() as session:
        for record in records:
            session.run("""
                CREATE (p:Property {
                    listing_id: $listing_id,
                    address: $address,
                    price: $price
                })
            """, **record.asDict())
```

This approach bypasses the Spark connector requirement but may be slower for large datasets.