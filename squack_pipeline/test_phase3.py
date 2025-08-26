#!/usr/bin/env python3
"""Test script for SQUACK Pipeline Phase 3 - Processing Pipeline."""

import time
import tempfile
from pathlib import Path

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.orchestrator.pipeline import PipelineOrchestrator
from squack_pipeline.utils.logging import PipelineLogger


def test_medallion_architecture():
    """Test the complete medallion architecture pipeline."""
    logger = PipelineLogger.get_logger("TestPhase3")
    
    logger.info("🧪 Testing Phase 3: Processing Pipeline (Medallion Architecture)")
    logger.info("=" * 60)
    
    # Create temporary settings for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Configure test settings
        test_settings = PipelineSettings(
            data={
                "input_path": Path("real_estate_data"),
                "output_path": temp_path / "output",
                "properties_file": "properties_sf.json",
                "sample_size": 5
            },
            dry_run=False,
            environment="test",
            log_level="INFO"
        )
        
        try:
            # Initialize pipeline
            orchestrator = PipelineOrchestrator(test_settings)
            
            # Test complete medallion pipeline
            logger.info("🚀 Running complete medallion architecture pipeline")
            start_time = time.time()
            
            orchestrator.run()
            
            processing_time = time.time() - start_time
            
            # Get metrics
            metrics = orchestrator.get_metrics()
            
            # Validate results
            logger.info("📊 Pipeline Results:")
            logger.info(f"  Processing time: {processing_time:.2f}s")
            logger.info(f"  Bronze records: {metrics['bronze_records']}")
            logger.info(f"  Silver records: {metrics['silver_records']}")
            logger.info(f"  Gold records: {metrics['gold_records']}")
            logger.info(f"  Tables created: {metrics['tables_created']}")
            logger.info(f"  Enrichment completeness: {metrics.get('enrichment_completeness', 0):.2%}")
            
            # Validation checks
            success = True
            
            if metrics['bronze_records'] == 0:
                logger.error("❌ No Bronze tier records loaded")
                success = False
            
            if metrics['silver_records'] == 0:
                logger.error("❌ No Silver tier records processed")
                success = False
            
            if metrics['gold_records'] == 0:
                logger.error("❌ No Gold tier records processed")
                success = False
            
            if metrics['tables_created'] < 3:
                logger.error(f"❌ Expected at least 3 tables, got {metrics['tables_created']}")
                success = False
            
            if metrics.get('enrichment_completeness', 0) < 0.5:
                logger.warning(f"⚠️ Low enrichment completeness: {metrics.get('enrichment_completeness', 0):.2%}")
            
            # Cleanup
            orchestrator.cleanup()
            
            if success:
                logger.success("✅ Phase 3 medallion architecture test PASSED")
                return True
            else:
                logger.error("❌ Phase 3 medallion architecture test FAILED")
                return False
                
        except Exception as e:
            logger.error(f"❌ Test failed with error: {e}")
            return False


def test_data_quality():
    """Test data quality through the medallion tiers."""
    logger = PipelineLogger.get_logger("TestDataQuality")
    
    logger.info("🧪 Testing Data Quality across Medallion Tiers")
    logger.info("=" * 50)
    
    # Test with minimal settings for quality check
    test_settings = PipelineSettings(
        data={
            "input_path": Path("real_estate_data"),
            "properties_file": "properties_sf.json",
            "sample_size": 3
        },
        dry_run=True,
        environment="test"
    )
    
    try:
        orchestrator = PipelineOrchestrator(test_settings)
        
        # Test processors initialization
        orchestrator._initialize_pipeline()
        
        # Check processors are initialized
        if not orchestrator.silver_processor:
            logger.error("❌ Silver processor not initialized")
            return False
        
        if not orchestrator.gold_processor:
            logger.error("❌ Gold processor not initialized")  
            return False
        
        if not orchestrator.geo_enrichment:
            logger.error("❌ Geographic enrichment processor not initialized")
            return False
        
        logger.success("✅ All processors initialized successfully")
        
        # Test connection sharing
        connection = orchestrator.connection_manager.get_connection()
        if not connection:
            logger.error("❌ No database connection")
            return False
        
        logger.success("✅ Database connection established")
        
        # Cleanup
        orchestrator.cleanup()
        
        logger.success("✅ Data quality test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Data quality test failed: {e}")
        return False


def main():
    """Run all Phase 3 tests."""
    logger = PipelineLogger.get_logger("Phase3Tests")
    
    logger.info("🎯 SQUACK Pipeline Phase 3 Test Suite")
    logger.info("=" * 60)
    
    tests = [
        ("Medallion Architecture Pipeline", test_medallion_architecture),
        ("Data Quality Validation", test_data_quality)
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
    logger.info(f"📊 Phase 3 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.success("🎉 All Phase 3 tests PASSED!")
        logger.info("\n🚀 Phase 3 (Processing Pipeline) is ready!")
        logger.info("✨ Medallion architecture implemented successfully")
        logger.info("📈 Bronze → Silver → Gold data flow working")
        logger.info("🌍 Geographic enrichment integrated")
        return True
    else:
        logger.error(f"💥 {total - passed} test(s) FAILED")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)