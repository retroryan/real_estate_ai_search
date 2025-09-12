# Geographic Fields Cleanup Proposal

## What to Remove

### From Neighborhood Model (`real_estate_search/models/neighborhood.py`)

**Remove these fields:**
- `boundaries` field - Not used anywhere in the codebase
- `area_sqmi` field - Not used anywhere in the codebase

### Complete File Removal

**Delete this entire file:**
- `real_estate_search/models/geojson.py` - Contains unused classes:
  - GeoJSONPoint
  - GeoJSONPolygon  
  - GeoJSONMultiPolygon
  - GeoJSONBoundingBox
  - GeographicBoundaries

## Why It's Safe to Remove

- No code reads or writes these fields
- Fields are not in Elasticsearch index mappings
- Fields are not in the actual data files
- No tests use these fields or classes
- The geojson module is only imported once for a type hint on an unused field

## What Will Still Work

Everything will continue working exactly the same:
- All neighborhood searches still work
- All geo-distance searches still work (they use the `location` field, not boundaries)
- All data loading still works
- All tests still pass

## Simple Summary

These geographic boundary fields and the geojson module were added but never actually used. They're just sitting there doing nothing. Removing them makes the code cleaner without breaking anything.