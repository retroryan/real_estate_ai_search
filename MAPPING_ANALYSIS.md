# Field Mapping Analysis - Phase 1

## Executive Summary
This document analyzes the field mismatches between squack_pipeline_v2's Elasticsearch output and what real_estate_search expects to read. The analysis is based on actual code inspection of both systems.

## Properties Index Field Analysis

### Source Data Structure (properties_sf.json)
```
{
  "listing_id": "prop-oak-125",
  "neighborhood_id": "oak-temescal-006",  ✅ EXISTS IN SOURCE
  "address": {
    "street": "2986 Telegraph Court",
    "city": "Oakland",
    "state": "CA",                      ✅ STATE not state_code
    "zip": "94115"
  },
  "coordinates": {
    "latitude": 37.834,
    "longitude": -122.264
  },
  "property_details": {
    "bedrooms": 4,
    "bathrooms": 3.5,
    "square_feet": 1685,
    "property_type": "townhome",
    "garage_spaces": 2
  }
}
```

### Pipeline Processing Status

#### Bronze Layer (✅ CORRECT)
- Loads data AS-IS using read_json_auto
- Preserves ALL fields including neighborhood_id
- No transformations applied

#### Silver Layer (✅ PRESERVES neighborhood_id)
- Line 35: Correctly selects neighborhood_id
- Line 54: Uses address.state (correct field name)
- Flattens property_details to top level
- Creates address structure with location inside

#### Gold Layer (✅ PRESERVES neighborhood_id)
- Line 33: Correctly selects neighborhood_id
- Maintains all required fields
- Creates parking object structure

### Elasticsearch Writer Issues (❌ DROPS CRITICAL FIELDS)

#### PropertyDocument Model (squack_pipeline_v2/writers/elasticsearch.py)
**Current Fields:**
- listing_id ✅
- price ✅
- bedrooms ✅
- bathrooms ✅
- square_feet ✅
- property_type ✅
- city ✅
- **state_code** ❌ (should be "state")
- latitude ✅
- longitude ✅
- **NO neighborhood_id field** ❌ CRITICAL MISSING FIELD
- location (GeoPoint) ✅
- parking ✅

**Missing Fields:**
- **neighborhood_id** - Required for relationship building
- **address** nested object - Expected by search module
- **state** field name (currently state_code)

### What Search Module Expects (real_estate_search)

From elasticsearch/templates/properties.json:
- listing_id (keyword)
- **neighborhood_id** - Expected but not provided
- price (float)
- bedrooms (short)
- bathrooms (half_float)
- address (nested object with):
  - street (text)
  - city (keyword)
  - **state** (keyword) - NOT state_code
  - zip_code (keyword)
  - location (geo_point)

From relationship_builder.py line 231:
```python
if neighborhood_id := prop.get("neighborhood_id"):
    neighborhood_ids.add(neighborhood_id)
```
The relationship builder REQUIRES neighborhood_id to link properties to neighborhoods.

## Neighborhoods Index Field Analysis

### Elasticsearch Writer Issues

#### NeighborhoodDocument Model
**Current Fields:**
- neighborhood_id ✅
- name ✅
- city ✅
- **state_code** ❌ (should be "state")
- center_latitude ✅
- center_longitude ✅

**Field Name Issues:**
- Uses state_code instead of state
- Uses center_latitude/center_longitude instead of location field

### What Search Module Expects

From elasticsearch/templates/neighborhoods.json:
- neighborhood_id (keyword) ✅
- name (text)
- city (keyword)
- **state** (keyword) - NOT state_code
- location (geo_point)

## Wikipedia Index Field Analysis

### Elasticsearch Writer Issues

#### WikipediaDocument Model
**Current Fields:**
- page_id (converted from int to string) ✅
- title ✅
- Most fields aligned correctly

**Minor Issues:**
- Type conversion handled correctly (int to string)

## Field Fixes Required

### Priority 1 - CRITICAL (Breaks Functionality)
1. **Add neighborhood_id to PropertyDocument** - Without this, relationship building cannot work
2. **Change state_code to state in all documents** - Field name mismatch prevents queries
3. **Add address nested object to PropertyDocument** - Expected structure missing

### Priority 2 - IMPORTANT (Structure Mismatch)
4. **Create proper address object with location inside** - Currently flat structure
5. **Fix location field in NeighborhoodDocument** - Use standard geo_point

### Priority 3 - MINOR (Consistency)
6. Ensure all field types match exactly between pipeline and templates

## Root Cause Analysis

The core issue is in the Elasticsearch writer's document models and transformers:

1. **PropertyDocument model doesn't include neighborhood_id field** even though it's preserved through Bronze → Silver → Gold
2. **Field naming inconsistency**: Using state_code when templates expect state
3. **Structure mismatch**: Flat fields instead of nested address object
4. **PropertyTransformer doesn't extract neighborhood_id** from the record

## Solution Path

### Phase 2 Tasks - Data Preservation
- ✅ neighborhood_id already preserved through Bronze/Silver/Gold
- Need to ensure it reaches Elasticsearch writer

### Phase 3 Tasks - Elasticsearch Writer Correction
- Add neighborhood_id field to PropertyDocument model
- Add neighborhood_id to PropertyInput model  
- Update PropertyTransformer.transform() to include neighborhood_id
- Change all state_code fields to state
- Create proper nested address structure
- Update NeighborhoodDocument to use state instead of state_code

### Phase 4 Tasks - Template Alignment
- Templates already correct (they expect the right field names)
- No changes needed to templates

## Validation Checklist

After fixes, verify:
- [ ] neighborhood_id present in Elasticsearch properties index
- [ ] state field (not state_code) in all indices
- [ ] address object properly nested with location inside
- [ ] All field types match templates exactly
- [ ] Relationship builder can find neighborhood_id
- [ ] Relationship builder successfully creates documents

## Conclusion

The fix is straightforward: The pipeline correctly preserves all data through Gold layer, but the Elasticsearch writer drops critical fields and uses wrong field names. The solution requires only updating the Elasticsearch writer's document models and transformers to include all fields with correct names.