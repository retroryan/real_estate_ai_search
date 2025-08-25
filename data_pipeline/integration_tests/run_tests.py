#!/usr/bin/env python3
"""
Test runner for data pipeline integration tests.

This script provides convenient ways to run different types of integration tests
for the data pipeline, including Parquet validation, schema compliance, and
data quality checks.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_smoke_tests():
    """Run quick smoke tests to verify basic functionality."""
    print("🔥 Running smoke tests...")
    
    # Run the quick parquet smoke test
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "data_pipeline/integration_tests/test_parquet_validation.py::test_quick_parquet_smoke",
        "-v", "--tb=short"
    ])
    
    if result.returncode == 0:
        print("✅ Smoke tests passed!")
    else:
        print("❌ Smoke tests failed!")
        return False
    
    return True


def run_parquet_tests():
    """Run comprehensive Parquet validation tests."""
    print("📊 Running Parquet validation tests...")
    
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "data_pipeline/integration_tests/test_parquet_validation.py",
        "-v", "--tb=short", "-m", "not slow"
    ])
    
    if result.returncode == 0:
        print("✅ Parquet tests passed!")
    else:
        print("❌ Parquet tests failed!")
        return False
    
    return True


def run_full_tests():
    """Run comprehensive integration tests."""
    print("🚀 Running full integration test suite...")
    
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "data_pipeline/integration_tests/",
        "-v", "--tb=short"
    ])
    
    if result.returncode == 0:
        print("✅ All integration tests passed!")
    else:
        print("❌ Some integration tests failed!")
        return False
    
    return True


def run_with_coverage():
    """Run tests with coverage reporting."""
    print("📈 Running tests with coverage...")
    
    try:
        import coverage
    except ImportError:
        print("❌ Coverage not installed. Install with: pip install coverage")
        return False
    
    result = subprocess.run([
        "coverage", "run", "-m", "pytest",
        "data_pipeline/integration_tests/",
        "-v", "--tb=short"
    ])
    
    if result.returncode == 0:
        # Generate coverage report
        subprocess.run(["coverage", "report", "--show-missing"])
        subprocess.run(["coverage", "html"])
        print("✅ Tests with coverage completed! See htmlcov/index.html for detailed report.")
    else:
        print("❌ Tests with coverage failed!")
        return False
    
    return True


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Run data pipeline integration tests")
    parser.add_argument(
        "test_type", 
        choices=["smoke", "parquet", "full", "coverage"],
        help="Type of tests to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("🧪 DATA PIPELINE INTEGRATION TESTS")
    print("="*60)
    
    # Change to project root directory
    project_root = Path(__file__).parent.parent.parent
    import os
    os.chdir(project_root)
    
    success = False
    
    if args.test_type == "smoke":
        success = run_smoke_tests()
    elif args.test_type == "parquet":
        success = run_parquet_tests()
    elif args.test_type == "full":
        success = run_full_tests()
    elif args.test_type == "coverage":
        success = run_with_coverage()
    
    print("\n" + "="*60)
    if success:
        print("🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()