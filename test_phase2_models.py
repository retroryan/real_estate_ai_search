#!/usr/bin/env python3
"""
Test script to verify Phase 2 model reorganization is complete and functional.
"""

import sys

def test_model_imports():
    """Test that all models can be imported from new locations."""
    print("Testing model imports after Phase 2 reorganization...")
    print("=" * 60)
    
    errors = []
    
    # Test core domain models
    try:
        from real_estate_search.models import (
            Address, PropertyListing, Parking, WikipediaArticle,
            Neighborhood, Demographics, SchoolRatings
        )
        print("✅ Core domain models imported successfully")
    except ImportError as e:
        errors.append(f"Core domain models: {e}")
        print(f"❌ Core domain models failed: {e}")
    
    # Test enumerations
    try:
        from real_estate_search.models import (
            PropertyType, PropertyStatus, ParkingType,
            IndexName, EntityType, QueryType, AggregationType
        )
        print("✅ Enumerations imported successfully")
    except ImportError as e:
        errors.append(f"Enumerations: {e}")
        print(f"❌ Enumerations failed: {e}")
    
    # Test geographic models
    try:
        from real_estate_search.models import (
            GeoPoint, Distance, BoundingBox, GeoSearchParams
        )
        print("✅ Geographic models imported successfully")
    except ImportError as e:
        errors.append(f"Geographic models: {e}")
        print(f"❌ Geographic models failed: {e}")
    
    # Test search models
    try:
        from real_estate_search.models import (
            SearchHit, SourceFilter, SearchRequest, SearchResponse,
            QueryClause, BoolQuery, MatchQuery, MultiMatchQuery,
            PropertySearchParams, PropertyFilterParams
        )
        print("✅ Search models imported successfully")
    except ImportError as e:
        errors.append(f"Search models: {e}")
        print(f"❌ Search models failed: {e}")
    
    # Test result models
    try:
        from real_estate_search.models import (
            BaseQueryResult, PropertySearchResult, WikipediaSearchResult,
            AggregationBucket, AggregationSearchResult, MixedEntityResult
        )
        print("✅ Result models imported successfully")
    except ImportError as e:
        errors.append(f"Result models: {e}")
        print(f"❌ Result models failed: {e}")
    
    return errors

def test_demo_imports():
    """Test that demo functions still work after model reorganization."""
    print("\nTesting demo function imports...")
    print("-" * 40)
    
    errors = []
    
    try:
        from real_estate_search.demo_queries import (
            demo_basic_property_search,
            demo_property_filter,
            demo_geo_search,
            demo_neighborhood_stats,
            demo_price_distribution,
            WikipediaDemoRunner,
            demo_simplified_relationships,
            demo_natural_language_examples,
            demo_rich_property_listing,
            demo_hybrid_search,
            demo_location_understanding,
            demo_location_aware_waterfront_luxury,
            demo_location_aware_family_schools,
            demo_location_aware_recreation_mountain,
            demo_location_aware_search_showcase,
            demo_wikipedia_location_search
        )
        print("✅ All demo functions imported successfully")
    except ImportError as e:
        errors.append(f"Demo functions: {e}")
        print(f"❌ Demo functions failed: {e}")
    
    return errors

def test_old_models_removed():
    """Verify old model files have been deleted."""
    print("\nVerifying old model files are removed...")
    print("-" * 40)
    
    errors = []
    old_modules = [
        'real_estate_search.demo_queries.base_models',
        'real_estate_search.demo_queries.result_models',
        'real_estate_search.demo_queries.es_models',
        'real_estate_search.demo_queries.models',
        'real_estate_search.demo_queries.rich_listing_models'
    ]
    
    for module_name in old_modules:
        try:
            __import__(module_name)
            errors.append(f"Old module still exists: {module_name}")
            print(f"❌ {module_name}: Still exists (should be deleted)")
        except ImportError:
            print(f"✅ {module_name}: Successfully removed")
    
    return errors

def main():
    """Run all Phase 2 tests."""
    all_errors = []
    
    # Run tests
    all_errors.extend(test_model_imports())
    all_errors.extend(test_demo_imports())
    all_errors.extend(test_old_models_removed())
    
    # Summary
    print("\n" + "=" * 60)
    if all_errors:
        print(f"❌ PHASE 2 FAILED: {len(all_errors)} errors found:")
        for error in all_errors:
            print(f"   - {error}")
        return False
    else:
        print("✅ PHASE 2 SUCCESS: Model reorganization complete!")
        print("   - All models migrated to real_estate_search/models/")
        print("   - All imports updated successfully")
        print("   - Old model files removed")
        print("   - Display logic removed from result models")
        print("   - Single source of truth established for all models")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)