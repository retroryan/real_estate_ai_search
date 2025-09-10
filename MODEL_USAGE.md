# Model Usage Reference

## Overview
This document tracks the usage of all Pydantic model classes defined in `real_estate_search/demo_queries/models.py` to facilitate refactoring and cleanup.

## Update: Unused Models Removed
The following unused model classes have been removed from `models.py`:
- PropertySearchParams
- PropertyFilterParams  
- GeoSearchParams
- AggregationParams
- SemanticSearchParams
- MultiEntitySearchParams

## Remaining Model Classes

| Model Class | Purpose | Where Used | Description |
|-------------|---------|------------|-------------|
| **DemoQueryResult** | Standard demo query result format | Used extensively throughout demo system | Primary result class for all demo queries with display formatting and query metadata |
| **LocationUnderstandingResult** | Specialized location understanding result | Used in location understanding demo only | Extends DemoQueryResult with specialized display for location extraction results |

## Detailed Analysis: LocationUnderstandingResult

### Current Implementation

**LocationUnderstandingResult** is a minimal subclass that only overrides the `display()` method:

```python
class LocationUnderstandingResult(DemoQueryResult):
    """Specialized result class for location understanding demos."""
    
    def display(self, verbose: bool = False) -> str:
        """Use the specialized location understanding display."""
        return self.display_location_understanding(verbose=verbose)
```

### Usage Analysis

#### Where It's Used:
1. **location_understanding.py** (line 85) - Returns LocationUnderstandingResult instead of DemoQueryResult
2. **test_location_understanding.py** (line 135) - Tests that the return type is LocationUnderstandingResult

#### What It Does:
- Inherits all fields and methods from DemoQueryResult
- Only difference: calls `display_location_understanding()` instead of the default `display()` method
- The `display_location_understanding()` method is already defined in the parent DemoQueryResult class

### Value Assessment

**Does LocationUnderstandingResult add value?**

**NO - It could be removed.** Here's why:

1. **Redundant Abstraction**: 
   - The specialized display method `display_location_understanding()` already exists in the parent DemoQueryResult class
   - The subclass only serves as a switch to use a different display method

2. **Alternative Approach**:
   - Could add a `display_type` field to DemoQueryResult (e.g., "standard" or "location")
   - The display() method could check this field and call the appropriate display method
   - This would eliminate the need for a separate class

3. **Single Usage**:
   - Only used in one demo function (demo_location_understanding)
   - The test only checks instance type, not actual functionality

4. **Maintenance Overhead**:
   - Extra class to maintain for minimal benefit
   - Violates YAGNI (You Aren't Gonna Need It) principle

### Recommended Refactoring

**Option 1: Remove LocationUnderstandingResult** (Recommended)
- Add a `display_format` field to DemoQueryResult with default "standard"
- Modify display() method to check format and call appropriate display method
- Change demo_location_understanding to return DemoQueryResult with display_format="location"

**Option 2: Keep but Justify**
- Only keep if planning to add location-specific fields or methods
- Currently provides no additional functionality beyond display switching

### Code Changes Required if Removed:

1. **models.py**:
   - Remove LocationUnderstandingResult class
   - Add display_format field to DemoQueryResult
   - Update display() method to check display_format

2. **location_understanding.py**:
   - Return DemoQueryResult instead of LocationUnderstandingResult
   - Set display_format="location" in the result

3. **test_location_understanding.py**:
   - Update test to check for DemoQueryResult type
   - Optionally test that display_format is set correctly

## Final Recommendations

1. **Remove LocationUnderstandingResult** - It adds no real value and creates unnecessary class hierarchy
2. **Refactor DemoQueryResult.display()** - Break into smaller methods for better maintainability
3. **Consider a display service** - Move all display logic to a separate service class to follow Single Responsibility Principle