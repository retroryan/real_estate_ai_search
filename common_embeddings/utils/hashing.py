"""
Text hashing utilities for duplicate detection.
"""

import hashlib
from typing import Optional


def hash_text(text: str, algorithm: str = "sha256") -> str:
    """
    Generate a hash of the given text.
    
    Args:
        text: Text to hash
        algorithm: Hashing algorithm to use
        
    Returns:
        Hex digest of the hash
    """
    if algorithm == "sha256":
        hasher = hashlib.sha256()
    elif algorithm == "md5":
        hasher = hashlib.md5()
    else:
        raise ValueError(f"Unsupported hashing algorithm: {algorithm}")
    
    hasher.update(text.encode('utf-8'))
    return hasher.hexdigest()


def hash_document(
    text: str,
    metadata: Optional[dict] = None,
    fields: Optional[list] = None
) -> str:
    """
    Generate a hash for a document including optional metadata fields.
    
    Args:
        text: Document text
        metadata: Optional metadata dictionary
        fields: Optional list of metadata fields to include in hash
        
    Returns:
        Hex digest of the combined hash
    """
    components = [text]
    
    if metadata and fields:
        for field in fields:
            if field in metadata:
                components.append(str(metadata[field]))
    
    combined = "|".join(components)
    return hash_text(combined)