# Wikipedia Article Neighborhood Enrichment Proposal

## Executive Summary

This proposal outlines a simple, direct approach to enrich Wikipedia articles with neighborhood data in the squack_pipeline_v2 data pipeline. The goal is to denormalize neighborhood associations directly into Wikipedia articles in the Silver layer, making Wikipedia articles searchable by neighborhood name.

## Current State Analysis

### Existing Data Structure

1. **Neighborhoods (Silver Layer)**
   - Contains `wikipedia_correlations` field with primary wiki article page_id
   - Has neighborhood name, city, state, and other location data
   - Each neighborhood knows which Wikipedia articles it relates to

2. **Wikipedia Articles (Silver Layer)**
   - Contains page_id as unique identifier
   - Has title, content, location data
   - Currently has NO direct neighborhood associations

### Core Problem

Wikipedia articles cannot be searched by neighborhood name because the relationship exists only in one direction (neighborhood → wikipedia), not bidirectionally.

## Proposed Solution

### Simple Denormalization Strategy

Add neighborhood data directly to Wikipedia articles in the Silver layer through a straightforward denormalization process:

1. **Extract neighborhood associations** from the neighborhoods table
2. **Join with Wikipedia articles** using page_id
3. **Add neighborhood fields** directly to Wikipedia records
4. **Make searchable** in Gold layer

### Data Fields to Add to Wikipedia Articles

The following fields will be added to each Wikipedia article in the Silver layer:

- **neighborhood_names**: List of all neighborhood names associated with this article
- **primary_neighborhood_name**: The primary neighborhood name (for articles with one main association)
- **neighborhood_ids**: List of neighborhood identifiers for reference

## Technical Requirements

### Silver Layer Modifications

#### Wikipedia Silver Transformer Changes

1. **Create neighborhood mapping table**
   - Query silver_neighborhoods table
   - Extract wikipedia_page_id from wikipedia_correlations
   - Build mapping of page_id → neighborhood data

2. **Join with Wikipedia articles**
   - LEFT JOIN mapping table with silver_wikipedia on page_id
   - Aggregate multiple neighborhoods per article if they exist
   - Handle NULL cases where no neighborhood association exists

3. **Add new columns to silver_wikipedia**
   - neighborhood_names (VARCHAR[])
   - primary_neighborhood_name (VARCHAR)
   - neighborhood_ids (VARCHAR[])

### Gold Layer Modifications

#### Wikipedia Gold Enricher Changes

1. **Pass through neighborhood fields**
   - Include all neighborhood fields from Silver layer
   - Add to search_facets for filtering

2. **Create neighborhood search categories**
   - 'has_neighborhood': Articles with neighborhood associations
   - 'no_neighborhood': Articles without associations
   - 'multi_neighborhood': Articles associated with multiple neighborhoods

3. **Enhance embedding text**
   - Optionally append primary_neighborhood_name to embedding_text
   - Improves semantic search for neighborhood-specific queries

## Data Flow Architecture

```
Bronze Layer:
  bronze_neighborhoods → [wikipedia_correlations with page_id]
  bronze_wikipedia → [page_id, title, content]
                ↓
Silver Layer:
  1. silver_neighborhoods created with wikipedia_page_id extracted
  2. Build neighborhood mapping: page_id → [neighborhoods]
  3. silver_wikipedia enriched with neighborhood data via JOIN
                ↓
Gold Layer:
  gold_wikipedia → Includes neighborhood fields for business search
```

## Benefits

1. **Direct Searchability**: Wikipedia articles immediately searchable by neighborhood name
2. **Simple Implementation**: Single JOIN operation in Silver layer
3. **No Complex Logic**: Pure denormalization, no business rules
4. **Backwards Compatible**: Existing fields unchanged, only additions
5. **Performance**: No runtime JOINs needed for neighborhood searches

## Constraints and Considerations

### One-to-Many Relationships

Some Wikipedia articles may be associated with multiple neighborhoods. The solution handles this through:
- Array fields for multiple values
- Primary neighborhood designation for display

### NULL Handling

Many Wikipedia articles have no neighborhood associations. These will have:
- NULL or empty arrays in neighborhood fields
- Proper handling in Gold layer categorization
- No impact on existing functionality

### Data Consistency

Updates to neighborhood associations require:
- Re-running Silver layer transformation
- No complex synchronization needed
- Simple full refresh approach

## Implementation Status

### ✅ Phase 1: Silver Layer Implementation - COMPLETED

**Status**: Successfully implemented and tested on 2025-09-04

**Completed Tasks**:
- ✅ Modified wikipedia.py in silver layer to extract neighborhood mappings
- ✅ Created neighborhood mapping extraction logic with Pydantic models
- ✅ Implemented LEFT JOIN with wikipedia articles using DuckDB Relation API
- ✅ Added new neighborhood columns (neighborhood_names, primary_neighborhood_name, neighborhood_ids)
- ✅ Handled NULL and multiple-value cases gracefully
- ✅ Updated table schema documentation in module docstrings

