"""
Configuration resolver utilities.

This module provides utilities for resolving paths and validating
configuration values.
"""

from pathlib import Path
from typing import List, Optional


def resolve_path(path: str, base_dir: Optional[Path] = None) -> str:
    """
    Resolve a single path to absolute.
    
    Args:
        path: Path string to resolve
        base_dir: Base directory for relative paths (defaults to cwd)
        
    Returns:
        Absolute path string
    """
    if base_dir is None:
        base_dir = Path.cwd()
    
    p = Path(path)
    if p.is_absolute():
        return str(p)
    return str(base_dir / p)


def resolve_paths(paths: List[str], base_dir: Optional[Path] = None) -> List[str]:
    """
    Resolve a list of paths to absolute.
    
    Args:
        paths: List of path strings to resolve
        base_dir: Base directory for relative paths (defaults to cwd)
        
    Returns:
        List of absolute path strings
    """
    return [resolve_path(p, base_dir) for p in paths]


def validate_input_paths(paths: List[str]) -> bool:
    """
    Validate that input paths exist.
    
    Args:
        paths: List of input file paths
        
    Returns:
        True if all paths exist
        
    Raises:
        FileNotFoundError: If any path doesn't exist
    """
    missing = []
    for path in paths:
        p = Path(path)
        if not p.exists():
            missing.append(str(p))
    
    if missing:
        raise FileNotFoundError(f"Input files not found: {', '.join(missing)}")
    
    return True


def ensure_output_directory(path: str) -> str:
    """
    Ensure output directory exists, creating if necessary.
    
    Args:
        path: Output directory path
        
    Returns:
        Absolute path to output directory
    """
    p = Path(path)
    if not p.is_absolute():
        p = Path.cwd() / p
    
    p.mkdir(parents=True, exist_ok=True)
    return str(p)