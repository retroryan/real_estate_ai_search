# START_HERE.md

## Current State & Issues

We were working on integrating Neo4j writer with the data pipeline and fixing relationship building errors. The system is mostly working but has some remaining issues with property enrichment.

## What We Were Working On

1. **Primary Goal**: Create neo4j_config.yaml and integrate Neo4j writer with data pipeline
2. **Secondary Goal**: Ensure all data flows correctly through the pipeline with proper relationship building
3. **Current Task**: Fix property enrichment to preserve neighborhood_id through the enrichment process

## Current Problems

### 1. Property Enrichment Column Resolution Error
**Status**: 🔴 BROKEN - Immediate attention needed

The property enricher is failing because it's trying to access `bedrooms` column before extracting it from nested `property_details` structure.

**Error**: 
```
[UNRESOLVED_COLUMN.WITH_SUGGESTION] A column, variable, or function parameter with name `bedrooms` cannot be resolved.
```

**Root Cause**: The `_calculate_price_fields` method is accessing `bedrooms` column before the nested structure has been flattened.

**Files Affected**:
- `data_pipeline/enrichment/property_enricher.py` (lines around 327-333)

### 2. Schema Mismatch Between Loader and Source Data
**Status**: 🟡 PARTIALLY FIXED - Needs verification

The property loader schema expects different field names than what's in the source data:
- Source data has `address.zip` but loader expected `address.zip_code` 
- Property details are nested differently than expected

**Files Affected**:
- `data_pipeline/loaders/property_loader.py` 
- `real_estate_data/properties_sf.json`

## What's Working

### ✅ Successfully Completed
1. **Neo4j Configuration**: Created comprehensive `data_pipeline/configs/neo4j_config.yaml`
2. **Neo4j Integration**: Neo4j writer is properly configured and working
3. **Relationship Building**: Fixed all ambiguous column issues and relationship building works
4. **Data Loading**: Properties load correctly with `neighborhood_id` from source data
5. **Configuration Loading**: Properly loads from parent `.env` and `data_pipeline/config.yaml`
6. **Path Issues**: Fixed relative path problems for parent directory execution

### ✅ Working Relationships
When the pipeline runs successfully, it creates:
- **420 LOCATED_IN relationships** (properties to neighborhoods)
- **37 PART_OF relationships** (neighborhood hierarchies)  
- **868 DESCRIBES relationships** (Wikipedia articles to locations)

## Immediate Next Steps (Priority Order)

### 1. Fix Property Enricher Column Access 🔴 URGENT
**Problem**: Property enricher accesses columns before extracting them from nested structures.

**Solution**: Modify `data_pipeline/enrichment/property_enricher.py`:
- Extract all nested columns FIRST in the `enrich()` method
- Then run all subsequent enrichment steps on flattened DataFrame
- Ensure column extraction happens before any column references

### 2. Verify Schema Consistency 🟡
**Problem**: Potential mismatches between loader schema and source data structure.

**Solution**: 
- Run a test to verify property loading works with current schema
- Check if all nested structures are correctly defined
- Ensure field names match between loader and source data

### 3. Test Full Pipeline 🟢
**Problem**: Need to verify end-to-end pipeline works after fixes.

**Solution**:
```bash
cd data_pipeline
PYTHONPATH=. DATA_SUBSET_SAMPLE_SIZE=10 python -m data_pipeline --test-mode
```

## Key Architecture Points

### Data Flow
```
PropertyLoader → PropertyEnricher → RelationshipBuilder → Neo4jWriter
     ↓               ↓                    ↓                 ↓
Load w/ neighborhood_id → Preserve neighborhood_id → Build relationships → Write to Neo4j
```

### Critical Files
- `data_pipeline/enrichment/property_enricher.py` - **NEEDS IMMEDIATE FIX**
- `data_pipeline/loaders/property_loader.py` - Schema definitions
- `data_pipeline/enrichment/relationship_builder.py` - Working correctly
- `data_pipeline/configs/neo4j_config.yaml` - Neo4j configuration (working)
- `data_pipeline/config.yaml` - Main pipeline config (working)

### Environment Setup
```bash
# Required environment variables in parent .env
NEO4J_PASSWORD=scott_tiger
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_DATABASE=neo4j
```

## Test Commands

### Quick Test (Properties Only)
```bash
PYTHONPATH=. python -c "
from pyspark.sql import SparkSession
from data_pipeline.loaders.property_loader import PropertyLoader
spark = SparkSession.builder.appName('test').master('local[1]').getOrCreate()
loader = PropertyLoader(spark)
df = loader.load('real_estate_data/properties_sf.json')
print('Schema:', df.columns)
df.select('listing_id', 'neighborhood_id').show(5)
spark.stop()
"
```

### Full Pipeline Test
```bash
cd data_pipeline
PYTHONPATH=. DATA_SUBSET_SAMPLE_SIZE=5 python -m data_pipeline --test-mode
```

## Documentation
- **Neo4j Setup**: See `data_pipeline/README.md` for Neo4j installation and data loading instructions
- **Configuration**: All config files are in `data_pipeline/configs/` and `data_pipeline/config.yaml`
- **Parent Project**: See main `CLAUDE.md` for overall project documentation

---

**Last Updated**: 2025-08-24 17:15 PST
**Status**: Property enricher needs immediate fix for column access order
**Next Person Should**: Fix the column access issue in PropertyEnricher.enrich() method