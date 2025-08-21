"""
LLM utilities for Wikipedia summarization using modern DSPy patterns.
Simplified configuration following current DSPy best practices.
"""

import logging
import os
from typing import Optional

import dspy
from wiki_summary.exceptions import ConfigurationException, LLMException

logger = logging.getLogger(__name__)


def setup_llm(model: Optional[str] = None, **kwargs) -> dspy.LM:
    """
    Modern DSPy LLM setup following current best practices.
    
    Args:
        model: Model identifier (e.g., 'openai/gpt-4o-mini')
        **kwargs: Additional configuration (temperature, max_tokens, cache, etc.)
    
    Returns:
        Configured DSPy LM instance
    """
    # Default model from environment or fallback
    model = model or os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
    
    # Default configuration with sensible defaults for summarization
    default_config = {
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.3")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "2000")),
        "cache": True,  # Enable caching by default for cost efficiency
    }
    
    # Merge with provided kwargs (kwargs override defaults)
    llm_config = {**default_config, **kwargs}
    
    logger.info(f"Initializing LLM: {model} with config: {llm_config}")
    
    try:
        # Modern DSPy pattern: create LM instance and configure settings
        llm = dspy.LM(model=model, **llm_config)
        
        # Best practice: Use JSONAdapter for better performance and automatic fallback
        # This will use structured outputs when possible, JSON mode as fallback
        try:
            from dspy.adapters import JSONAdapter
            adapter = JSONAdapter()
            dspy.configure(lm=llm, adapter=adapter)
            logger.info(f"Successfully configured DSPy with model: {model} using JSONAdapter")
        except ImportError:
            # Fallback if JSONAdapter not available (older DSPy versions)
            dspy.settings.configure(lm=llm)
            logger.info(f"Successfully configured DSPy with model: {model} using default adapter")
        
        return llm
        
    except Exception as e:
        logger.error(f"Error initializing DSPy for model {model}: {type(e).__name__}: {e}")
        raise ConfigurationException(f"DSPy initialization error: {e}") from e


def test_llm_connection() -> bool:
    """
    Test the LLM connection with a simple prompt.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        logger.info("Starting DSPy LLM connection test...")
        llm = setup_llm()
        
        # Simple test using the configured LLM
        test_signature = dspy.Signature(
            "prompt -> response",
            prompt=dspy.InputField(desc="Test prompt"),
            response=dspy.OutputField(desc="Test response")
        )
        
        logger.debug("Creating DSPy predictor for connection test")
        predictor = dspy.Predict(test_signature)
        
        logger.debug("Executing test prompt")
        result = predictor(prompt="Say 'Wikipedia summarization system ready!'")
        
        logger.info(f"DSPy LLM test successful: {result.response}")
        return True
        
    except dspy.DSPyException as e:
        logger.error(f"DSPy LLM test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in LLM test: {type(e).__name__}: {e}")
        return False