"""
Utility functions for demo query formatting and display.
"""

from typing import List, Dict, Any, Optional


def format_demo_header(
    demo_name: str,
    search_description: str,
    es_features: List[str],
    indexes_used: List[str],
    document_count: Optional[str] = None
) -> str:
    """
    Format a consistent header for demo queries with overview information.
    
    Args:
        demo_name: Name of the demo
        search_description: Brief description of what the demo searches for
        es_features: List of Elasticsearch features demonstrated
        indexes_used: List of indexes being queried
        document_count: Optional description of document counts
        
    Returns:
        Formatted header string
    """
    output = []
    output.append("\n" + "=" * 80)
    output.append(f"🔍 {demo_name}")
    output.append("=" * 80)
    output.append(f"\n📝 SEARCH DESCRIPTION:")
    output.append(f"   {search_description}")
    
    output.append(f"\n📊 ELASTICSEARCH FEATURES:")
    for feature in es_features:
        output.append(f"   • {feature}")
    
    output.append(f"\n📁 INDEXES & DOCUMENTS:")
    for index in indexes_used:
        output.append(f"   • {index}")
    
    if document_count:
        output.append(f"\n📈 SCALE:")
        output.append(f"   {document_count}")
    
    output.append("-" * 80)
    
    return "\n".join(output)


def add_demo_overview(result: Dict[str, Any], overview_text: str) -> Dict[str, Any]:
    """
    Add an overview section to demo results.
    
    Args:
        result: Demo query result dictionary
        overview_text: Overview text to add
        
    Returns:
        Updated result dictionary
    """
    if "_overview" not in result:
        result["_overview"] = overview_text
    return result