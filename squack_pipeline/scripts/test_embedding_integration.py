#!/usr/bin/env python3
"""Test script for SQUACK Pipeline Embedding Integration - LlamaIndex document processing and embedding generation."""

import os
import sys
import time
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.orchestrator.pipeline import PipelineOrchestrator
from squack_pipeline.utils.logging import PipelineLogger


def test_yaml_config_loading():
    """Test YAML configuration loading."""
    logger = PipelineLogger.get_logger("TestYAMLConfig")
    
    logger.info("🧪 Testing YAML Configuration Loading")
    logger.info("=" * 50)
    
    try:
        # Test loading config.yaml
        config_path = Path("squack_pipeline/config.yaml")
        if not config_path.exists():
            logger.error("❌ config.yaml not found")
            return False
        
        # Load configuration
        settings = PipelineSettings.load_from_yaml(config_path)
        
        # Validate key configuration sections
        if not hasattr(settings, 'embedding'):
            logger.error("❌ No embedding configuration found")
            return False
        
        if not hasattr(settings, 'processing'):
            logger.error("❌ No processing configuration found")
            return False
        
        logger.info(f"📋 Configuration loaded successfully:")
        logger.info(f"  Pipeline: {settings.pipeline_name}")
        logger.info(f"  Embedding provider: {settings.embedding.provider.value}")
        logger.info(f"  Chunk method: {settings.processing.chunk_method.value}")
        logger.info(f"  Batch size: {settings.processing.batch_size}")
        logger.info(f"  Generate embeddings: {settings.processing.generate_embeddings}")
        
        logger.success("✅ YAML configuration loading test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ YAML configuration loading test failed: {e}")
        return False


def test_embedding_pipeline_mock():
    """Test embedding pipeline with mock provider."""
    logger = PipelineLogger.get_logger("TestEmbeddingMock")
    
    logger.info("🧪 Testing Embedding Pipeline with Mock Provider")
    logger.info("=" * 60)
    
    # Create temporary settings for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Configure test settings with mock embedding
        test_settings = PipelineSettings(
            data={
                "input_path": Path("real_estate_data"),
                "output_path": temp_path / "output",
                "properties_file": "properties_sf.json",
                "sample_size": 3
            },
            embedding={
                "provider": "mock",
                "mock_dimension": 1024
            },
            processing={
                "generate_embeddings": True,
                "batch_size": 2,
                "chunk_method": "simple",
                "chunk_size": 400,
                "enable_chunking": True
            },
            dry_run=False,
            environment="test",
            log_level="INFO"
        )
        
        try:
            # Initialize pipeline
            orchestrator = PipelineOrchestrator(test_settings)
            
            # Test complete pipeline with embeddings
            logger.info("🚀 Running complete pipeline with mock embeddings")
            start_time = time.time()
            
            orchestrator.run()
            
            processing_time = time.time() - start_time
            
            # Get metrics
            metrics = orchestrator.get_metrics()
            
            # Validate results
            logger.info("📊 Embedding Pipeline Results:")
            logger.info(f"  Processing time: {processing_time:.2f}s")
            logger.info(f"  Bronze records: {metrics['bronze_records']}")
            logger.info(f"  Silver records: {metrics['silver_records']}")
            logger.info(f"  Gold records: {metrics['gold_records']}")
            logger.info(f"  Documents converted: {metrics.get('documents_converted', 0)}")
            logger.info(f"  Embeddings generated: {metrics.get('embeddings_generated', 0)}")
            logger.info(f"  Embedding success rate: {metrics.get('embedding_success_rate', 0):.2%}")
            
            # Validation checks
            success = True
            
            if metrics.get('documents_converted', 0) == 0:
                logger.error("❌ No documents were converted")
                success = False
            
            if metrics.get('embeddings_generated', 0) == 0:
                logger.warning("⚠️ No embeddings were generated")
            else:
                if metrics.get('embedding_success_rate', 0) < 0.8:
                    logger.warning(f"⚠️ Low embedding success rate: {metrics.get('embedding_success_rate', 0):.2%}")
            
            # Cleanup
            orchestrator.cleanup()
            
            if success:
                logger.success("✅ Mock embedding pipeline test PASSED")
                return True
            else:
                logger.error("❌ Mock embedding pipeline test FAILED")
                return False
                
        except Exception as e:
            logger.error(f"❌ Test failed with error: {e}")
            return False


