# Eland DataFrames for Property Analysis

This directory contains examples of using [Eland](https://eland.readthedocs.io/) to analyze real estate property data stored in Elasticsearch.

## What is Eland?

Eland is a Python Elasticsearch client that provides:
- Pandas-compatible DataFrame API
- Server-side execution of operations
- Seamless integration with existing pandas workflows
- Support for large-scale data analysis

## Available Scripts

### 1. `eland_simple_demo.py`
A concise demonstration of core Eland functionality:
- Loading Elasticsearch indices as DataFrames
- Basic operations (filtering, aggregations, value counts)
- Exporting to pandas for advanced analysis
- Working with multiple indices

### 2. `eland_property_analysis.py`
A comprehensive example showcasing:
- Advanced filtering and selection
- Complex aggregations
- Geospatial analysis
- Visualization examples
- Performance optimization tips

## Installation

```bash
pip install eland matplotlib seaborn
```

## Usage

### Running the Simple Demo

```bash
python inference/eland_simple_demo.py
```

This will demonstrate:
- Loading 440 properties from Elasticsearch
- Filtering properties by price, bedrooms, etc.
- Calculating statistics (mean, median, min, max prices)
- Grouping and aggregating data
- Exporting results to CSV

### Running the Full Analysis

```bash
python inference/eland_property_analysis.py
```

## Key Features Demonstrated

### 1. DataFrame Creation
```python
df = ed.DataFrame(
    es_client=es_client,
    es_index_pattern="properties"
)
```

### 2. Filtering Operations
```python
# Properties between $500K and $1M
filtered = df[(df['price'] >= 500000) & (df['price'] <= 1000000)]

# 3+ bedroom properties
large_props = df[df['bedrooms'] >= 3]
```

### 3. Aggregations
```python
# Average price by property type
avg_by_type = df.groupby('property_type')['price'].mean()

# Count by bedrooms
bedroom_counts = df['bedrooms'].value_counts()
```

### 4. Export to Pandas
```python
# Export sample for advanced analysis
pandas_df = df.head(100).to_pandas()
```

## Data Overview

The demos work with:
- **Properties index**: 440 real estate listings
  - Fields: price, bedrooms, bathrooms, square_feet, location, etc.
- **Neighborhoods index**: 21 neighborhood records
  - Fields: demographics, walkability scores, amenities, etc.

## Benefits of Using Eland

1. **Scalability**: Process millions of documents without loading into memory
2. **Performance**: Operations execute on Elasticsearch cluster
3. **Familiarity**: Use pandas syntax you already know
4. **Integration**: Seamlessly switch between Eland and pandas
5. **Efficiency**: Only transfer data when needed

## Limitations to Note

- Some pandas operations not available (e.g., sort_values, nlargest)
- Limited join operations
- Correlation matrix requires conversion to pandas
- Complex operations may require Elasticsearch DSL queries

## Next Steps

1. Explore the [Eland documentation](https://eland.readthedocs.io/)
2. Try modifying queries for your use case
3. Integrate with ML pipelines for feature engineering
4. Use for exploratory data analysis (EDA)
5. Build dashboards with processed data

## Resources

- [Eland Documentation](https://eland.readthedocs.io/)
- [Elasticsearch Python Client](https://elasticsearch-py.readthedocs.io/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)