"""
Elasticsearch index mappings and settings.
Defines how property data is indexed and searched.
"""

from typing import Dict, Any
from .enums import FieldName, AnalyzerName


def get_property_mappings() -> Dict[str, Any]:
    """
    Get complete index mappings for properties.
    
    Returns:
        Dictionary containing settings and mappings for Elasticsearch index.
    """
    return {
        "settings": _get_index_settings(),
        "mappings": _get_field_mappings()
    }


def _get_index_settings() -> Dict[str, Any]:
    """
    Get index settings including analyzers and normalizers.
    
    Returns:
        Dictionary of index settings.
    """
    return {
        "number_of_shards": 1,
        "number_of_replicas": 1,
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
            }
        }
    }


def _get_field_mappings() -> Dict[str, Any]:
    """
    Get field mappings for property documents.
    
    Returns:
        Dictionary of field mappings.
    """
    return {
        "properties": {
            FieldName.LISTING_ID: {
                "type": "keyword"
            },
            FieldName.PROPERTY_TYPE: {
                "type": "keyword",
                "normalizer": "lowercase_normalizer"
            },
            FieldName.PRICE: {
                "type": "float"  # Changed from scaled_float for better performance
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
                "type": "float"  # Changed from scaled_float for better performance
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
                "doc_values": False  # Not used for sorting/aggregations, save disk space
            },
            FieldName.IMAGES: {
                "type": "keyword",
                "index": False,
                "doc_values": False  # Not used for sorting/aggregations, save disk space
            },
            FieldName.MLS_NUMBER: {
                "type": "keyword"
            },
            FieldName.TAX_ASSESSED_VALUE: {
                "type": "long"
            },
            FieldName.ANNUAL_TAX: {
                "type": "float"  # Changed from scaled_float for better performance
            },
            FieldName.SEARCH_TAGS: {
                "type": "text",
                "analyzer": AnalyzerName.PROPERTY_ANALYZER
            }
        }
    }


# Export the main function
PROPERTY_MAPPINGS = get_property_mappings()