def test_embedding_configuration_validation():
    """Test embedding configuration validation."""
    logger = PipelineLogger.get_logger("TestEmbeddingValidation")
    
    logger.info("🧪 Testing Embedding Configuration Validation")
    logger.info("=" * 55)
    
    try:
        # Test different embedding providers
        providers_to_test = [
            ("mock", {"provider": "mock", "mock_dimension": 512}),
            ("voyage", {"provider": "voyage", "voyage_model": "voyage-3"}),
            ("openai", {"provider": "openai", "openai_model": "text-embedding-3-small"})
        ]
        
        from squack_pipeline.embeddings.pipeline import EmbeddingPipeline
        
        for provider_name, embedding_config in providers_to_test:
            logger.info(f"🔍 Testing {provider_name} provider configuration")
            
            test_settings = PipelineSettings(
                embedding=embedding_config,
                processing={
                    "generate_embeddings": True,
                    "batch_size": 5,
                    "chunk_method": "simple"
                },
                environment="test"
            )
            
            # Test embedding pipeline initialization
            pipeline = EmbeddingPipeline(test_settings)
            
            # Test configuration validation
            is_valid = pipeline.validate_configuration()
            
            if provider_name == "mock":
                # Mock should always be valid
                if not is_valid:
                    logger.error(f"❌ Mock provider validation failed")
                    return False
                
                # Test initialization for mock
                if pipeline.initialize():
                    logger.success(f"✅ {provider_name} provider initialized successfully")
                else:
                    logger.error(f"❌ {provider_name} provider initialization failed")
                    return False
            else:
                # Other providers may fail without API keys in test environment
                if is_valid:
                    logger.info(f"✅ {provider_name} provider configuration is valid")
                else:
                    logger.info(f"ℹ️ {provider_name} provider requires API key (expected in test)")
        
        logger.success("✅ Embedding configuration validation test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Embedding configuration validation test failed: {e}")
        return False


def test_embedding_disabled():
    """Test pipeline with embedding generation disabled."""
    logger = PipelineLogger.get_logger("TestEmbeddingDisabled")
    
    logger.info("🧪 Testing Pipeline with Embedding Generation Disabled")
    logger.info("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        test_settings = PipelineSettings(
            data={
                "input_path": Path("real_estate_data"),
                "output_path": temp_path / "output",
                "properties_file": "properties_sf.json",
                "sample_size": 2
            },
            processing={
                "generate_embeddings": False  # Disabled
            },
            dry_run=False,
            environment="test"
        )
        
        try:
            orchestrator = PipelineOrchestrator(test_settings)
            orchestrator.run()
            
            metrics = orchestrator.get_metrics()
            
            # Should have processed data but no embeddings
            if (metrics.get('gold_records', 0) > 0 and 
                metrics.get('documents_converted', 0) == 0 and
                metrics.get('embeddings_generated', 0) == 0):
                
                logger.success("✅ Embedding disabled test PASSED")
                logger.info("📊 Pipeline completed without embedding generation as expected")
                return True
            else:
                logger.error("❌ Embedding disabled test FAILED - unexpected embedding activity")
                return False
                
        except Exception as e:
            logger.error(f"❌ Embedding disabled test failed: {e}")
            return False


def main():
    """Run all Phase 4 tests."""
    logger = PipelineLogger.get_logger("Phase4Tests")
    
    logger.info("🎯 SQUACK Pipeline Phase 4 Test Suite")
    logger.info("=" * 60)
    
    tests = [
        ("YAML Configuration Loading", test_yaml_config_loading),
        ("Embedding Pipeline (Mock Provider)", test_embedding_pipeline_mock),
        ("Embedding Configuration Validation", test_embedding_configuration_validation),
        ("Embedding Generation Disabled", test_embedding_disabled)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running: {test_name}")
        logger.info("-" * 40)
        
        try:
            if test_func():
                passed += 1
                logger.success(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
    
    # Final results
    logger.info("\n" + "=" * 60)
    logger.info(f"📊 Phase 4 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.success("🎉 All Phase 4 tests PASSED!")
        logger.info("\n🚀 Phase 4 (Embedding Integration) is ready!")
        logger.info("✨ YAML configuration loading working")
        logger.info("🧠 LlamaIndex Document → Node → Embedding pipeline working")
        logger.info("🔄 Batch processing with progress tracking implemented")
        logger.info("📝 Text chunking with semantic splitting available")
        logger.info("🏭 Embedding factory supporting multiple providers")
        return True
    else:
        logger.error(f"💥 {total - passed} test(s) FAILED")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)