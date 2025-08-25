"""
Feature enrichment utilities.

Provides functions for normalizing and deduplicating features and amenities.
"""

from typing import List, Optional

from ..utils.logger import setup_logger
from ..utils.config import get_settings

logger = setup_logger(__name__)


def normalize_feature_list(features: Optional[List[str]]) -> List[str]:
    """
    Normalize a list of features by deduplicating, lowercasing, and sorting.
    
    Args:
        features: List of feature strings
        
    Returns:
        Normalized list of features
    """
    if not features:
        return []
    
    settings = get_settings()
    
    # Convert to lowercase if configured
    if settings.enrichment.normalize_features_to_lowercase:
        features = [f.lower().strip() for f in features if f and f.strip()]
    else:
        features = [f.strip() for f in features if f and f.strip()]
    
    # Deduplicate if configured
    if settings.enrichment.deduplicate_features:
        features = list(set(features))
    
    # Sort if configured
    if settings.enrichment.sort_features:
        features = sorted(features)
    
    logger.debug(f"Normalized {len(features)} features")
    return features


def extract_features_from_description(description: Optional[str]) -> List[str]:
    """
    Extract potential features from a property description.
    
    Args:
        description: Property description text
        
    Returns:
        List of extracted features
    """
    if not description:
        return []
    
    # Common feature keywords to look for
    feature_keywords = [
        'pool', 'garage', 'garden', 'patio', 'deck', 'balcony',
        'fireplace', 'hardwood', 'granite', 'stainless steel',
        'walk-in closet', 'master suite', 'open floor plan',
        'updated kitchen', 'renovated', 'new roof', 'solar panels',
        'smart home', 'security system', 'gated', 'waterfront',
        'mountain view', 'city view', 'ocean view'
    ]
    
    description_lower = description.lower()
    found_features = []
    
    for keyword in feature_keywords:
        if keyword in description_lower:
            found_features.append(keyword)
    
    return found_features


def merge_feature_lists(*feature_lists: List[str]) -> List[str]:
    """
    Merge multiple feature lists into one normalized list.
    
    Args:
        *feature_lists: Variable number of feature lists
        
    Returns:
        Merged and normalized feature list
    """
    all_features = []
    for feature_list in feature_lists:
        if feature_list:
            all_features.extend(feature_list)
    
    return normalize_feature_list(all_features)