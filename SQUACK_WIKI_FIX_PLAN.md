# SQUACK Pipeline Wikipedia Fix - Implementation Plan

## Problem Summary
Wikipedia documents indexed by squack_pipeline lack the fields required by the enrichment command:
- `article_filename` (mapped from `html_file`)
- `content_loaded` (boolean flag)

## Solution: Clean, Direct Fix to WikipediaTransformer

### Core Requirements
✅ **FIX THE CORE ISSUE** - Add missing fields in WikipediaTransformer  
✅ **COMPLETE CHANGE** - Single atomic update to transformer  
✅ **CLEAN IMPLEMENTATION** - Direct field additions, no wrappers  
✅ **NO MIGRATION PHASES** - Fix it once, fix it right  
✅ **NO COMPATIBILITY LAYERS** - Direct transformer update only  
✅ **USE PYDANTIC** - Maintain type safety  
✅ **CLEAN CODE** - Simple, readable, maintainable  

### What We Will NOT Do
❌ Create "EnhancedWikipediaTransformer" or "ImprovedWikipediaTransformer"  
❌ Use hasattr checks for field existence  
❌ Create wrapper functions or abstraction layers  
❌ Add migration or compatibility code  
❌ Create backup copies of old code  

## Implementation Tasks

### Task 1: Update WikipediaTransformer
**File**: `squack_pipeline/transformers/wikipedia_transformer.py`

**Changes**:
1. Add `article_filename` field mapping from `html_file`
2. Add `content_loaded` field with default value `False`
3. Ensure both fields are included in output document

**Specific Updates**:
```python
# In transform() method, after line 63 (doc['id'] assignment):
doc['article_filename'] = wikipedia_data.get('html_file')  # Map html_file to article_filename
doc['content_loaded'] = False  # Default to not loaded

# These fields will be included in the final document after None removal
```

### Task 2: Verify Field Propagation
No changes needed - fields already propagate through all tiers:
- ✅ Bronze: Loads from source (has html_file if in source)
- ✅ Silver: Passes through html_file (line 94)
- ✅ Gold: Passes through html_file (line 117)
- 🔧 Transformer: Needs to map html_file → article_filename

### Task 3: Create Integration Test
**File**: `squack_pipeline/tests/test_wikipedia_enrichment_fields.py`

Test that:
1. WikipediaTransformer includes `article_filename` field
2. WikipediaTransformer includes `content_loaded` field
3. Fields have correct values and types

### Task 4: Update Documentation
**File**: `squack_pipeline/transformers/wikipedia_transformer.py` (docstring)

Update the class and method docstrings to document:
- Mapping of html_file to article_filename
- Addition of content_loaded field

## File Changes Summary

### Files to Modify
1. `squack_pipeline/transformers/wikipedia_transformer.py` - Add field mappings

### Files to Create
1. `squack_pipeline/tests/test_wikipedia_enrichment_fields.py` - Integration test

### Files NOT Changed
- ❌ WikipediaLoader - Already correct
- ❌ WikipediaSilverProcessor - Already correct  
- ❌ WikipediaGoldProcessor - Already correct
- ❌ ElasticsearchWriter - No changes needed
- ❌ Base classes - No changes needed

## Testing Plan

### Manual Testing Steps
1. Clear Wikipedia index: `curl -X DELETE "localhost:9200/wikipedia"`
2. Run pipeline with small sample: `python -m squack_pipeline run --sample-size 5 --entities wikipedia`
3. Check indexed documents have required fields:
   ```bash
   curl -X GET "localhost:9200/wikipedia/_search?size=1&pretty" | grep -E "(article_filename|content_loaded)"
   ```
4. Run enrichment command: `python -m real_estate_search.management enrich-wikipedia`
5. Verify documents are found for enrichment

### Automated Test Coverage
- Unit test for WikipediaTransformer field mapping
- Integration test for end-to-end field propagation
- Validation that Elasticsearch documents contain required fields

## Success Criteria

✅ Wikipedia documents in Elasticsearch have `article_filename` field  
✅ Wikipedia documents in Elasticsearch have `content_loaded: false` field  
✅ Enrichment command finds documents needing enrichment  
✅ No breaking changes to existing functionality  
✅ Clean, maintainable code without hacks  

## Implementation Order

1. **Update WikipediaTransformer** (5 minutes)
   - Add two field mappings
   - Update docstring

2. **Create test file** (10 minutes)
   - Write integration test
   - Ensure field presence and values

3. **Manual verification** (5 minutes)
   - Run pipeline
   - Check Elasticsearch
   - Run enrichment command

## Risk Assessment

**Low Risk** - Changes are:
- Additive only (new fields, no removals)
- Localized to one transformer
- Easy to test and verify
- Reversible if needed

## Notes

The fix is intentionally minimal and surgical. We're only adding the two missing fields that connect the indexing pipeline to the enrichment workflow. The `html_file` field already flows through all processing tiers correctly - we just need to map it to the expected field name and add the enrichment status flag.

This approach maintains the original two-phase architecture (index then enrich) while fixing the broken connection between phases.