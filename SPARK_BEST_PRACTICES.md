# Apache Spark Best Practices Guide

## Table of Contents
1. [Core Principles](#core-principles)
2. [Understanding Lazy Evaluation](#understanding-lazy-evaluation)
3. [Action vs Transformation Guidelines](#action-vs-transformation-guidelines)
4. [Count Operations Best Practices](#count-operations-best-practices)
5. [Broadcasting Best Practices](#broadcasting-best-practices)
6. [Caching and Persistence](#caching-and-persistence)
7. [Join Optimization](#join-optimization)
8. [DataFrame Operations](#dataframe-operations)
9. [Memory Management](#memory-management)
10. [Performance Monitoring](#performance-monitoring)
11. [Common Anti-Patterns](#common-anti-patterns)
12. [Code Quality Guidelines](#code-quality-guidelines)

## Core Principles

### 1. Embrace Lazy Evaluation
- **Principle**: Spark's power comes from lazy evaluation - transformations are not executed until an action is called
- **Benefit**: Allows Spark to optimize the entire execution plan
- **Practice**: Chain transformations and trigger evaluation only when necessary

### 2. Minimize Actions
- **Principle**: Every action triggers computation of the entire lineage
- **Benefit**: Reduces redundant computations and improves performance
- **Practice**: Batch operations and use single actions for multiple results

### 3. Think in Sets
- **Principle**: Spark works best with set-based operations, not row-by-row processing
- **Benefit**: Leverages distributed computing effectively
- **Practice**: Use DataFrame operations instead of iterating over rows

## Understanding Lazy Evaluation

### What Triggers Evaluation?

**Actions (force evaluation):**
```python
# These force immediate computation
df.count()          # Counts all rows
df.collect()        # Brings all data to driver
df.show()           # Shows sample rows
df.take(n)          # Takes first n rows
df.first()          # Gets first row
df.write.parquet()  # Writes to disk
df.foreach()        # Applies function to each row
```

**Transformations (lazy):**
```python
# These do NOT trigger computation
df.filter()         # Filters rows
df.select()         # Selects columns
df.withColumn()     # Adds/modifies columns
df.join()           # Joins DataFrames
df.groupBy()        # Groups data
df.orderBy()        # Sorts data
df.distinct()       # Gets unique rows
```

### Best Practice Example

❌ **Bad: Multiple actions forcing evaluation**
```python
def process_data(df):
    logger.info(f"Processing {df.count()} records")  # Action 1
    
    filtered_df = df.filter(col("status") == "active")
    logger.info(f"Active records: {filtered_df.count()}")  # Action 2
    
    enriched_df = filtered_df.withColumn("processed", lit(True))
    logger.info(f"Enriched records: {enriched_df.count()}")  # Action 3
    
    return enriched_df
```

✅ **Good: Single action at the end**
```python
def process_data(df):
    logger.info("Processing data...")
    
    filtered_df = df.filter(col("status") == "active")
    enriched_df = filtered_df.withColumn("processed", lit(True))
    
    # Single action at the end
    enriched_df.write.parquet(output_path)
    logger.info("✓ Data processing complete")
    
    return enriched_df
```

## Count Operations Best Practices

### When to Use Count

✅ **Appropriate Uses:**
```python
# 1. Data validation at pipeline end
result_df = pipeline.run()
final_count = result_df.count()
if final_count == 0:
    raise ValueError("Pipeline produced no results")

# 2. Aggregation operations
city_counts = df.groupBy("city").agg(
    count("*").alias("property_count")
)

# 3. After writes to report success
df.write.parquet(path)
written_count = spark.read.parquet(path).count()
logger.info(f"Successfully wrote {written_count} records")
```

❌ **Inappropriate Uses:**
```python
# 1. Logging during processing
def enrich_data(df):
    initial_count = df.count()  # Unnecessary evaluation
    enriched = df.withColumn("new_field", expr("..."))
    final_count = enriched.count()  # Another unnecessary evaluation
    logger.info(f"Enriched {initial_count} -> {final_count}")
    return enriched

# 2. Conditional logic that doesn't need exact count
if df.count() > 0:  # Forces full scan
    process(df)
# Better: use limit
if df.limit(1).count() > 0:  # Only checks for at least 1 row
    process(df)

# 3. Progress tracking in loops
for batch in batches:
    processed = transform(batch)
    logger.info(f"Processed {processed.count()}")  # Multiple evaluations
```

### Count Alternatives

```python
# Instead of count for existence checking
if df.count() > 0:  # Bad - full scan
if not df.isEmpty():  # Better - stops at first row
if df.limit(1).count() > 0:  # Also good

# Instead of count for logging
logger.info(f"Processed {df.count()} records")  # Bad
logger.info("✓ Data processed successfully")  # Good

# Use explain() for debugging instead of count
df.explain(True)  # Shows execution plan without evaluation
```

## Broadcasting Best Practices

### When to Broadcast

✅ **Good Candidates for Broadcasting:**
- Lookup tables (< 1GB)
- Configuration data
- Reference data that fits in memory
- Small dimension tables in joins

❌ **Bad Candidates for Broadcasting:**
- Large fact tables
- Data that changes frequently
- Tables larger than driver memory
- Streaming DataFrames

### Broadcasting Patterns

```python
# Manual broadcasting
from pyspark.sql.functions import broadcast

# ✅ Good: Broadcast small lookup table
small_lookup = spark.read.parquet("lookup_table")  # < 100MB
result = large_df.join(
    broadcast(small_lookup),
    "join_key"
)

# ❌ Bad: Broadcasting large table
large_table = spark.read.parquet("fact_table")  # > 1GB
result = small_df.join(
    broadcast(large_table),  # Will cause OOM
    "join_key"
)

# ✅ Good: Selective column broadcasting
location_broadcast = spark.sparkContext.broadcast(
    locations_df.select("city", "state", "county").collect()
)

# ❌ Bad: Broadcasting entire DataFrame
all_data_broadcast = spark.sparkContext.broadcast(
    full_df.collect()  # Includes unnecessary columns
)
```

### Broadcast Configuration

```python
# Set automatic broadcast threshold (default 10MB)
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", 104857600)  # 100MB

# Disable auto-broadcast for specific join
result = df1.join(df2.hint("shuffle"), "key")

# Force broadcast even if over threshold
result = df1.join(df2.hint("broadcast"), "key")
```

## Caching and Persistence

### When to Cache

✅ **Cache When:**
```python
# 1. DataFrame used multiple times
neighborhoods_df = load_neighborhoods().cache()
properties_with_hood = properties.join(neighborhoods_df, "hood_id")
stats_by_hood = neighborhoods_df.groupBy("city").count()

# 2. After expensive operations before branching
enriched_df = (
    raw_df
    .join(lookup1, "key1")
    .join(lookup2, "key2")
    .withColumn("complex_calc", expensive_udf(col("value")))
    .cache()
)
result1 = enriched_df.filter(col("type") == "A")
result2 = enriched_df.filter(col("type") == "B")

# 3. Iterative algorithms
df = initial_df.cache()
for i in range(iterations):
    df = transform(df).cache()
    df.count()  # Force evaluation each iteration
```

❌ **Don't Cache When:**
```python
# 1. DataFrame used only once
df = load_data().cache()  # Unnecessary
result = df.filter(...).write.parquet(...)

# 2. Right before writing
df.cache().write.parquet(...)  # Cache is never reused

# 3. Very large DataFrames that don't fit in memory
huge_df.cache()  # Will spill to disk, negating benefits
```

### Cache Cleanup

```python
# Always unpersist when done
try:
    df = expensive_operation().cache()
    # Use df multiple times
    result1 = process1(df)
    result2 = process2(df)
finally:
    df.unpersist()  # Free memory

# In pipeline cleanup
def cleanup_pipeline(cached_dfs):
    for df in cached_dfs:
        if df is not None:
            df.unpersist()
```

## Join Optimization

### Join Strategies

```python
# 1. Broadcast join for small tables
result = large_df.join(
    broadcast(small_df),
    "key"
)

# 2. Sort-merge join for large tables
spark.conf.set("spark.sql.join.preferSortMergeJoin", "true")
result = large_df1.join(large_df2, "key")

# 3. Bucketed joins for repeated joins
df.write.bucketBy(100, "key").sortBy("key").saveAsTable("bucketed_table")

# 4. Salted joins for skewed data
def salt_join(df1, df2, key_col, salt_range=100):
    salted_df1 = df1.withColumn(
        "salt", (rand() * salt_range).cast("int")
    ).withColumn(
        "salted_key", concat(col(key_col), lit("_"), col("salt"))
    )
    
    exploded_df2 = df2.select(
        "*",
        explode(array([lit(i) for i in range(salt_range)])).alias("salt")
    ).withColumn(
        "salted_key", concat(col(key_col), lit("_"), col("salt"))
    )
    
    return salted_df1.join(exploded_df2, "salted_key").drop("salt", "salted_key")
```

### Join Order Matters

```python
# ✅ Good: Filter before join
filtered_df1 = df1.filter(col("active") == True)
filtered_df2 = df2.filter(col("status") == "valid")
result = filtered_df1.join(filtered_df2, "key")

# ❌ Bad: Join then filter
result = df1.join(df2, "key").filter(
    (col("active") == True) & (col("status") == "valid")
)

# ✅ Good: Small tables first in multi-way joins
result = (
    large_df
    .join(broadcast(small_lookup1), "key1")
    .join(broadcast(small_lookup2), "key2")
    .join(medium_df, "key3")
)
```

## DataFrame Operations

### Efficient Column Operations

```python
# ✅ Good: Single select with all operations
result = df.select(
    col("id"),
    lower(trim(col("name"))).alias("clean_name"),
    when(col("age") > 18, "adult").otherwise("minor").alias("category"),
    col("salary") * 1.1 as "adjusted_salary"
)

# ❌ Bad: Multiple withColumn calls
result = df.withColumn("clean_name", lower(trim(col("name"))))
result = result.withColumn("category", when(col("age") > 18, "adult").otherwise("minor"))
result = result.withColumn("adjusted_salary", col("salary") * 1.1)

# ✅ Good: Batch transformations
transformations = [
    ("clean_name", lower(trim(col("name")))),
    ("category", when(col("age") > 18, "adult").otherwise("minor")),
    ("adjusted_salary", col("salary") * 1.1)
]

result = df.select("*", *[expr.alias(name) for name, expr in transformations])
```

### Avoid UDFs When Possible

```python
# ❌ Bad: Python UDF (slow)
@udf(returnType=StringType())
def categorize_price(price):
    if price < 100000:
        return "low"
    elif price < 500000:
        return "medium"
    else:
        return "high"

df.withColumn("price_category", categorize_price(col("price")))

# ✅ Good: Spark SQL functions (fast)
df.withColumn(
    "price_category",
    when(col("price") < 100000, "low")
    .when(col("price") < 500000, "medium")
    .otherwise("high")
)

# If UDF necessary, use Pandas UDF
@pandas_udf(returnType=StringType())
def categorize_price_pandas(prices: pd.Series) -> pd.Series:
    return pd.cut(
        prices,
        bins=[0, 100000, 500000, float('inf')],
        labels=['low', 'medium', 'high']
    )
```

## Memory Management

### Partition Management

```python
# Check partition count
df.rdd.getNumPartitions()

# ✅ Good: Right-size partitions
# Target 100-200MB per partition
optimal_partitions = total_data_size_mb / 150
df = df.repartition(optimal_partitions)

# ✅ Good: Coalesce after filtering
filtered_df = large_df.filter(col("rare_condition") == True)
if filtered_df.count() < original_count * 0.1:
    filtered_df = filtered_df.coalesce(10)

# ❌ Bad: Too many small partitions
df.repartition(10000)  # Overhead of managing partitions

# ❌ Bad: Too few large partitions
df.coalesce(1)  # No parallelism, memory pressure
```

### Memory Configuration

```python
# Configure memory fractions
spark.conf.set("spark.memory.fraction", "0.6")  # Default 0.6
spark.conf.set("spark.memory.storageFraction", "0.5")  # Default 0.5

# Configure off-heap memory
spark.conf.set("spark.memory.offHeap.enabled", "true")
spark.conf.set("spark.memory.offHeap.size", "10g")

# Adaptive execution (Spark 3.0+)
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
```

## Performance Monitoring

### Use explain() for Query Planning

```python
# View execution plan without running
df.explain(True)  # True for extended plan

# Understand physical plan
df.select(...).filter(...).join(...).explain("formatted")
```

### Monitor Without Evaluation

```python
# ✅ Good: Schema inspection
logger.info(f"Columns: {df.columns}")
logger.info(f"Schema: {df.schema}")
logger.info(f"Partitions: {df.rdd.getNumPartitions()}")

# ✅ Good: Execution plan analysis
df.explain()
logger.info("Execution plan generated")

# ❌ Bad: Forcing evaluation for monitoring
logger.info(f"Row count: {df.count()}")
logger.info(f"Sample: {df.take(5)}")
df.show()  # Forces evaluation
```

### Use Accumulators for Metrics

```python
# Track metrics without forcing evaluation
processed_count = spark.sparkContext.accumulator(0)
error_count = spark.sparkContext.accumulator(0)

def process_row(row):
    try:
        # Process row
        processed_count.add(1)
        return transform(row)
    except:
        error_count.add(1)
        return None

result = df.rdd.map(process_row).filter(lambda x: x is not None)
result.saveAsTextFile(output)  # Single action

logger.info(f"Processed: {processed_count.value}, Errors: {error_count.value}")
```

## Common Anti-Patterns

### Anti-Pattern 1: Collect and Distribute

```python
# ❌ Bad: Collect to driver then parallelize
data = df.collect()
processed = [process(row) for row in data]
result_df = spark.createDataFrame(processed)

# ✅ Good: Process in Spark
result_df = df.select(process_udf(col("data")))
```

### Anti-Pattern 2: Row-by-Row Processing

```python
# ❌ Bad: Iterate over rows
for row in df.collect():
    process_row(row)

# ✅ Good: Batch processing
df.foreachPartition(lambda partition: process_batch(list(partition)))
```

### Anti-Pattern 3: Cartesian Products

```python
# ❌ Bad: Unintentional cartesian product
result = df1.join(df2)  # No join condition!

# ✅ Good: Explicit join condition
result = df1.join(df2, df1.key == df2.key)
```

### Anti-Pattern 4: Wide Dependencies

```python
# ❌ Bad: Many wide transformations
result = (
    df.groupBy("key1").agg(...)
    .groupBy("key2").agg(...)  
    .groupBy("key3").agg(...)  # Multiple shuffles
)

# ✅ Good: Minimize shuffles
result = df.groupBy("key1", "key2", "key3").agg(
    # All aggregations at once
)
```

## Code Quality Guidelines

### 1. Use Type Hints and Pydantic Models

```python
from pydantic import BaseModel
from typing import Optional, List
from pyspark.sql import DataFrame

class PipelineConfig(BaseModel):
    """Configuration for data pipeline."""
    input_path: str
    output_path: str
    cache_enabled: bool = True
    broadcast_threshold_mb: int = 100

def process_data(
    df: DataFrame, 
    config: PipelineConfig
) -> DataFrame:
    """Process DataFrame according to config."""
    if config.cache_enabled:
        df = df.cache()
    return df
```

### 2. Modular Design

```python
# ✅ Good: Separate concerns
class DataLoader:
    def load(self, path: str) -> DataFrame:
        return self.spark.read.parquet(path)

class DataEnricher:
    def enrich(self, df: DataFrame) -> DataFrame:
        return df.withColumn("enriched", lit(True))

class DataWriter:
    def write(self, df: DataFrame, path: str) -> None:
        df.write.parquet(path)

# Pipeline uses modules
loader = DataLoader(spark)
enricher = DataEnricher(spark)
writer = DataWriter(spark)

df = loader.load(input_path)
df = enricher.enrich(df)
writer.write(df, output_path)
```

### 3. Error Handling

```python
def safe_process(df: DataFrame) -> Optional[DataFrame]:
    """Process DataFrame with error handling."""
    try:
        result = df.filter(col("valid") == True)
        
        # Check for empty result without forcing evaluation
        if result.limit(1).count() == 0:
            logger.warning("No valid records found")
            return None
            
        return result
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return None
```

### 4. Documentation

```python
def optimize_join(
    left_df: DataFrame,
    right_df: DataFrame,
    join_key: str,
    broadcast_threshold_mb: int = 100
) -> DataFrame:
    """
    Optimize join operation based on DataFrame sizes.
    
    Uses broadcast join if right DataFrame is under threshold,
    otherwise uses sort-merge join.
    
    Args:
        left_df: Left DataFrame in join
        right_df: Right DataFrame in join  
        join_key: Column name to join on
        broadcast_threshold_mb: Max size in MB for broadcast
        
    Returns:
        Joined DataFrame with optimization applied
        
    Note:
        This function estimates size and may force a count
        operation on the right DataFrame for size calculation.
    """
    # Implementation here
    pass
```

## Summary

### Key Takeaways

1. **Lazy is Good**: Defer evaluation until necessary
2. **Actions are Expensive**: Minimize count(), collect(), show()
3. **Broadcast Small Data**: Use broadcast joins for small tables
4. **Cache Strategically**: Cache only when reused multiple times
5. **Monitor Without Evaluation**: Use explain(), schema inspection
6. **Batch Operations**: Combine transformations when possible
7. **Clean Code**: Use Pydantic, type hints, modular design

### Performance Checklist

Before committing Spark code, verify:

- [ ] No unnecessary count() or collect() operations
- [ ] Broadcasts used for small table joins
- [ ] DataFrames cached only when reused
- [ ] Filters applied before joins
- [ ] UDFs replaced with built-in functions where possible
- [ ] Partitions appropriately sized
- [ ] No cartesian products
- [ ] Error handling doesn't force evaluation
- [ ] Logging doesn't trigger actions
- [ ] Clean modular code with type hints

Following these practices will help you write efficient, scalable, and maintainable Spark applications.