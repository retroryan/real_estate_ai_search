#!/usr/bin/env python3
"""
Simple script to test Elasticsearch connection.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from elasticsearch import Elasticsearch

# Test different connection methods
print("Testing Elasticsearch connection methods...\n")

# Method 1: No auth
print("1. Testing without authentication:")
try:
    es = Elasticsearch(["http://localhost:9200"])
    if es.ping():
        print("   ✅ Connected without auth")
        info = es.info()
        print(f"   Version: {info['version']['number']}")
    else:
        print("   ❌ Cannot connect without auth")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n2. Testing with authentication:")
try:
    es = Elasticsearch(
        ["http://localhost:9200"],
        basic_auth=("elastic", "2GJXncaV")
    )
    if es.ping():
        print("   ✅ Connected with auth")
        info = es.info()
        print(f"   Version: {info['version']['number']}")
    else:
        print("   ❌ Cannot connect with auth")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n3. Testing Docker hostname:")
try:
    es = Elasticsearch(
        ["http://elasticsearch:9200"],
        basic_auth=("elastic", "2GJXncaV")
    )
    if es.ping():
        print("   ✅ Connected to Docker container")
    else:
        print("   ❌ Cannot connect to Docker container")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\nRecommendation:")
print("Update your .env file with the working connection settings above.")