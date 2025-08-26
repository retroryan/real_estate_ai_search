#!/usr/bin/env python3
"""Test script for SQUACK Pipeline Phase 6 - Complete Orchestration."""

import os
import time
import tempfile
from pathlib import Path
import json
import subprocess

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.orchestrator.pipeline import PipelineOrchestrator
from squack_pipeline.orchestrator.state_manager import PipelineStateManager, PipelineState
from squack_pipeline.utils.logging import PipelineLogger


def test_cli_interface():
    """Test CLI interface functionality."""
    logger = PipelineLogger.get_logger("TestCLIInterface")
    
    logger.info("🧪 Testing CLI Interface")
    logger.info("=" * 50)
    
    try:
        # Test help command
        result = subprocess.run(
            ["python", "-m", "squack_pipeline", "--help"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error("❌ CLI help command failed")
            return False
        
        if "SQUACK Pipeline" not in result.stdout:
            logger.error("❌ CLI help output missing expected content")
            return False
        
        logger.info("✅ CLI help command working")
        
        # Test show-config command
        result = subprocess.run(
            ["python", "-m", "squack_pipeline", "show-config"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": "."}
        )
        
        if result.returncode != 0:
            logger.error(f"❌ CLI show-config failed: {result.stderr}")
            return False
        
        # Parse JSON output
        try:
            config = json.loads(result.stdout)
            if "pipeline_name" not in config:
                logger.error("❌ Config output missing expected fields")
                return False
        except json.JSONDecodeError:
            logger.error("❌ Config output is not valid JSON")
            return False
        
        logger.info("✅ CLI show-config command working")
        
        # Test validate-config command
        result = subprocess.run(
            ["python", "-m", "squack_pipeline", "validate-config", "squack_pipeline/config.yaml"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": "."}
        )
        
        if result.returncode != 0:
            logger.warning(f"⚠️ Config validation returned non-zero: {result.stderr}")
        else:
            logger.info("✅ CLI validate-config command working")
        
        # Test version command
        result = subprocess.run(
            ["python", "-m", "squack_pipeline", "version"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": "."}
        )
        
        if "SQUACK Pipeline" not in result.stdout:
            logger.error("❌ Version command output missing")
            return False
        
        logger.info("✅ CLI version command working")
        
        logger.success("✅ CLI interface test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ CLI interface test failed: {e}")
        return False


def test_state_management():
    """Test pipeline state management and recovery."""
    logger = PipelineLogger.get_logger("TestStateManagement")
    
    logger.info("🧪 Testing State Management")
    logger.info("=" * 50)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        settings = PipelineSettings(
            data={"output_path": temp_path},
            dry_run=False
        )
        
        try:
            # Create state manager
            state_manager = PipelineStateManager(settings)
            
            # Test state updates
            state_manager.update_state(PipelineState.LOADING_BRONZE, "Loading data")
            if state_manager.current_state.state != PipelineState.LOADING_BRONZE:
                logger.error("❌ State update failed")
                return False
            
            # Test table recording
            state_manager.record_table("bronze", "test_bronze_table")
            if state_manager.current_state.bronze_table != "test_bronze_table":
                logger.error("❌ Table recording failed")
                return False
            
            # Test metrics update
            state_manager.update_metrics({"test_metric": 100})
            if state_manager.current_state.metrics.get("test_metric") != 100:
                logger.error("❌ Metrics update failed")
                return False
            
            # Test state persistence
            state_file = state_manager.state_file
            if not state_file.exists():
                logger.error("❌ State file not created")
                return False
            
            # Test state loading
            loaded_state = state_manager.load_state(state_file)
            if not loaded_state:
                logger.error("❌ State loading failed")
                return False
            
            if loaded_state.bronze_table != "test_bronze_table":
                logger.error("❌ Loaded state doesn't match")
                return False
            
            logger.info("✅ State persistence and loading working")
            
            # Test recovery detection
            recoverable = state_manager.find_recoverable_pipelines()
            if len(recoverable) != 1:
                logger.error("❌ Recovery detection failed")
                return False
            
            # Test marking as completed
            state_manager.mark_completed()
            if state_manager.current_state.state != PipelineState.COMPLETED:
                logger.error("❌ Mark completed failed")
                return False
            
            # Test state summary
            summary = state_manager.get_state_summary()
            if summary["state"] != "completed":
                logger.error("❌ State summary incorrect")
                return False
            
            logger.info(f"📊 State summary:")
            logger.info(f"  Pipeline ID: {summary['pipeline_id']}")
            logger.info(f"  State: {summary['state']}")
            logger.info(f"  Duration: {summary['duration_seconds']:.2f}s")
            
            logger.success("✅ State management test PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ State management test failed: {e}")
            return False


def test_metrics_collection():
    """Test metrics collection and reporting."""
    logger = PipelineLogger.get_logger("TestMetricsCollection")
    
    logger.info("🧪 Testing Metrics Collection")
    logger.info("=" * 50)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        settings = PipelineSettings(
            data={
                "input_path": Path("real_estate_data"),
                "output_path": temp_path,
                "properties_file": "properties_sf.json",
                "sample_size": 2
            },
            processing={
                "generate_embeddings": False  # Disable for faster test
            },
            dry_run=True,  # Don't write output
            environment="test"
        )
        
        try:
            orchestrator = PipelineOrchestrator(settings)
            orchestrator.run()
            
            # Get metrics
            metrics = orchestrator.get_metrics()
            
            # Validate metrics
            required_metrics = [
                "records_processed",
                "bronze_records",
                "silver_records",
                "gold_records",
                "tables_created",
                "processing_time",
                "enrichment_completeness"
            ]
            
            for metric in required_metrics:
                if metric not in metrics:
                    logger.error(f"❌ Missing metric: {metric}")
                    return False
            
            # Display metrics
            logger.info("📊 Collected Metrics:")
            logger.info(f"  Records processed: {metrics['records_processed']}")
            logger.info(f"  Bronze records: {metrics['bronze_records']}")
            logger.info(f"  Silver records: {metrics['silver_records']}")
            logger.info(f"  Gold records: {metrics['gold_records']}")
            logger.info(f"  Tables created: {metrics['tables_created']}")
            logger.info(f"  Processing time: {metrics['processing_time']:.2f}s")
            logger.info(f"  Enrichment completeness: {metrics['enrichment_completeness']:.2%}")
            
            # Get status
            status = orchestrator.get_status()
            
            if "pipeline_id" not in status:
                logger.error("❌ Status missing pipeline_id")
                return False
            
            if status["state"] != "completed":
                logger.error(f"❌ Unexpected status state: {status['state']}")
                return False
            
            logger.info(f"  Pipeline status: {status['state']}")
            
            # Cleanup
            orchestrator.cleanup()
            
            logger.success("✅ Metrics collection test PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Metrics collection test failed: {e}")
            return False


def test_complete_orchestration():
    """Test complete end-to-end orchestration."""
    logger = PipelineLogger.get_logger("TestCompleteOrchestration")
    
    logger.info("🧪 Testing Complete End-to-End Orchestration")
    logger.info("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test with YAML configuration
        config_path = Path("squack_pipeline/config.yaml")
        
        from squack_pipeline.config.settings import EmbeddingProvider
        
        settings = PipelineSettings.load_from_yaml(config_path)
        settings.data.output_path = temp_path
        settings.data.sample_size = 3
        settings.embedding.provider = EmbeddingProvider.MOCK
        settings.processing.generate_embeddings = True
        settings.dry_run = False
        settings.validate_output = True
        
        try:
            # Run complete pipeline
            orchestrator = PipelineOrchestrator(settings)
            
            # Track state changes
            initial_state = orchestrator.state_manager.current_state.state
            
            orchestrator.run()
            
            # Verify state progression
            final_state = orchestrator.state_manager.current_state.state
            if final_state != PipelineState.COMPLETED:
                logger.error(f"❌ Pipeline didn't complete: {final_state}")
                return False
            
            # Get comprehensive metrics
            metrics = orchestrator.get_metrics()
            status = orchestrator.get_status()
            
            # Verify all phases completed
            if metrics['bronze_records'] == 0:
                logger.error("❌ No Bronze records processed")
                return False
            
            if metrics['silver_records'] == 0:
                logger.error("❌ No Silver records processed")
                return False
            
            if metrics['gold_records'] == 0:
                logger.error("❌ No Gold records processed")
                return False
            
            # Verify output files created
            parquet_files = list(temp_path.glob("*.parquet"))
            if len(parquet_files) == 0:
                logger.error("❌ No output files created")
                return False
            
            # Display orchestration summary
            logger.info("📊 Orchestration Summary:")
            logger.info(f"  Pipeline ID: {status['pipeline_id']}")
            logger.info(f"  Environment: {status['environment']}")
            logger.info(f"  Duration: {status['duration_seconds']:.2f}s")
            logger.info(f"  Final state: {status['state']}")
            logger.info(f"  Tables created: {metrics['tables_created']}")
            logger.info(f"  Output files: {len(parquet_files)}")
            
            # Verify state file exists
            state_file = orchestrator.state_manager.state_file
            if not state_file.exists():
                logger.error("❌ State file not persisted")
                return False
            
            # Load and verify state
            with open(state_file, 'r') as f:
                saved_state = json.load(f)
            
            if saved_state['state'] != 'completed':
                logger.error("❌ Saved state incorrect")
                return False
            
            logger.info(f"  State persisted: {state_file.name}")
            
            # Test cleanup
            orchestrator.cleanup()
            
            logger.success("✅ Complete orchestration test PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Complete orchestration test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_error_handling():
    """Test error handling and recovery."""
    logger = PipelineLogger.get_logger("TestErrorHandling")
    
    logger.info("🧪 Testing Error Handling and Recovery")
    logger.info("=" * 55)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create settings with invalid input to trigger error
        settings = PipelineSettings(
            data={
                "input_path": Path("non_existent_directory"),
                "output_path": temp_path,
                "properties_file": "non_existent.json",
                "sample_size": 1
            },
            dry_run=False
        )
        
        try:
            orchestrator = PipelineOrchestrator(settings)
            
            # This should fail gracefully
            try:
                orchestrator.run()
                logger.error("❌ Pipeline should have failed but didn't")
                return False
            except Exception as e:
                # Expected failure
                logger.info(f"✅ Pipeline failed as expected: {str(e)[:100]}")
            
            # Check that state was marked as failed
            if orchestrator.state_manager.current_state.state != PipelineState.FAILED:
                logger.error("❌ State not marked as failed")
                return False
            
            if not orchestrator.state_manager.current_state.error_message:
                logger.error("❌ Error message not recorded")
                return False
            
            logger.info(f"  Error state: {orchestrator.state_manager.current_state.state.value}")
            logger.info(f"  Error phase: {orchestrator.state_manager.current_state.error_phase}")
            
            logger.success("✅ Error handling test PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error handling test failed unexpectedly: {e}")
            return False


def main():
    """Run all Phase 6 tests."""
    logger = PipelineLogger.get_logger("Phase6Tests")
    
    logger.info("🎯 SQUACK Pipeline Phase 6 Test Suite")
    logger.info("=" * 60)
    
    tests = [
        ("CLI Interface", test_cli_interface),
        ("State Management", test_state_management),
        ("Metrics Collection", test_metrics_collection),
        ("Complete Orchestration", test_complete_orchestration),
        ("Error Handling", test_error_handling)
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
    logger.info(f"📊 Phase 6 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.success("🎉 All Phase 6 tests PASSED!")
        logger.info("\n🚀 Phase 6 (Complete Orchestration) is ready!")
        logger.info("✨ CLI interface with typer working")
        logger.info("💾 Pipeline state management and recovery implemented")
        logger.info("📊 Comprehensive metrics collection and reporting")
        logger.info("🎯 End-to-end orchestration validated")
        logger.info("⚡ Error handling and graceful failure")
        return True
    else:
        logger.error(f"💥 {total - passed} test(s) FAILED")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)