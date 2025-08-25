#!/usr/bin/env python
"""
Simple test runner for property_finder_models.
"""

import sys
import unittest

# Add the current directory to the path
sys.path.insert(0, '.')

# Load and run tests
loader = unittest.TestLoader()
suite = loader.discover('tests', pattern='test_*.py')
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# Exit with appropriate code
sys.exit(0 if result.wasSuccessful() else 1)