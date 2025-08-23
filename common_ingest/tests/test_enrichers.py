"""
Test enrichment utilities.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common_ingest.enrichers.address_utils import (
    expand_city_name,
    expand_state_code,
    normalize_address,
    validate_coordinates
)
from common_ingest.enrichers.feature_utils import (
    normalize_feature_list,
    extract_features_from_description,
    merge_feature_lists
)
from common_ingest.utils.logger import setup_logger

logger = setup_logger("test_enrichers")


def test_expand_city_name():
    """Test city name expansion."""
    logger.info("Testing city name expansion...")
    
    # Test abbreviations
    assert expand_city_name("SF") == "San Francisco"
    assert expand_city_name("sf") == "San Francisco"
    assert expand_city_name("PC") == "Park City"
    assert expand_city_name("pc") == "Park City"
    
    # Test full names (should remain unchanged)
    assert expand_city_name("San Francisco") == "San Francisco"
    assert expand_city_name("Park City") == "Park City"
    assert expand_city_name("Los Angeles") == "Los Angeles"
    
    # Test unknown cities
    assert expand_city_name("Unknown City") == "Unknown City"
    
    logger.info("✅ City name expansion test passed")
    return True


def test_expand_state_code():
    """Test state code expansion."""
    logger.info("Testing state code expansion...")
    
    # Test state codes
    assert expand_state_code("CA") == "California"
    assert expand_state_code("ca") == "California"
    assert expand_state_code("UT") == "Utah"
    assert expand_state_code("ut") == "Utah"
    assert expand_state_code("NY") == "New York"
    assert expand_state_code("TX") == "Texas"
    
    # Test full names (should remain unchanged)
    assert expand_state_code("California") == "California"
    assert expand_state_code("Utah") == "Utah"
    
    # Test unknown codes
    assert expand_state_code("ZZ") == "ZZ"
    assert expand_state_code("Unknown") == "Unknown"
    
    logger.info("✅ State code expansion test passed")
    return True


def test_normalize_address():
    """Test address normalization."""
    logger.info("Testing address normalization...")
    
    # Test with abbreviations
    address = {
        "city": "SF",
        "state": "CA",
        "zip_code": 94102
    }
    normalized = normalize_address(address)
    assert normalized["city"] == "San Francisco"
    assert normalized["state"] == "California"
    assert normalized["zip_code"] == "94102"  # Should be string
    
    # Test with full names
    address2 = {
        "city": "Park City",
        "state": "Utah",
        "zip": "84060"
    }
    normalized2 = normalize_address(address2)
    assert normalized2["city"] == "Park City"
    assert normalized2["state"] == "Utah"
    assert normalized2["zip_code"] == "84060"  # zip renamed to zip_code
    assert "zip" not in normalized2  # old key removed
    
    # Test empty address
    assert normalize_address({}) == {}
    assert normalize_address(None) == None
    
    logger.info("✅ Address normalization test passed")
    return True


def test_validate_coordinates():
    """Test coordinate validation."""
    logger.info("Testing coordinate validation...")
    
    # Valid coordinates
    assert validate_coordinates(37.7749, -122.4194) == True
    assert validate_coordinates(0, 0) == True
    assert validate_coordinates(-90, 180) == True
    assert validate_coordinates(90, -180) == True
    
    # Invalid latitude
    assert validate_coordinates(91, 0) == False
    assert validate_coordinates(-91, 0) == False
    
    # Invalid longitude
    assert validate_coordinates(0, 181) == False
    assert validate_coordinates(0, -181) == False
    
    # None values
    assert validate_coordinates(None, 0) == False
    assert validate_coordinates(0, None) == False
    assert validate_coordinates(None, None) == False
    
    # String values that can be converted
    assert validate_coordinates("37.7749", "-122.4194") == True
    
    # Invalid strings
    assert validate_coordinates("invalid", "0") == False
    
    logger.info("✅ Coordinate validation test passed")
    return True


def test_normalize_feature_list():
    """Test feature list normalization."""
    logger.info("Testing feature list normalization...")
    
    # Test deduplication and normalization
    features = ["Pool", "pool", "POOL", "Garage", "garage", "Garden"]
    normalized = normalize_feature_list(features)
    
    # Should be lowercase, deduplicated, sorted
    assert "pool" in normalized
    assert "garage" in normalized
    assert "garden" in normalized
    assert normalized.count("pool") == 1  # No duplicates
    assert normalized.count("garage") == 1
    
    # Check sorting
    assert normalized == sorted(normalized)
    
    # Test with empty and None
    assert normalize_feature_list([]) == []
    assert normalize_feature_list(None) == []
    
    # Test with whitespace
    features2 = ["  pool  ", "garage ", " garden"]
    normalized2 = normalize_feature_list(features2)
    assert normalized2 == ["garage", "garden", "pool"]
    
    # Test with empty strings
    features3 = ["pool", "", "garage", "  ", None]
    normalized3 = normalize_feature_list(features3)
    assert "" not in normalized3
    assert None not in normalized3
    
    logger.info("✅ Feature list normalization test passed")
    return True


def test_extract_features_from_description():
    """Test feature extraction from description."""
    logger.info("Testing feature extraction from description...")
    
    # Test with various features
    description = """
    Beautiful home with a sparkling pool and attached garage.
    Features include hardwood floors, granite countertops,
    and stainless steel appliances. The property has a lovely garden
    and patio area, perfect for entertaining. Recently renovated
    with a new roof and solar panels. Mountain view from the deck.
    """
    
    features = extract_features_from_description(description)
    
    # Check expected features were found
    assert "pool" in features
    assert "garage" in features
    assert "garden" in features
    assert "patio" in features
    assert "hardwood" in features
    assert "granite" in features
    assert "stainless steel" in features
    assert "renovated" in features
    assert "new roof" in features
    assert "solar panels" in features
    assert "mountain view" in features
    assert "deck" in features
    
    # Test with empty description
    assert extract_features_from_description("") == []
    assert extract_features_from_description(None) == []
    
    # Test case insensitivity
    description2 = "This home has a POOL, Garage, and FIREPLACE."
    features2 = extract_features_from_description(description2)
    assert "pool" in features2
    assert "garage" in features2
    assert "fireplace" in features2
    
    logger.info("✅ Feature extraction test passed")
    return True


def test_merge_feature_lists():
    """Test merging multiple feature lists."""
    logger.info("Testing feature list merging...")
    
    list1 = ["pool", "garage", "garden"]
    list2 = ["Pool", "Spa", "Gym"]
    list3 = ["garden", "patio", "deck"]
    
    merged = merge_feature_lists(list1, list2, list3)
    
    # Should contain all unique features, normalized
    expected = ["deck", "garage", "garden", "gym", "patio", "pool", "spa"]
    assert merged == expected
    
    # Test with empty lists
    merged2 = merge_feature_lists([], ["pool"], None, ["garage"])
    assert "pool" in merged2
    assert "garage" in merged2
    
    # Test with all empty
    assert merge_feature_lists([], None, []) == []
    
    logger.info("✅ Feature list merging test passed")
    return True


def run_all_tests():
    """Run all enricher tests."""
    logger.info("=" * 60)
    logger.info("Running Enricher Tests")
    logger.info("=" * 60)
    
    tests = [
        test_expand_city_name,
        test_expand_state_code,
        test_normalize_address,
        test_validate_coordinates,
        test_normalize_feature_list,
        test_extract_features_from_description,
        test_merge_feature_lists
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test {test.__name__} failed: {e}")
            failed += 1
    
    logger.info("=" * 60)
    logger.info(f"Test Results: {passed} passed, {failed} failed")
    logger.info("=" * 60)
    
    if failed == 0:
        logger.info("🎉 All enricher tests passed!")
    else:
        logger.error(f"⚠️ {failed} tests failed")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)