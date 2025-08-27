# Property Relationships Data Flow Analysis

## Current Implementation Flow

### 1. Data Loading Phase
```
DataLoaderOrchestrator.load_all()
├── Load Properties → properties_df
├── Load Neighborhoods → neighborhoods_df  
└── Load Wikipedia → wikipedia_df
```

### 2. Processing Phase
```
Pipeline Runner processes each entity:
├── Process Properties (enrichment, text processing, embeddings)
├── Process Neighborhoods (enrichment, text processing, embeddings)
└── Process Wikipedia (enrichment, text processing, embeddings)
```

### 3. Entity Writing Phase
```
WriterOrchestrator.write_entity() for each:
├── Write Properties → Elasticsearch index "properties"
├── Write Neighborhoods → Elasticsearch index "neighborhoods"
└── Write Wikipedia → Elasticsearch index "wikipedia"
```

### 4. Relationship Writing Phase (PROBLEMATIC)
```
WriterOrchestrator.write_property_relationships_denormalized()
└── ElasticsearchOrchestrator.write_property_relationships()
    └── PropertyRelationshipBuilder.build_relationships()
        ├── _join_properties_neighborhoods() 
        ├── _extract_wikipedia_correlations()
        ├── _join_wikipedia_articles()
        └── _format_final_structure()
```

## Deep Analysis of Data Flow

### What Each Step Does

1. **_join_properties_neighborhoods()**
   - Takes properties_df and neighborhoods_df
   - Creates a struct from neighborhood fields
   - Joins on neighborhood_id
   - Result: properties with embedded neighborhood struct

2. **_extract_wikipedia_correlations()**
   - Looks for wikipedia_correlations field in neighborhoods
   - Extracts correlation data
   - Result: properties with Wikipedia references

3. **_join_wikipedia_articles()**
   - Extracts page_ids from correlations (primary and related)
   - Joins with wikipedia_df on page_id
   - Groups back to property level with collected Wikipedia articles
   - Result: properties with embedded Wikipedia array

4. **_format_final_structure()**
   - Selects final fields for denormalized document
   - Adds metadata fields
   - Result: Final denormalized structure

## Critical Issues Found

### Issue 1: Column Name Collision
**Problem**: After joining properties with neighborhoods, we have an ambiguous "neighborhood" column.

**Why it happens**:
- Properties already have a "neighborhood" field after being processed
- We're adding another "neighborhood" struct in the join
- Spark can't resolve which "neighborhood" to use

**Evidence**: Error message "Reference `neighborhood` is ambiguous, could be: [`main`.`neighborhood`, `neighborhood`]"

### Issue 2: DataFrame State Mismatch
**Problem**: The DataFrames passed to relationship builder have been processed and enriched, not in their original state.

**Why it happens**:
- Properties went through PropertyEnricher which may add neighborhood-related fields
- The relationship builder expects clean, unprocessed DataFrames
- We're passing the SAME processed DataFrames that were written to individual indices

### Issue 3: Wikipedia Correlation Structure
**Problem**: The wikipedia_correlations field structure doesn't match what the code expects.

**Why it happens**:
- Neighborhoods have complex nested correlation structure
- Code tries to access fields like `related_wiki_articles[0].page_id` which doesn't work in Spark
- The actual structure is an array: `related_wiki_articles` with multiple elements

### Issue 4: Timing and Data Consistency
**Problem**: Building relationships AFTER individual entity writes means we're working with potentially modified data.

**Why it happens**:
- Entity writing may transform data for Elasticsearch
- We then use these transformed DataFrames for relationships
- Original relationships may be lost or modified

## Root Cause Analysis

The fundamental issue is **architectural**: We're trying to build denormalized relationships as an afterthought rather than as part of the main pipeline flow.

### Current (Broken) Architecture:
```
Load Data → Process Entities → Write Entities → Build Relationships (fails)
```

### What Should Happen:
```
Load Data → Process Entities → Build Relationships → Write All Indices
                                    ↓
                        (denormalized index gets fresh data)
```

## Proposed Fix

### Option 1: Fix Column Naming (Quick Fix)
1. In PropertyEnricher, don't add "neighborhood" field if it will conflict
2. In relationship builder, use explicit column prefixes
3. Handle the column ambiguity with aliases

### Option 2: Build Relationships Earlier (Better Fix)
1. Build relationships BEFORE writing individual entities
2. Use clean DataFrames for relationship building
3. Store relationship DataFrame alongside entity DataFrames
4. Write all indices together

### Option 3: Dedicated Relationship Pipeline (Best Fix)
1. Create a separate pipeline path for relationships
2. Load data specifically for relationship building
3. Skip enrichments that cause conflicts
4. Build clean denormalized structure from scratch

## Specific Code Fixes Needed

### 1. Fix Column Ambiguity
```python
# In _join_properties_neighborhoods
neighborhoods_for_join = neighborhoods_df.select(
    col("neighborhood_id").alias("nbh_id"),
    struct(*[...]).alias("neighborhood_data")  # Use different name
)
```

### 2. Fix Wikipedia Correlation Extraction
```python
# Properly handle array structure
col("wikipedia_correlations.related_wiki_articles.page_id")
# This returns an array of page_ids, not individual elements
```

### 3. Fix Data Pipeline Integration
```python
# In pipeline_runner.py, build relationships BEFORE entity writing
if "elasticsearch" in enabled_destinations:
    # Build relationships first with clean data
    relationships_df = build_property_relationships(
        properties_df, neighborhoods_df, wikipedia_df
    )
    # Then write everything
    write_entities(...)
    write_relationships(relationships_df)
```

### 4. Prevent DataFrame Contamination
```python
# Use copies for relationship building
props_for_rels = properties_df.select(essential_columns_only)
nbh_for_rels = neighborhoods_df.select(essential_columns_only)
```

## Implementation Status

### ✅ Completed
1. **Column naming conflict** - Fixed by dropping existing "neighborhood" column before join
2. **Field availability** - Made field selection conditional with defaults

### 🔄 In Progress  
3. **Write operation failing** - Documents are built (6 created) but Elasticsearch write fails with socket error

### ⏳ Pending
4. **Wikipedia correlation extraction** - Structure mismatch needs fixing
5. **Pipeline refactoring** - Build relationships before heavy processing

## Current Blockers

1. **Socket/Connection Error during ES write**
   - 6 documents are successfully built
   - Write operation starts
   - Fails with `java.net.SocketException: Connection reset`
   - Likely due to DataFrame serialization issues

2. **Missing Original Fields**
   - Properties DataFrame has been heavily processed
   - Lost basic fields like price, bedrooms, bathrooms
   - Using defaults/nulls as workaround
   - Real fix: preserve original data through pipeline

## Next Steps

1. **Debug ES Write Failure** (Immediate)
   - Check DataFrame schema compatibility with ES mapping
   - Verify no incompatible data types
   - Test with minimal fields first

2. **Preserve Original Fields** (Short-term)
   - Modify pipeline to keep original property fields
   - Or build relationships before enrichment phase

3. **Fix Wikipedia Correlations** (Medium-term)
   - Handle array structure properly
   - Join with actual Wikipedia data

## Testing Strategy

1. Test with 5 properties first
2. Verify denormalized structure is correct
3. Check Elasticsearch mapping compatibility
4. Validate query performance improvement
5. Full pipeline test with all data

## Success Criteria

- [ ] Property relationships index populated with data
- [ ] No column ambiguity errors
- [ ] Wikipedia articles properly embedded
- [ ] Single-query retrieval works as designed
- [ ] Performance improvement demonstrated