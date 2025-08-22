"""
Elasticsearch mappings with Wikipedia integration.
Includes Wikipedia-derived fields for enriched property search.
"""

from typing import Dict, Any
from .enums import FieldName, AnalyzerName


def get_property_mappings() -> Dict[str, Any]:
    """
    Get index mappings including Wikipedia enrichment fields.
    
    Returns:
        Dictionary containing settings and mappings for Wikipedia-enriched index.
    """
    return {
        "settings": _get_index_settings(),
        "mappings": _get_field_mappings()
    }


def _get_index_settings() -> Dict[str, Any]:
    """
    Get index settings with optimized analyzers for Wikipedia content.
    
    Returns:
        Dictionary of index settings.
    """
    return {
        "number_of_shards": 1,
        "number_of_replicas": 0,  # Demo mode - no replicas needed
        "refresh_interval": "1s",
        "analysis": {
            "analyzer": {
                AnalyzerName.PROPERTY_ANALYZER: {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "stop",
                        "snowball"
                    ]
                },
                AnalyzerName.ADDRESS_ANALYZER: {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "asciifolding"
                    ]
                },
                AnalyzerName.FEATURE_ANALYZER: {
                    "type": "custom",
                    "tokenizer": "keyword",
                    "filter": [
                        "lowercase"
                    ]
                },
                # New analyzer for Wikipedia content
                "wikipedia_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "stop",
                        "snowball",
                        "shingle"  # For phrase matching
                    ]
                }
            },
            "normalizer": {
                "lowercase_normalizer": {
                    "type": "custom",
                    "filter": [
                        "lowercase",
                        "asciifolding"
                    ]
                }
            },
            "filter": {
                "shingle": {
                    "type": "shingle",
                    "min_shingle_size": 2,
                    "max_shingle_size": 3
                }
            }
        }
    }


def _get_field_mappings() -> Dict[str, Any]:
    """
    Get field mappings including Wikipedia enrichment fields.
    
    Returns:
        Dictionary of field mappings.
    """
    # Start with base property fields
    base_fields = _get_base_property_fields()
    
    # Add Wikipedia enhancement fields
    wikipedia_fields = _get_wikipedia_enhancement_fields()
    
    return {
        "properties": {
            **base_fields,
            **wikipedia_fields
        }
    }


def _get_base_property_fields() -> Dict[str, Any]:
    """Get base property fields (original mappings)."""
    return {
        FieldName.LISTING_ID: {
            "type": "keyword"
        },
        FieldName.PROPERTY_TYPE: {
            "type": "keyword",
            "normalizer": "lowercase_normalizer"
        },
        FieldName.PRICE: {
            "type": "float"
        },
        FieldName.BEDROOMS: {
            "type": "short"
        },
        FieldName.BATHROOMS: {
            "type": "half_float"
        },
        FieldName.SQUARE_FEET: {
            "type": "integer"
        },
        FieldName.YEAR_BUILT: {
            "type": "short"
        },
        FieldName.LOT_SIZE: {
            "type": "integer"
        },
        FieldName.ADDRESS: {
            "type": "object",
            "properties": {
                "street": {
                    "type": "text",
                    "analyzer": AnalyzerName.ADDRESS_ANALYZER,
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "city": {
                    "type": "keyword",
                    "normalizer": "lowercase_normalizer"
                },
                "state": {
                    "type": "keyword"
                },
                "zip_code": {
                    "type": "keyword"
                },
                "location": {
                    "type": "geo_point"
                }
            }
        },
        FieldName.NEIGHBORHOOD: {
            "type": "object",
            "properties": {
                "id": {
                    "type": "keyword"
                },
                "name": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword"
                        }
                    }
                },
                "walkability_score": {
                    "type": "byte"
                },
                "school_rating": {
                    "type": "half_float"
                }
            }
        },
        FieldName.DESCRIPTION: {
            "type": "text",
            "analyzer": AnalyzerName.PROPERTY_ANALYZER,
            "fields": {
                "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                }
            }
        },
        FieldName.FEATURES: {
            "type": "keyword",
            "normalizer": "lowercase_normalizer"
        },
        FieldName.AMENITIES: {
            "type": "keyword",
            "normalizer": "lowercase_normalizer"
        },
        FieldName.STATUS: {
            "type": "keyword"
        },
        FieldName.LISTING_DATE: {
            "type": "date"
        },
        FieldName.LAST_UPDATED: {
            "type": "date"
        },
        FieldName.DAYS_ON_MARKET: {
            "type": "integer"
        },
        FieldName.PRICE_PER_SQFT: {
            "type": "float"
        },
        FieldName.HOA_FEE: {
            "type": "float"
        },
        "parking": {
            "type": "object",
            "properties": {
                "spaces": {
                    "type": "byte"
                },
                "type": {
                    "type": "keyword"
                }
            }
        },
        FieldName.VIRTUAL_TOUR_URL: {
            "type": "keyword",
            "index": False,
            "doc_values": False
        },
        FieldName.IMAGES: {
            "type": "keyword",
            "index": False,
            "doc_values": False
        },
        FieldName.MLS_NUMBER: {
            "type": "keyword"
        },
        FieldName.TAX_ASSESSED_VALUE: {
            "type": "long"
        },
        FieldName.ANNUAL_TAX: {
            "type": "float"
        },
        FieldName.SEARCH_TAGS: {
            "type": "text",
            "analyzer": AnalyzerName.PROPERTY_ANALYZER
        }
    }


