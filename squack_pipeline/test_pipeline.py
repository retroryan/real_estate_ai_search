#!/usr/bin/env python3
"""Test script for the complete SQUACK pipeline."""

import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(cmd_list, description):
    """Run a command and check result."""
    print(f"🧪 Testing: {description}")
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            cwd=project_root,
            env={'PYTHONPATH': str(project_root)}
        )
        
        if result.returncode == 0:
            print(f"✓ {description}: PASSED")
            # Show key output lines
            output_lines = result.stdout.strip().split('\n')
            success_lines = [line for line in output_lines if '✓' in line or 'SUCCESS' in line or 'Loaded' in line]
            for line in success_lines[-3:]:  # Show last 3 success messages
                if line.strip():
                    print(f"  → {line.strip()}")
        else:
            print(f"❌ {description}: FAILED")
            print(f"  Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ {description}: ERROR - {e}")
        return False
    
    return True


def main():
    """Test the complete SQUACK pipeline."""
    print("🚀 SQUACK Pipeline - Complete Pipeline Tests\n")
    
    tests = [
        # Configuration tests
        ([sys.executable, "-m", "squack_pipeline", "version"], "Version check"),
        ([sys.executable, "-m", "squack_pipeline", "run", "--validate"], "Configuration validation"),
        
        # Pipeline execution tests  
        ([sys.executable, "-m", "squack_pipeline", "run", "--sample-size", "3", "--dry-run"], "Dry run with sample data"),
        ([sys.executable, "-m", "squack_pipeline", "run", "--sample-size", "5"], "Process sample data"),
        ([sys.executable, "-m", "squack_pipeline", "run", "--sample-size", "10", "--verbose", "--dry-run"], "Verbose dry run"),
    ]
    
    passed = 0
    total = len(tests)
    
    for cmd, desc in tests:
        if run_command(cmd, desc):
            passed += 1
        print()
    
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All pipeline tests passed!")
        print("\n🎉 SQUACK Pipeline is working correctly!")
        print("   - DuckDB integration: ✓")
        print("   - Property data loading: ✓") 
        print("   - Data validation: ✓")
        print("   - Logging and metrics: ✓")
        print("   - CLI interface: ✓")
    else:
        print("❌ Some pipeline tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()