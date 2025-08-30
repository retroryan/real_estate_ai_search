# DuckDB Best Practices for Production Data Pipelines (2024)

## Executive Summary

This document consolidates DuckDB best practices for production data pipelines, based on official documentation, performance benchmarks, and real-world implementations. Updated for DuckDB 1.0+ (stable release) with the latest optimizations from 2024.

## Table of Contents
1. [Core Philosophy](#core-philosophy)
2. [Performance Fundamentals](#performance-fundamentals)
3. [Security Best Practices](#security-best-practices)
4. [Medallion Architecture](#medallion-architecture)
5. [Data Type Management](#data-type-management)
6. [Python Integration](#python-integration)
7. [SQL Patterns](#sql-patterns)
8. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
9. [Testing Strategies](#testing-strategies)
10. [Production Checklist](#production-checklist)

## Core Philosophy

DuckDB is an in-process OLAP database optimized for analytical queries on local data. In 2024, DuckDB has become 3-25× faster than 3 years ago and can analyze ~10× larger datasets on the same hardware.

### Key Principles
- **SQL-First**: Use SQL as the primary transformation language
- **Columnar Processing**: Leverage DuckDB's columnar engine
- **Zero-Copy**: Minimize data movement and serialization
- **In-Process**: Run within your application process

## Performance Fundamentals

### Connection Management
```python
# ✅ GOOD: Reuse connections
conn = duckdb.connect('pipeline.db')
# Reuse conn for multiple queries

# ❌ BAD: Create new connection per query
for query in queries:
    conn = duckdb.connect('pipeline.db')  # Overhead!
    conn.execute(query)
    conn.close()
```

**Best Practice**: Reuse the same database connection many times. Disconnecting and reconnecting incurs overhead and loses cached data and metadata.

### File Format Optimization
- **Parquet > CSV**: DuckDB can be up to 600× slower reading CSV vs Parquet
- **Always convert CSV to Parquet** for production workloads
- **Direct file operations**: Use `read_parquet()` without intermediate loading

```sql
-- ✅ GOOD: Direct Parquet reading
CREATE TABLE bronze AS SELECT * FROM read_parquet('data/*.parquet');

-- ❌ BAD: CSV in production
CREATE TABLE bronze AS SELECT * FROM read_csv('data/*.csv');
```

### Memory Configuration
```python
# Configure for large operations (v0.10.0+ improvements)
conn = duckdb.connect(config={
    'memory_limit': '8GB',      # Adjust based on available RAM
    'threads': 4,               # Parallel processing
    'max_memory': '8GB',        # v0.10.0+ memory management
})
```

For remote files, set `threads` to 2-5× CPU cores for better parallelism with network IO.

### Query Optimization

#### Use EXPLAIN ANALYZE
```sql
-- Analyze query performance
EXPLAIN ANALYZE
SELECT * FROM large_table WHERE condition;
```

Watch for:
- ✅ Hash joins (fast)
- ❌ Nested loop joins (slow for large data)
- ✅ Filter pushdowns applied
- ❌ Cardinality explosion in joins

#### Prepared Statements
For queries <100ms runtime executed repeatedly:
```python
# Prepare once, execute many times
conn.execute("PREPARE stmt AS SELECT * FROM t WHERE id = ?")
for id in ids:
    conn.execute("EXECUTE stmt(?)", [id])
```

## Security Best Practices

### SQL Injection Prevention

#### Table Name Validation
```python
from pydantic import BaseModel, Field, validator
import re

class TableIdentifier(BaseModel):
    """SQL-safe table identifier"""
    name: str = Field(..., regex=r'^[a-zA-Z][a-zA-Z0-9_]{0,63}$')
    schema: str = Field(default='main')
    
    @property
    def qualified_name(self) -> str:
        return f'"{self.schema}"."{self.name}"'

# ✅ SAFE: Validated table names
table = TableIdentifier(name="properties_bronze")
conn.execute(f"CREATE TABLE {table.qualified_name} AS ...")

# ❌ UNSAFE: Direct concatenation
table_name = user_input
conn.execute(f"CREATE TABLE {table_name} AS ...")  # SQL injection risk!
```

#### Parameterized Queries
```python
# ✅ SAFE: Parameterized for user data
conn.execute("SELECT * FROM t WHERE price > ?", [user_price])

# ❌ UNSAFE: String concatenation
conn.execute(f"SELECT * FROM t WHERE price > {user_price}")
```

### Connection Security
```python
class DuckDBConnectionConfig(BaseModel):
    """Secure connection configuration"""
    memory_limit: str = Field(regex=r'^\d+[MG]B$')
    threads: int = Field(ge=1, le=128)
    database_file: Path = Field(default=':memory:')
    read_only: bool = Field(default=False)
    
    def create_connection(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(
            database=str(self.database_file),
            read_only=self.read_only,
            config={
                'memory_limit': self.memory_limit,
                'threads': self.threads
            }
        )
```

## Medallion Architecture

### Layer Definitions

#### Bronze Layer (Raw Ingestion)
**Purpose**: Immutable raw data storage with minimal transformation

```sql
-- Bronze: Preserve raw data exactly
CREATE TABLE bronze_properties AS
SELECT 
    *,
    current_timestamp AS ingested_at,
    'properties.json' AS source_file,
    md5(to_json(*)::VARCHAR) AS row_hash  -- For change detection
FROM read_json_auto('data/properties/*.json');

-- Add metadata for lineage
ALTER TABLE bronze_properties 
ADD COLUMN load_id UUID DEFAULT gen_random_uuid();
```

**Best Practices**:
- Keep data immutable
- Add ingestion metadata
- Preserve original data types
- Use `read_json_auto()` for schema inference
- Store row hashes for change detection

#### Silver Layer (Standardization)
**Purpose**: Clean, standardize, and validate data

```sql
-- Silver: Standardize and clean
CREATE TABLE silver_properties AS
SELECT
    -- Standardize identifiers
    listing_id AS property_id,
    
    -- Clean numeric values
    CASE 
        WHEN price BETWEEN 10000 AND 100000000 THEN price
        ELSE NULL 
    END AS price,
    
    -- Standardize text
    TRIM(UPPER(state)) AS state_code,
    LOWER(REGEXP_REPLACE(property_type, '[^a-z0-9]', '_', 'g')) AS property_type,
    
    -- Parse nested JSON
    json_extract_string(address, '$.street') AS street,
    json_extract_string(address, '$.city') AS city,
    
    -- Normalize coordinates
    CAST(latitude AS DECIMAL(10, 7)) AS latitude,
    CAST(longitude AS DECIMAL(10, 7)) AS longitude,
    
    -- Data quality flags
    CASE 
        WHEN price IS NULL THEN 'missing_price'
        WHEN bedrooms > 20 THEN 'suspicious_bedrooms'
        ELSE 'valid'
    END AS quality_flag
    
FROM bronze_properties
WHERE listing_id IS NOT NULL;

-- Create indexes for common queries
CREATE INDEX idx_silver_prop_state ON silver_properties(state_code);
CREATE INDEX idx_silver_prop_price ON silver_properties(price);
```

**Best Practices**:
- Apply data quality rules
- Standardize formats (dates, strings, decimals)
- Extract from nested structures
- Add quality flags but don't drop records
- Create indexes for query performance

#### Gold Layer (Business Logic)
**Purpose**: Apply business rules and create analytical datasets

```sql
-- Gold: Business-ready analytical data
CREATE TABLE gold_properties AS
WITH enriched AS (
    SELECT 
        p.*,
        -- Computed metrics
        p.price / NULLIF(p.square_feet, 0) AS price_per_sqft,
        EXTRACT(YEAR FROM current_date) - p.year_built AS property_age,
        
        -- Geographic enrichment
        h3_latlng_to_cell(p.latitude, p.longitude, 9) AS h3_cell,
        
        -- Neighborhood enrichment
        n.median_income AS neighborhood_median_income,
        n.school_score AS neighborhood_school_score,
        
        -- Market analysis
        p.price / NULLIF(n.median_home_price, 1) AS price_ratio,
        PERCENT_RANK() OVER (
            PARTITION BY p.state_code 
            ORDER BY p.price
        ) AS price_percentile_state
        
    FROM silver_properties p
    LEFT JOIN silver_neighborhoods n 
        ON p.neighborhood_id = n.neighborhood_id
)
SELECT 
    *,
    -- Business categorizations
    CASE 
        WHEN price_ratio > 1.5 THEN 'luxury'
        WHEN price_ratio < 0.7 THEN 'affordable'
        ELSE 'standard'
    END AS market_segment,
    
    CASE
        WHEN price_percentile_state > 0.9 THEN 'top_10_percent'
        WHEN price_percentile_state > 0.75 THEN 'upper_quartile'
        WHEN price_percentile_state < 0.25 THEN 'lower_quartile'
        ELSE 'middle_market'
    END AS market_position

FROM enriched;

-- Create materialized aggregates for dashboards
CREATE TABLE gold_market_summary AS
SELECT 
    state_code,
    market_segment,
    COUNT(*) AS property_count,
    AVG(price) AS avg_price,
    MEDIAN(price) AS median_price,
    STDDEV(price) AS price_stddev,
    AVG(price_per_sqft) AS avg_price_per_sqft
FROM gold_properties
GROUP BY state_code, market_segment;
```

**Best Practices**:
- Apply complex business logic
- Create denormalized views for performance
- Pre-compute expensive aggregations
- Add business categorizations
- Use window functions for rankings

## Data Type Management

### Decimal Type Best Practices

```sql
-- ✅ GOOD: Optimal decimal precision
CREATE TABLE financial_data (
    -- Width ≤ 18 for performance
    amount DECIMAL(18, 2),     -- Fast: Uses INT64 internally
    
    -- For money, always use DECIMAL
    price DECIMAL(12, 2),       -- Exact arithmetic
    tax_amount DECIMAL(10, 4)   -- 4 decimal places for tax calculations
);

-- ❌ BAD: Over-specified precision
CREATE TABLE slow_data (
    -- Width > 19 is slow (uses INT128)
    huge_number DECIMAL(38, 10)  -- Very slow arithmetic!
);
```

**Python Decimal Handling**:
```python
from decimal import Decimal
import duckdb

# DuckDB returns Python Decimal objects for DECIMAL columns
result = conn.execute("SELECT price FROM properties").fetchall()
# result contains Decimal objects for exact precision

# For DataFrame conversion
df = conn.execute("SELECT * FROM properties").df()
# DataFrames may convert to float64 - be aware of precision loss
```

### Type Conversion Rules

```python
# Pydantic model for type-safe conversion
from pydantic import BaseModel, Field
from decimal import Decimal

class PropertyInput(BaseModel):
    """DuckDB input with Decimal types"""
    price: Decimal
    bedrooms: int
    bathrooms: Decimal  # Can be 2.5
    
    @field_serializer('price', 'bathrooms')
    def serialize_decimal(self, value: Decimal) -> float:
        """Convert Decimal to float for JSON/ES"""
        return float(value)

# Type mapping reference
TYPE_MAPPING = {
    'DECIMAL': Decimal,      # Python decimal.Decimal
    'INTEGER': int,          # Python int
    'BIGINT': int,           # Python int
    'DOUBLE': float,         # Python float
    'VARCHAR': str,          # Python str
    'DATE': date,           # Python datetime.date
    'TIMESTAMP': datetime,   # Python datetime.datetime
    'BOOLEAN': bool,        # Python bool
    'JSON': dict,           # Python dict
    'LIST': list,           # Python list
}
```

## Python Integration

### Connection Patterns

```python
from contextlib import contextmanager
import duckdb
from pathlib import Path

class DuckDBConnectionManager:
    """Singleton connection manager"""
    _instance = None
    _connection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_connection(self, config: dict = None) -> duckdb.DuckDBPyConnection:
        if self._connection is None:
            self._connection = duckdb.connect(
                database=':memory:',
                config=config or {
                    'memory_limit': '4GB',
                    'threads': 4
                }
            )
        return self._connection
    
    @contextmanager
    def transaction(self):
        """Context manager for transactions"""
        conn = self.get_connection()
        conn.execute("BEGIN TRANSACTION")
        try:
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
```

### Efficient Data Loading

```python
# ✅ GOOD: Direct file operations
def load_parquet_files(pattern: str) -> None:
    conn = duckdb.connect()
    conn.execute(f"""
        CREATE TABLE data AS 
        SELECT * FROM read_parquet('{pattern}')
    """)

# ❌ BAD: Load to pandas first
def inefficient_load(pattern: str) -> None:
    import pandas as pd
    import glob
    
    dfs = []
    for file in glob.glob(pattern):
        dfs.append(pd.read_parquet(file))  # Memory overhead!
    
    df = pd.concat(dfs)
    conn = duckdb.connect()
    conn.execute("CREATE TABLE data AS SELECT * FROM df")
```

### Streaming Large Results

```python
def stream_query_results(query: str, batch_size: int = 10000):
    """Stream large query results in batches"""
    conn = duckdb.connect()
    conn.execute(query)
    
    while True:
        batch = conn.fetchmany(batch_size)
        if not batch:
            break
        yield batch

# Usage
for batch in stream_query_results("SELECT * FROM large_table"):
    process_batch(batch)
```

## SQL Patterns

### Efficient Transformations

```sql
-- ✅ GOOD: Set-based operations
UPDATE properties 
SET city = INITCAP(city)
WHERE city IS NOT NULL;

-- ❌ BAD: Row-by-row processing
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN SELECT * FROM properties LOOP
        UPDATE properties 
        SET city = INITCAP(city) 
        WHERE id = r.id;
    END LOOP;
END $$;
```

### Window Functions (25× faster in v0.9.0)

```sql
-- Efficient ranking and analytics
SELECT 
    property_id,
    price,
    -- Running statistics
    AVG(price) OVER (
        PARTITION BY state_code 
        ORDER BY listing_date 
        ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
    ) AS moving_avg_30d,
    
    -- Ranking
    ROW_NUMBER() OVER (
        PARTITION BY state_code 
        ORDER BY price DESC
    ) AS price_rank_in_state,
    
    -- Lag/Lead for comparisons
    price - LAG(price) OVER (
        PARTITION BY property_id 
        ORDER BY listing_date
    ) AS price_change
    
FROM properties;
```

### CTEs for Complex Logic

```sql
WITH RECURSIVE property_hierarchy AS (
    -- Base case
    SELECT 
        property_id,
        parent_property_id,
        1 AS level
    FROM properties
    WHERE parent_property_id IS NULL
    
    UNION ALL
    
    -- Recursive case
    SELECT 
        p.property_id,
        p.parent_property_id,
        ph.level + 1
    FROM properties p
    JOIN property_hierarchy ph 
        ON p.parent_property_id = ph.property_id
    WHERE ph.level < 10  -- Prevent infinite recursion
)
SELECT * FROM property_hierarchy;
```

## Anti-Patterns to Avoid

### ❌ DON'T: Use isinstance/hasattr for Type Checking
```python
# BAD: Runtime type checking
if isinstance(value, Decimal):
    value = float(value)
    
# GOOD: Pydantic models with explicit types
class DataModel(BaseModel):
    value: Decimal
    
    @field_serializer('value')
    def serialize_value(self, v: Decimal) -> float:
        return float(v)
```

### ❌ DON'T: Create Unnecessary Intermediate Tables
```sql
-- BAD: Multiple intermediate tables
CREATE TABLE temp1 AS SELECT * FROM source WHERE condition1;
CREATE TABLE temp2 AS SELECT * FROM temp1 WHERE condition2;
CREATE TABLE final AS SELECT * FROM temp2;

-- GOOD: Single query with CTEs
CREATE TABLE final AS
WITH filtered AS (
    SELECT * FROM source 
    WHERE condition1 AND condition2
)
SELECT * FROM filtered;
```

### ❌ DON'T: Use Python Loops for Data Transformation
```python
# BAD: Python loops
for row in data:
    row['price_per_sqft'] = row['price'] / row['sqft']
    
# GOOD: SQL transformation
conn.execute("""
    ALTER TABLE properties 
    ADD COLUMN price_per_sqft AS (price / NULLIF(sqft, 0))
""")
```

### ❌ DON'T: Over-Normalize for Analytics
```sql
-- BAD: Excessive normalization for OLAP
SELECT p.*, a.*, n.*, s.*, c.*
FROM properties p
JOIN addresses a ON p.address_id = a.id
JOIN neighborhoods n ON a.neighborhood_id = n.id
JOIN schools s ON n.school_id = s.id
JOIN cities c ON n.city_id = c.id;

-- GOOD: Denormalized for analytics
SELECT * FROM gold_properties_denormalized;
```

### ❌ DON'T: Ignore File Formats
```python
# BAD: CSV in production
df = pd.read_csv('large_file.csv')  # Slow!

# GOOD: Convert to Parquet
conn.execute("""
    COPY (SELECT * FROM read_csv('large_file.csv')) 
    TO 'large_file.parquet' (FORMAT PARQUET)
""")
```

## Testing Strategies

### Data Validation Tests

```sql
-- Test suite using SQL assertions
CREATE OR REPLACE MACRO test_unique_ids() AS (
    SELECT 
        CASE 
            WHEN COUNT(*) = COUNT(DISTINCT property_id) 
            THEN 'PASS: All IDs are unique'
            ELSE 'FAIL: Duplicate IDs found: ' || 
                 (COUNT(*) - COUNT(DISTINCT property_id))::VARCHAR
        END AS result
    FROM silver_properties
);

CREATE OR REPLACE MACRO test_price_range() AS (
    SELECT 
        CASE
            WHEN MIN(price) >= 0 AND MAX(price) <= 100000000
            THEN 'PASS: Prices in valid range'
            ELSE 'FAIL: Price out of range - Min: ' || MIN(price)::VARCHAR || 
                 ', Max: ' || MAX(price)::VARCHAR
        END AS result
    FROM silver_properties
    WHERE price IS NOT NULL
);

-- Run all tests
SELECT test_unique_ids() 
UNION ALL 
SELECT test_price_range();
```

### Transformation Testing

```python
import duckdb
import pytest

class TestTransformations:
    def test_bronze_to_silver(self):
        conn = duckdb.connect(':memory:')
        
        # Setup test data
        conn.execute("""
            CREATE TABLE bronze_properties AS 
            SELECT * FROM (VALUES 
                ('1', 'ca', 500000.00),
                ('2', 'CA', 750000.00),
                ('3', ' ca ', 600000.00)
            ) AS t(listing_id, state, price)
        """)
        
        # Apply transformation
        conn.execute("""
            CREATE TABLE silver_properties AS
            SELECT 
                listing_id AS property_id,
                TRIM(UPPER(state)) AS state_code,
                price
            FROM bronze_properties
        """)
        
        # Verify
        result = conn.execute("""
            SELECT COUNT(DISTINCT state_code) 
            FROM silver_properties
        """).fetchone()[0]
        
        assert result == 1  # All normalized to 'CA'
```

### Performance Testing

```python
import time
import duckdb

def benchmark_query(conn, query: str, name: str):
    """Benchmark query performance"""
    start = time.time()
    conn.execute(query).fetchall()
    elapsed = time.time() - start
    
    print(f"{name}: {elapsed:.2f}s")
    
    # Get query plan
    plan = conn.execute(f"EXPLAIN {query}").fetchall()
    
    # Check for anti-patterns
    plan_str = str(plan)
    if 'NESTED_LOOP_JOIN' in plan_str:
        print("WARNING: Nested loop join detected!")
    if 'SEQ_SCAN' in plan_str and 'Filter' not in plan_str:
        print("WARNING: Full table scan without filter!")
```

## Production Checklist

### Pre-Deployment

- [ ] **File Formats**: All data files converted to Parquet
- [ ] **Connection Management**: Singleton pattern implemented
- [ ] **Security**: SQL injection prevention via parameterized queries
- [ ] **Memory Configuration**: Appropriate limits set for workload
- [ ] **Decimal Precision**: WIDTH ≤ 18 for performance
- [ ] **Indexes**: Created for frequently filtered columns
- [ ] **Data Validation**: Test suite passes
- [ ] **Error Handling**: Try-catch blocks and logging

### Performance Optimization

- [ ] **Query Plans**: EXPLAIN ANALYZE run on critical queries
- [ ] **Join Strategies**: Hash joins used (not nested loops)
- [ ] **Filter Pushdown**: Confirmed via EXPLAIN
- [ ] **Batch Size**: Optimal for memory and performance
- [ ] **Prepared Statements**: Used for repeated queries
- [ ] **Column Pruning**: SELECT only needed columns

### Monitoring

- [ ] **Query Timing**: Logging slow queries
- [ ] **Memory Usage**: Tracking via `pragma database_size`
- [ ] **Connection Pool**: Monitoring active connections
- [ ] **Data Quality**: Regular validation checks
- [ ] **Error Rates**: Tracking failed queries

### Data Quality

- [ ] **Null Checks**: Critical fields validated
- [ ] **Range Checks**: Numeric values within bounds  
- [ ] **Uniqueness**: Primary keys verified
- [ ] **Referential Integrity**: Foreign keys valid
- [ ] **Completeness**: Required fields present

## Version-Specific Features (2024)

### DuckDB 1.0+ (Stable Release)
- Production-ready stability guarantees
- Backward compatibility commitment
- Enhanced memory management

### v0.10.0 (February 2024)
- Improved memory management for concurrent operators
- Better handling of larger-than-memory datasets
- Enhanced spilling to disk

### v0.9.0 (September 2023) 
- 25× faster window functions
- 10× faster exports
- 4-5× faster Parquet export

## Conclusion

This guide represents production-tested best practices for DuckDB as of 2024. Key takeaways:

1. **Connection Reuse**: Single connection pattern for performance
2. **File Formats**: Always use Parquet for production
3. **SQL-First**: Leverage DuckDB's SQL engine, not Python loops
4. **Type Safety**: Pydantic models at boundaries, SQL for transforms
5. **Security**: Parameterized queries and validated identifiers
6. **Medallion Architecture**: Clear Bronze → Silver → Gold layers
7. **Performance**: Monitor query plans, use appropriate indexes
8. **Testing**: SQL-based validation and performance benchmarks

Following these practices ensures efficient, maintainable, and secure data pipelines with DuckDB.