def _get_wikipedia_enhancement_fields() -> Dict[str, Any]:
    """Get Wikipedia enhancement fields."""
    return {
        # Location context from Wikipedia
        "location_context": {
            "type": "object",
            "properties": {
                "wikipedia_page_id": {"type": "keyword"},
                "wikipedia_title": {
                    "type": "text",
                    "analyzer": "wikipedia_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "location_summary": {
                    "type": "text",
                    "analyzer": "wikipedia_analyzer"
                },
                "historical_significance": {
                    "type": "text",
                    "analyzer": "wikipedia_analyzer"
                },
                "key_topics": {
                    "type": "keyword",
                    "normalizer": "lowercase_normalizer"
                },
                "landmarks": {
                    "type": "nested",
                    "properties": {
                        "name": {
                            "type": "text",
                            "fields": {
                                "keyword": {"type": "keyword"}
                            }
                        },
                        "wikipedia_page_id": {"type": "keyword"},
                        "category": {"type": "keyword"},
                        "distance_miles": {"type": "float"},
                        "significance_score": {"type": "float"},
                        "description": {
                            "type": "text",
                            "analyzer": "wikipedia_analyzer"
                        }
                    }
                },
                "cultural_features": {
                    "type": "keyword",
                    "normalizer": "lowercase_normalizer"
                },
                "recreational_features": {
                    "type": "keyword",
                    "normalizer": "lowercase_normalizer"
                },
                "transportation": {
                    "type": "keyword",
                    "normalizer": "lowercase_normalizer"
                },
                "location_type": {"type": "keyword"},
                "confidence_score": {"type": "float"}
            }
        },
        
        # Neighborhood context from Wikipedia
        "neighborhood_context": {
            "type": "object",
            "properties": {
                "wikipedia_page_id": {"type": "keyword"},
                "wikipedia_title": {
                    "type": "text",
                    "analyzer": "wikipedia_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "description": {
                    "type": "text",
                    "analyzer": "wikipedia_analyzer"
                },
                "history": {
                    "type": "text",
                    "analyzer": "wikipedia_analyzer"
                },
                "character": {
                    "type": "text",
                    "analyzer": "wikipedia_analyzer"
                },
                "notable_residents": {
                    "type": "keyword"
                },
                "architectural_style": {
                    "type": "keyword",
                    "normalizer": "lowercase_normalizer"
                },
                "establishment_year": {"type": "integer"},
                "gentrification_index": {"type": "float"},
                "diversity_score": {"type": "float"},
                "key_topics": {
                    "type": "keyword",
                    "normalizer": "lowercase_normalizer"
                }
            }
        },
        
        # Points of Interest from Wikipedia
        "nearby_poi": {
            "type": "nested",
            "properties": {
                "name": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "wikipedia_page_id": {"type": "keyword"},
                "category": {"type": "keyword"},
                "distance_miles": {"type": "float"},
                "walking_time_minutes": {"type": "integer"},
                "significance_score": {"type": "float"},
                "description": {
                    "type": "text",
                    "analyzer": "wikipedia_analyzer"
                },
                "key_topics": {
                    "type": "keyword",
                    "normalizer": "lowercase_normalizer"
                }
            }
        },
        
        # Enriched search text combining all Wikipedia data
        "enriched_search_text": {
            "type": "text",
            "analyzer": "wikipedia_analyzer"
        },
        
        # Location quality scores
        "location_scores": {
            "type": "object",
            "properties": {
                "cultural_richness": {"type": "float"},
                "historical_importance": {"type": "float"},
                "tourist_appeal": {"type": "float"},
                "local_amenities": {"type": "float"},
                "overall_desirability": {"type": "float"}
            }
        }
    }


# Export the mappings
PROPERTY_MAPPINGS = get_property_mappings()