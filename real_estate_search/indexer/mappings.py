"""
Elasticsearch mappings with Wikipedia integration.
Includes Wikipedia-derived fields for enriched property search.
"""

import json
import os
from typing import Dict, Any
from pathlib import Path


def get_property_mappings() -> Dict[str, Any]:
    """
    Get index mappings including Wikipedia enrichment fields.
    
    Returns:
        Dictionary containing settings and mappings for Wikipedia-enriched index.
    """
    return {
        "settings": _load_index_settings(),
        "mappings": _load_field_mappings()
    }


def _load_index_settings() -> Dict[str, Any]:
    """
    Load index settings from JSON file.
    
    Returns:
        Dictionary of index settings.
    """
    settings_path = _get_settings_path("analyzers.json")
    return _load_json_file(settings_path)


def _load_field_mappings() -> Dict[str, Any]:
    """
    Load field mappings from JSON file.
    
    Returns:
        Dictionary of field mappings.
    """
    mappings_path = _get_templates_path("properties.json")
    return _load_json_file(mappings_path)


def _get_settings_path(filename: str) -> Path:
    """Get path to settings JSON file."""
    current_dir = Path(__file__).parent
    elasticsearch_dir = current_dir.parent / "elasticsearch" / "settings"
    return elasticsearch_dir / filename


def _get_templates_path(filename: str) -> Path:
    """Get path to templates JSON file."""
    current_dir = Path(__file__).parent
    elasticsearch_dir = current_dir.parent / "elasticsearch" / "templates"
    return elasticsearch_dir / filename


def _load_json_file(file_path: Path) -> Dict[str, Any]:
    """
    Load JSON file with error handling.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Dictionary loaded from JSON file
        
    Raises:
        FileNotFoundError: If JSON file doesn't exist
        ValueError: If JSON is invalid
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Elasticsearch configuration file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {str(e)}")


# Export the mappings
PROPERTY_MAPPINGS = get_property_mappings()