**Files Modified**:
- `/squack_pipeline_v2/silver/wikipedia.py` - Added neighborhood enrichment functionality
- `/squack_pipeline_v2/models/pipeline/neighborhood_mapping.py` - Created Pydantic models for mappings
- `/squack_pipeline_v2/integration_tests/test_wikipedia_neighborhood_enrichment.py` - Created comprehensive integration tests

**Test Results**:
- All 3 integration tests passing
- Verified handling of multiple neighborhoods per article
- Verified graceful handling when neighborhoods table is missing

### ✅ Phase 2: Gold Layer Enhancement - COMPLETED

**Status**: Successfully implemented and tested on 2025-09-04

**Completed Tasks**:
- ✅ Modified wikipedia.py in gold layer to include neighborhood fields
- ✅ Added neighborhood fields to view projection (neighborhood_ids, neighborhood_names, primary_neighborhood_name)
- ✅ Created neighborhood-based search facet categories (has_neighborhood, no_neighborhood, multi_neighborhood)
- ✅ Updated search_facets array to include neighborhood filters
- ✅ Enhanced article quality scoring with +0.1 boost for neighborhood presence, +0.05 additional for multiple neighborhoods
- ✅ Added neighborhood component (15% weight) to search ranking score
- ✅ Documented new fields in Gold view with processing version update

**Files Modified**:
- `/squack_pipeline_v2/gold/wikipedia.py` - Enhanced with neighborhood-based enrichments
- `/squack_pipeline_v2/utils/gold_enrichment.py` - Created modular utilities for Gold layer enrichment
- `/squack_pipeline_v2/integration_tests/test_gold_neighborhood_enrichment.py` - Created comprehensive Gold layer tests

**Implementation Details**:
- **Search Facets**: Added neighborhood association status to enable filtering by neighborhood presence
- **Quality Boost**: Articles with neighborhoods receive 0.1-0.15 boost to quality score
- **Search Ranking**: 15% of search ranking score now based on neighborhood presence
- **Metadata Fields**: Added neighborhood_count and has_neighborhood_association fields

**Test Results**:
- All 4 Gold layer integration tests passing
- Verified search facets include neighborhood filters  
- Confirmed quality score boosting works correctly
- Validated search ranking includes neighborhood component

---

## Implementation Plan

### Phase 1: Silver Layer Implementation

**Objective**: Implement the core denormalization in the Silver layer

**Tasks**:
- Modify wikipedia.py in silver layer
- Create neighborhood mapping extraction logic
- Implement LEFT JOIN with wikipedia articles
- Add new neighborhood columns to output
- Handle NULL and multiple-value cases
- Update table schema documentation

### Phase 2: Gold Layer Enhancement

**Objective**: Expose neighborhood data for business use

**Tasks**:
- Modify wikipedia.py in gold layer
- Add neighborhood fields to view projection
- Create neighborhood-based categories
- Update search_facets with neighborhood filters
- Enhance quality scoring with neighborhood presence
- Document new fields in Gold view

### Phase 3: Testing and Validation

**Objective**: Ensure data quality and correctness

**Tasks**:
- Create unit tests for Silver layer changes
- Create unit tests for Gold layer changes  
- Test NULL handling and edge cases
- Validate multi-neighborhood associations
- Test search functionality with neighborhood filters
- Performance testing with full dataset

### Phase 4: Integration Testing

**Objective**: Verify end-to-end pipeline functionality

**Tasks**:
- Run full pipeline with test data
- Verify Bronze → Silver → Gold flow
- Test with real neighborhood data
- Validate embedding generation still works
- Check Elasticsearch export functionality
- Verify search results include neighborhood data

### Phase 5: Documentation and Deployment

**Objective**: Complete documentation and deploy changes

**Tasks**:
- Update pipeline documentation
- Document new field definitions
- Create example queries showing neighborhood search
- Update data dictionary
- Deploy to production environment
- Monitor initial runs for issues

### Phase 6: Code Review and Final Testing

**Objective**: Ensure code quality and system stability

**Tasks**:
- Conduct thorough code review
- Run regression tests on existing functionality
- Validate performance metrics
- Test error handling and recovery
- Verify logging and monitoring
- Final acceptance testing with stakeholders

## Success Criteria

1. **Functional**: Wikipedia articles contain neighborhood data in Gold layer
2. **Searchable**: Articles can be filtered by neighborhood name
3. **Complete**: All neighborhood associations properly mapped
4. **Performant**: No significant pipeline performance degradation
5. **Quality**: No data loss or corruption in existing fields

## Risk Mitigation

### Risk 1: Data Volume
- **Mitigation**: Use efficient DuckDB array operations

### Risk 2: Multiple Neighborhoods per Article
- **Mitigation**: Use array fields and proper aggregation

### Risk 3: Performance Impact
- **Mitigation**: Single JOIN operation, no nested queries

### Risk 4: Breaking Changes
- **Mitigation**: Only additive changes, no field modifications

## Conclusion

This proposal provides a straightforward solution to enrich Wikipedia articles with neighborhood data through simple denormalization in the Silver layer. The approach is direct, efficient, and maintains compatibility while enabling powerful new search capabilities.