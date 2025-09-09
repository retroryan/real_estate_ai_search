# Real Estate AI Search Constitution

## Core Principles

### I. Requirements First
FOLLOW THE REQUIREMENTS EXACTLY - Do not add new features or functionality beyond the specific requirements requested and documented
Requirements drive implementation, not the other way around
No speculative features, no "nice-to-haves", no scope creep

### II. Fix Core Issues
ALWAYS FIX THE CORE ISSUE - Do not work around problems with hacks or mocks
If data is missing, find out why - do not generate sample data
If something doesn't work, fix the root cause - do not patch symptoms
If there are questions, ASK - do not assume

### III. Complete Atomic Changes
COMPLETE CHANGE - All occurrences must be changed in a single, atomic update
NO PARTIAL UPDATES - Change everything or change nothing
NO MIGRATION PHASES - Do not create temporary compatibility periods
NO ROLLBACK PLANS - Never create rollback plans
Changes are immediate and complete

### IV. Clean Implementation
CLEAN IMPLEMENTATION - Simple, direct replacements only
NO COMPATIBILITY LAYERS or Backwards Compatibility - Do not maintain old and new paths simultaneously
NO BACKUPS OF OLD CODE - Do not comment out old code "just in case"
NO CODE DUPLICATION - Do not duplicate functions to handle both patterns
NO WRAPPER FUNCTIONS - Direct replacements only, no abstraction layers
DO NOT CALL FUNCTIONS ENHANCED or IMPROVED - Update the actual methods directly

### V. Technical Standards
ALWAYS USE PYDANTIC - For all data models and validation
USE MODULES AND CLEAN CODE - Proper separation of concerns
Never use hasattr or isinstance for type checking
Never cast variables or create variable aliases
Never use Union types - evaluate the core issue instead
Never name things after phases or steps from process documents

## Code Quality Requirements

### Type Safety
All data models must use Pydantic
No dynamic attribute checking (hasattr)
No runtime type checking (isinstance)
No Union types - redesign if needed
No type casting or variable aliasing

### Naming Conventions
Direct, descriptive names only
No "Enhanced", "Improved", "V2" suffixes on classes
No phase/step references in names (e.g., no "test_phase_2_bronze_layer.py")
Update existing classes directly, do not create parallel versions

### Testing Philosophy
Test actual functionality, not mocks
If tests fail due to missing data, fix the data source
Do not mock or stub unless absolutely necessary for external dependencies
Integration tests for all cross-module interactions

## Change Management

### Implementation Strategy
Make changes directly to existing code
No parallel implementations
No gradual migrations
No backwards compatibility maintenance
Complete replacement in single commits

### Problem Resolution
When encountering issues:
1. Identify the root cause
2. Fix the core problem
3. If unclear, ask for clarification
4. Never hack around problems

### Documentation
Document actual behavior, not intended behavior
Keep documentation in sync with code
No speculative documentation
Follow existing format and schema exactly

## Governance

Constitution supersedes all other practices
All changes must comply with these principles
Complexity must be justified by requirements
Use CLAUDE.md for runtime development guidance

**Version**: 2.0.0 | **Ratified**: 2025-01-07 | **Last Amended**: 2025-01-07