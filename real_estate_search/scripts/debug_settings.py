#!/usr/bin/env python3
"""Debug settings loading."""

import os
import sys
from pathlib import Path

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Show current directory
print(f"Current directory: {os.getcwd()}")
print(f"Script directory: {Path(__file__).parent}")

# Check if .env exists
env_path = Path(".env")
print(f"\n.env exists in current dir: {env_path.exists()}")
if env_path.exists():
    print("First 5 lines of .env:")
    with open(env_path) as f:
        for i, line in enumerate(f):
            if i >= 5:
                break
            print(f"  {line.rstrip()}")

# Try loading settings
from real_estate_search.config.settings import Settings

print("\nLoading settings...")
settings = Settings.load()

print(f"\nElasticsearch settings:")
print(f"  Host: {settings.elasticsearch.host}")
print(f"  Port: {settings.elasticsearch.port}")
print(f"  Username: {settings.elasticsearch.username}")
print(f"  Password: {'*' * len(settings.elasticsearch.password) if settings.elasticsearch.password else 'None'}")
print(f"  Has auth: {settings.elasticsearch.has_auth}")

# Check environment variables directly
print(f"\nEnvironment variables:")
print(f"  ES_USERNAME: {os.getenv('ES_USERNAME', 'Not set')}")
print(f"  ES_PASSWORD: {'***' if os.getenv('ES_PASSWORD') else 'Not set'}")