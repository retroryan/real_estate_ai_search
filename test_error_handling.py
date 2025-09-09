#!/usr/bin/env python3
"""Test script to verify ElasticsearchIndexError handling."""

import sys
from real_estate_search.indexer.exceptions import ElasticsearchIndexError
from real_estate_search.indexer.enums import ErrorCode

def test_error_handling():
    """Test various error scenarios."""
    
    print("Testing ElasticsearchIndexError handling...")
    
    # Test 1: Error with error code and message
    try:
        raise ElasticsearchIndexError(
            ErrorCode.CONNECTION_ERROR,
            "Elasticsearch client connection failed"
        )
    except ElasticsearchIndexError as e:
        print(f"✓ Test 1 passed: {e}")
        assert str(e) == "[CONNECTION_ERROR] Elasticsearch client connection failed"
        assert e.error_code == ErrorCode.CONNECTION_ERROR
        assert e.message == "Elasticsearch client connection failed"
    
    # Test 2: Error with error code, message, and details
    try:
        raise ElasticsearchIndexError(
            ErrorCode.INDEX_NOT_FOUND,
            "Index 'properties' not found",
            details={"index": "properties", "status": 404}
        )
    except ElasticsearchIndexError as e:
        print(f"✓ Test 2 passed: {e}")
        assert str(e) == "[INDEX_NOT_FOUND] Index 'properties' not found"
        assert e.details == {"index": "properties", "status": 404}
    
    # Test 3: Error with just message (no error code)
    try:
        raise ElasticsearchIndexError(
            message="Generic error message"
        )
    except ElasticsearchIndexError as e:
        print(f"✓ Test 3 passed: {e}")
        assert str(e) == "Generic error message"
        assert e.error_code is None
    
    # Test 4: Test actual usage in index_manager style
    try:
        # Simulate the actual usage pattern from index_manager
        raise ElasticsearchIndexError(
            ErrorCode.CONFIGURATION_ERROR,
            "Failed to register template properties_template: Connection timeout"
        )
    except ElasticsearchIndexError as e:
        print(f"✓ Test 4 passed: {e}")
        assert "[CONFIGURATION_ERROR]" in str(e)
    
    print("\n✅ All error handling tests passed!")
    return True

if __name__ == "__main__":
    try:
        success = test_error_handling()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)