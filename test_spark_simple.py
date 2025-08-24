#!/usr/bin/env python
"""
Simplest possible Spark test to identify the issue.
"""

import sys
import time

print("Testing basic Spark operations...")

# Test 1: Basic Spark
print("\n1. Creating SparkSession...")
start = time.time()

from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("SimpleTest") \
    .master("local[1]") \
    .config("spark.sql.shuffle.partitions", "1") \
    .getOrCreate()

print(f"   SparkSession created in {time.time() - start:.2f}s")

# Test 2: Simple DataFrame
print("\n2. Creating DataFrame...")
start = time.time()

data = [(1, "a"), (2, "b")]
df = spark.createDataFrame(data, ["id", "text"])
count = df.count()

print(f"   DataFrame created with {count} rows in {time.time() - start:.2f}s")

# Test 3: Simple transformation
print("\n3. Simple transformation...")
start = time.time()

from pyspark.sql.functions import upper
df2 = df.withColumn("text_upper", upper("text"))
df2.show()

print(f"   Transformation completed in {time.time() - start:.2f}s")

# Test 4: Simple UDF
print("\n4. Testing UDF...")
start = time.time()

from pyspark.sql.functions import udf
from pyspark.sql.types import StringType

def simple_udf(text):
    return text + "_processed"

my_udf = udf(simple_udf, StringType())
df3 = df.withColumn("processed", my_udf("text"))
df3.show()

print(f"   UDF completed in {time.time() - start:.2f}s")

# Test 5: Array operations
print("\n5. Testing array operations...")
start = time.time()

from pyspark.sql.functions import array, lit
from pyspark.sql.types import ArrayType

def array_udf(text):
    return [text, text + "2"]

my_array_udf = udf(array_udf, ArrayType(StringType()))
df4 = df.withColumn("array_col", my_array_udf("text"))
df4.show()

print(f"   Array UDF completed in {time.time() - start:.2f}s")

# Test 6: Explode
print("\n6. Testing explode...")
start = time.time()

from pyspark.sql.functions import explode

df5 = df4.select("id", explode("array_col").alias("exploded"))
print(f"   Before count...")
exploded_count = df5.count()
print(f"   Explode created {exploded_count} rows in {time.time() - start:.2f}s")

# Clean up
spark.stop()

print("\n✓ All tests completed successfully!")
sys.exit(0)