#!/usr/bin/env python3
"""
Test script to verify Phase 1 setup is working correctly.
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from shared.llm_utils import test_llm_connection, setup_llm
from summarize.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_config():
    """Test configuration loading."""
    logger.info("Testing configuration...")
    
    try:
        # Test default config
        config = Config()
        logger.info(f"Default config loaded: {config.model_dump()}")
        
        # Test from environment
        config_env = Config.from_env()
        logger.info(f"Environment config loaded: {config_env.model_dump()}")
        
        return True
    except Exception as e:
        logger.error(f"Config test failed: {e}")
        return False


def test_dspy_hello_world():
    """Test DSPy with a simple prompt."""
    logger.info("Testing DSPy connection...")
    
    try:
        import dspy
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv('.env')
        
        # Test connection
        if test_llm_connection():
            logger.info("✓ DSPy connection successful!")
            
            # Try a Wikipedia-specific test
            llm = setup_llm()
            test_prompt = "Summarize in one sentence: San Francisco is a city in California."
            response = llm(test_prompt)
            logger.info(f"Wikipedia test response: {response}")
            
            return True
        else:
            logger.error("✗ DSPy connection failed")
            return False
            
    except ImportError as e:
        logger.error(f"Import error - ensure requirements are installed: {e}")
        return False
    except Exception as e:
        logger.error(f"DSPy test failed: {e}")
        return False


def main():
    """Run all Phase 1 tests."""
    logger.info("=" * 60)
    logger.info("Phase 1: Foundation Setup - Verification")
    logger.info("=" * 60)
    
    results = []
    
    # Test configuration
    results.append(("Configuration", test_config()))
    
    # Test DSPy
    results.append(("DSPy Connection", test_dspy_hello_world()))
    
    # Summary
    logger.info("=" * 60)
    logger.info("Test Results:")
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"  {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    if all_passed:
        logger.info("✓ Phase 1 setup complete and verified!")
    else:
        logger.info("✗ Phase 1 setup has issues - please check the errors above")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
