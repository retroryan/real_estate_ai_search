#!/usr/bin/env python
"""
Test script to verify environment variable loading from parent .env file.
"""

import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def test_env_loading():
    """Test that environment variables are loaded from parent .env."""
    
    print("=" * 60)
    print("Testing Environment Variable Loading")
    print("=" * 60)
    
    # Import after adding to path to trigger load_dotenv
    from data_pipeline.config.settings import ConfigurationManager
    
    # Check if parent .env exists
    parent_env = Path(__file__).parent.parent / ".env"
    print(f"\nParent .env location: {parent_env}")
    print(f"Parent .env exists: {parent_env.exists()}")
    
    # Check if local .env exists
    local_env = Path(__file__).parent / ".env"
    print(f"\nLocal .env location: {local_env}")
    print(f"Local .env exists: {local_env.exists()}")
    
    # Test loading configuration
    print("\nLoading configuration...")
    config_manager = ConfigurationManager()
    config = config_manager.load_config()
    
    # Check Neo4j configuration
    print("\n--- Neo4j Configuration ---")
    if hasattr(config, 'output_destinations') and config.output_destinations.neo4j:
        neo4j_config = config.output_destinations.neo4j
        print(f"URI: {neo4j_config.uri}")
        print(f"Username: {neo4j_config.username}")
        print(f"Database: {neo4j_config.database}")
        print(f"Password configured: {'Yes' if neo4j_config.password else 'No'}")
        
        # Check environment variable
        neo4j_pass_from_env = os.getenv("NEO4J_PASSWORD")
        print(f"NEO4J_PASSWORD in environment: {'Yes' if neo4j_pass_from_env else 'No'}")
        
        if neo4j_config.password and neo4j_config.password.startswith("${"):
            resolved_password = neo4j_config.get_password()
            print(f"Password resolved from environment: {'Yes' if resolved_password else 'No'}")
    
    # Check other important environment variables
    print("\n--- Other Environment Variables ---")
    important_vars = [
        "OPENAI_API_KEY",
        "VOYAGE_API_KEY", 
        "GEMINI_API_KEY",
        "ES_PASSWORD",
        "LLM_MODEL"
    ]
    
    for var in important_vars:
        value = os.getenv(var)
        if value:
            # Mask the value for security
            masked = value[:4] + "..." if len(value) > 4 else "***"
            print(f"{var}: {masked}")
        else:
            print(f"{var}: Not set")
    
    print("\n✅ Environment variable loading test complete!")
    print("\nTo set up credentials:")
    print(f"1. Copy {parent_env.parent}/.env.example to {parent_env}")
    print("2. Fill in your actual credentials")
    print("3. Run this test again to verify")


if __name__ == "__main__":
    test_env_loading()