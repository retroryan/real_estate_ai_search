# Fix Neo4j Data Loading Issues

Based on the analysis in QUERY_ANALYSIS.md, here's how to fix the missing data in Neo4j.

## Quick Fix Commands

Run these commands in order to properly load all data:

### 1. Clear and Reinitialize Database
```bash
# Clear existing incomplete data
python -m graph-real-estate clear

# Initialize schema
python -m graph-real-estate init
```

### 2. Run Complete Data Pipeline
```bash
# Run the full pipeline with all entity extraction and relationship building
PYTHONPATH=. python -m data_pipeline --full-pipeline

# Or if you want to see what would be loaded:
PYTHONPATH=. python -m data_pipeline --sample-size 5 --test-mode
```

### 3. Verify Entity Extraction
```python
# Check that entity extraction completed
from data_pipeline.core.pipeline_runner import DataPipelineRunner

runner = DataPipelineRunner()
result = runner.run_full_pipeline_with_embeddings()

# Check entity nodes were created
print("Entity DataFrames created:")
for entity_type, df in result.items():
    if df is not None:
        print(f"  {entity_type}: {df.count()} records")
```

### 4. Verify Relationship Building
```python
# Check that relationships were built
from data_pipeline.core.pipeline_runner import DataPipelineRunner

runner = DataPipelineRunner()
result = runner.run_full_pipeline_with_embeddings()
relationships = runner._build_relationships(result)

print("Relationships created:")
for rel_type, df in relationships.items():
    if df is not None:
        print(f"  {rel_type}: {df.count()} relationships")
```

## Manual Fix for Missing Nodes

If the pipeline still doesn't create all nodes, run this script:

```python
#!/usr/bin/env python3
"""Fix missing nodes and relationships in Neo4j."""

from pyspark.sql import SparkSession
from data_pipeline.enrichment.feature_extractor import FeatureExtractor
from data_pipeline.enrichment.entity_extractors import PropertyTypeExtractor, PriceRangeExtractor
from data_pipeline.enrichment.county_extractor import CountyExtractor
from data_pipeline.enrichment.topic_extractor import TopicExtractor
from data_pipeline.enrichment.relationship_builder import RelationshipBuilder
from data_pipeline.loaders.data_loader_orchestrator import DataLoaderOrchestrator
from data_pipeline.config.settings import ConfigurationManager
from data_pipeline.writers.neo4j_writer import Neo4jWriter

# Initialize Spark
spark = SparkSession.builder.appName("FixNeo4j").master("local[*]").getOrCreate()

# Load configuration
config_manager = ConfigurationManager()
config = config_manager.load_config()

# Load data
loader = DataLoaderOrchestrator(spark, config)
loaded_data = loader.load_all_sources()

# Extract missing entities
print("Extracting missing entities...")

# Features
feature_extractor = FeatureExtractor(spark)
features_df = feature_extractor.extract(loaded_data.properties)
print(f"  Features: {features_df.count()}")

# Property Types
type_extractor = PropertyTypeExtractor(spark)
property_types_df = type_extractor.extract_property_types(loaded_data.properties)
print(f"  Property Types: {property_types_df.count()}")

# Price Ranges
price_extractor = PriceRangeExtractor(spark)
price_ranges_df = price_extractor.extract_price_ranges(loaded_data.properties)
print(f"  Price Ranges: {price_ranges_df.count()}")

# Counties
county_extractor = CountyExtractor(spark)
counties_df = county_extractor.extract_counties(
    loaded_data.locations,
    loaded_data.properties,
    loaded_data.neighborhoods
)
print(f"  Counties: {counties_df.count()}")

# Topic Clusters
topic_extractor = TopicExtractor(spark)
topic_clusters_df = topic_extractor.extract_topic_clusters(loaded_data.wikipedia)
print(f"  Topic Clusters: {topic_clusters_df.count()}")

# Build missing relationships
print("\nBuilding missing relationships...")
relationship_builder = RelationshipBuilder(spark)

all_relationships = relationship_builder.build_extended_relationships(
    properties_df=loaded_data.properties,
    neighborhoods_df=loaded_data.neighborhoods,
    wikipedia_df=loaded_data.wikipedia,
    features_df=features_df,
    property_types_df=property_types_df,
    price_ranges_df=price_ranges_df,
    counties_df=counties_df,
    topic_clusters_df=topic_clusters_df
)

for rel_name, rel_df in all_relationships.items():
    if rel_df:
        print(f"  {rel_name}: {rel_df.count()} relationships")

# Write to Neo4j
print("\nWriting to Neo4j...")
neo4j_writer = Neo4jWriter(config.output.destinations.neo4j)

# Write nodes
neo4j_writer.write(features_df, "Feature")
neo4j_writer.write(property_types_df, "PropertyType")
neo4j_writer.write(price_ranges_df, "PriceRange")
neo4j_writer.write(counties_df, "County")
neo4j_writer.write(topic_clusters_df, "TopicCluster")

# Write relationships
for rel_name, rel_df in all_relationships.items():
    if rel_df:
        neo4j_writer.write_relationships(rel_df)

print("\n✅ Missing data has been loaded to Neo4j")
spark.stop()
```

## Validation Queries

After fixing, run these queries in Neo4j Browser to verify:

```cypher
// Check all nodes are present
CALL db.labels() YIELD label
WITH label
MATCH (n) WHERE label IN labels(n)
RETURN label, count(n) as count
ORDER BY label;

// Check all relationships are present
CALL db.relationshipTypes() YIELD relationshipType as type
MATCH ()-[r]->() WHERE type(r) = type
RETURN type, count(r) as count
ORDER BY type;

// Verify feature extraction worked
MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
RETURN f.name, count(p) as property_count
ORDER BY property_count DESC
LIMIT 10;

// Verify similarity relationships
MATCH (p1:Property)-[s:SIMILAR_TO]->(p2:Property)
RETURN count(s) as similarity_count;

// Verify geographic hierarchy
MATCH (n:Neighborhood)-[:PART_OF]->(c:City)
RETURN c.name, count(n) as neighborhood_count
ORDER BY neighborhood_count DESC;

// Verify Wikipedia relationships
MATCH (w:WikipediaArticle)-[:DESCRIBES]->(n:Neighborhood)
RETURN n.name, count(w) as article_count
ORDER BY article_count DESC
LIMIT 10;
```

## Expected Results After Fix

You should see:
- **Nodes**: Property (420), Neighborhood (21), Feature (~400+), PropertyType (3-5), PriceRange (5), County (~10), City (~10), State (2-3), TopicCluster (~10)
- **Relationships**: LOCATED_IN (420), HAS_FEATURE (3000+), SIMILAR_TO (20000+), PART_OF (50+), DESCRIBES (100+), OF_TYPE (420), IN_PRICE_RANGE (420), IN_COUNTY (50+)

## Troubleshooting

If data is still missing:

1. **Check Spark logs** for extraction errors:
   ```bash
   grep ERROR spark.log
   ```

2. **Verify source data exists**:
   ```bash
   ls -la real_estate_data/*.json
   ls -la data/wikipedia/wikipedia.db
   ```

3. **Run with verbose logging**:
   ```bash
   PYTHONPATH=. python -m data_pipeline --log-level DEBUG
   ```

4. **Check Neo4j constraints**:
   ```cypher
   SHOW CONSTRAINTS;
   ```

5. **Verify Neo4j writer is enabled**:
   ```bash
   grep neo4j data_pipeline/config.yaml
   ```