# Elasticsearch Configuration

This directory contains Elasticsearch configuration files in pure JSON format, following enterprise best practices.

## Structure

```
elasticsearch/
├── settings/
│   └── analyzers.json     # Index settings and analyzers
└── templates/
    └── properties.json    # Field mappings for properties index
```

## Files

### settings/analyzers.json
Contains Elasticsearch index settings including:
- Custom analyzers (property_analyzer, address_analyzer, feature_analyzer, wikipedia_analyzer)
- Normalizers (lowercase_normalizer)
- Custom filters (shingle)
- Index settings (shards, replicas, refresh_interval)

### templates/properties.json
Contains field mappings for the properties index including:
- Core property fields (listing_id, price, bedrooms, etc.)
- Address and location fields with geo_point support
- Wikipedia enrichment fields (location_context, neighborhood_context, nearby_poi)
- Search optimization fields

## Usage

The mappings are loaded automatically by the `real_estate_search.indexer.mappings` module:

```python
from real_estate_search.indexer.mappings import get_property_mappings

# This loads settings from analyzers.json and mappings from properties.json
mappings = get_property_mappings()
```

## Benefits

- **Separation of Concerns**: Configuration is separate from code
- **Version Control Friendly**: JSON files can be easily diffed and reviewed
- **Enterprise Ready**: No dynamic generation or environment-specific logic
- **Maintainable**: Easy to modify without touching Python code
- **Deterministic**: Same configuration every time