#!/usr/bin/env python3
"""Test script for SQUACK Pipeline CLI Interface - Command-line interface and argument parsing."""

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
            if result.stdout.strip():
                # Show first line of output
                first_line = result.stdout.split('\n')[0]
                print(f"  → {first_line}")
        else:
            print(f"❌ {description}: FAILED")
            print(f"  Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ {description}: ERROR - {e}")
        return False
    
    return True


def main():
    """Test CLI interface."""
    print("🚀 SQUACK Pipeline - CLI Tests\n")
    
    tests = [
        ([sys.executable, "-m", "squack_pipeline", "version"], "Version command"),
        ([sys.executable, "-m", "squack_pipeline", "--help"], "Help command"),
        ([sys.executable, "-m", "squack_pipeline", "show-config"], "Show config"),
    ]
    
    passed = 0
    total = len(tests)
    
    for cmd, desc in tests:
        if run_command(cmd, desc):
            passed += 1
        print()
    
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All CLI tests passed!")
    else:
        print("❌ Some CLI tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()