#!/usr/bin/env python
"""Run all MCP demos to test functionality."""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from real_estate_search.mcp_demos.demos import (
    demo_basic_property_search,
    demo_property_filter,
    demo_wikipedia_search,
    demo_wikipedia_location_context,
    demo_location_based_discovery,
    demo_multi_entity_search,
    demo_property_details_deep_dive,
    demo_semantic_vs_text_comparison
)
from real_estate_search.mcp_demos.demos.natural_language_demo import (
    demo_natural_language_semantic_search,
    demo_natural_language_examples,
    demo_semantic_vs_keyword_comparison
)


async def run_all_demos():
    """Run all demos and report results."""
    print("="*70)
    print("RUNNING ALL MCP DEMOS - REAL SERVER TEST")
    print("="*70)
    
    demos = [
        ("Basic Property Search", lambda: demo_basic_property_search("modern home")),
        ("Filtered Property Search", lambda: demo_property_filter()),
        ("Wikipedia Search", lambda: demo_wikipedia_search("San Francisco")),
        ("Wikipedia Location Context", lambda: demo_wikipedia_location_context("Oakland", "CA")),
        ("Location-Based Discovery", lambda: demo_location_based_discovery("Oakland", "CA")),
        ("Multi-Entity Search", lambda: demo_multi_entity_search("downtown")),
        ("Property Details Deep Dive", lambda: demo_property_details_deep_dive()),
        ("Search Comparison", lambda: demo_semantic_vs_text_comparison("garden")),
        ("Natural Language Semantic Search", lambda: demo_natural_language_semantic_search("cozy family home near good schools")),
        ("Natural Language Examples", lambda: demo_natural_language_examples()),
        ("Semantic vs Keyword Comparison", lambda: demo_semantic_vs_keyword_comparison("stunning views from modern kitchen"))
    ]
    
    results = []
    
    for name, demo_func in demos:
        print(f"\n{'='*70}")
        print(f"Running: {name}")
        print("="*70)
        
        try:
            result = await demo_func()
            status = "✓ PASSED" if result.success else "✗ FAILED"
            results.append((name, status, result.total_results, result.execution_time_ms))
            print(f"\nResult: {status}")
            print(f"Total Results: {result.total_results}")
            print(f"Execution Time: {result.execution_time_ms}ms")
        except Exception as e:
            results.append((name, "✗ ERROR", 0, 0))
            print(f"\n✗ ERROR: {str(e)[:100]}")
        
        # Small delay between demos
        await asyncio.sleep(0.5)
    
    # Print summary
    print("\n" + "="*70)
    print("DEMO RESULTS SUMMARY")
    print("="*70)
    print(f"{'Demo Name':<35} {'Status':<12} {'Results':<10} {'Time (ms)':<10}")
    print("-"*70)
    
    for name, status, total, time_ms in results:
        print(f"{name:<35} {status:<12} {total:<10} {time_ms:<10}")
    
    passed = sum(1 for _, status, _, _ in results if "PASSED" in status)
    failed = sum(1 for _, status, _, _ in results if "FAILED" in status or "ERROR" in status)
    
    print("-"*70)
    print(f"Total: {len(results)} demos | Passed: {passed} | Failed: {failed}")
    print("="*70)
    
    return passed == len(results)


async def main():
    """Main entry point."""
    all_passed = await run_all_demos()
    
    if all_passed:
        print("\n✅ ALL DEMOS PASSED!")
    else:
        print("\n⚠️  SOME DEMOS FAILED - Check logs above for details")
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())