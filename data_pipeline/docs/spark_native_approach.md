# Using Spark's Native Data Source APIs

## Overview

This document explains our approach to using Apache Spark's built-in data source capabilities instead of custom adapters, following Spark best practices.

## Key Design Decisions

### 1. Native JSON Support ✅

**Instead of:** Custom JSON parsing logic
**We use:** Spark's native `DataFrameReader.json()`

```python
# Native Spark JSON reading with schema
df = spark.read \
    .schema(expected_schema) \
    .option("multiLine", True) \
    .option("mode", "PERMISSIVE") \
    .json("path/to/properties*.json")
```

**Benefits:**
- Automatic schema inference
- Built-in error handling modes
- Optimized performance
- Support for wildcards and multiple files
- Native compression support

### 2. Pure Python SQLite Approach ✅

**Instead of:** JDBC with Java dependencies
**We use:** pandas/sqlite3 → Spark DataFrame

```python
# Pure Python approach
import pandas as pd
import sqlite3

conn = sqlite3.connect("data/wikipedia/wikipedia.db")
pdf = pd.read_sql_query(query, conn)
conn.close()

# Convert to Spark DataFrame
df = spark.createDataFrame(pdf)
```

**Benefits:**
- No Java SQLite JDBC driver required
- Simpler deployment (pure Python)
- Easier debugging
- Better for small-to-medium SQLite databases
- Perfect for demo scenarios

### 3. Efficient DataFrame Transformations ✅

**Instead of:** Multiple `withColumn` calls
**We use:** Single `select` with all transformations

```python
# Efficient transformation in one select
df = raw_df.select(
    col("listing_id").alias("entity_id"),
    lit("PROPERTY").alias("entity_type"),
    col("address.city").alias("city"),
    col("address.state").alias("state"),
    # ... all other columns
)
```

**Benefits:**
- Better performance (single pass)
- Avoids query plan explosion
- More readable code
- Follows Spark best practices

## Architecture Benefits

### Simplicity
- Fewer custom abstractions
- Leverages well-tested Spark functionality
- Easier to understand and maintain

### Performance
- Spark's optimized readers
- Catalyst optimizer works better with native operations
- Efficient columnar processing

### Flexibility
- Easy to switch between formats
- Built-in support for various options
- Schema evolution support

## When to Use Custom Adapters

Custom adapters are still valuable when:
1. Complex business logic is required
2. Multiple data sources need coordination
3. Special error handling is needed
4. Data requires significant preprocessing

## Best Practices Applied

1. **Schema Definition**: Always define schemas for better performance
2. **Option Configuration**: Use appropriate reader options
3. **Error Handling**: Leverage Spark's built-in modes (PERMISSIVE, DROPMALFORMED, FAILFAST)
4. **Transformation Efficiency**: Use `select` over multiple `withColumn`
5. **Resource Management**: Proper caching and unpersisting

## Configuration Example

```yaml
data_sources:
  properties_sf:
    path: "real_estate_data/properties_sf.json"
    format: "json"
    options:
      multiLine: true
      mode: "PERMISSIVE"
  
  wikipedia:
    path: "data/wikipedia/wikipedia.db"
    format: "sqlite"
    options:
      use_pandas: true  # Pure Python approach
```

## Summary

By using Spark's native data source APIs and a pure Python approach for SQLite, we achieve:
- ✅ Cleaner, more maintainable code
- ✅ Better performance through optimized readers
- ✅ Simpler deployment (no JDBC drivers)
- ✅ Following Spark best practices
- ✅ Demo-friendly implementation