#!/usr/bin/env python3
"""
Run model comparison evaluation.

Simple, sequential evaluation of multiple embedding models for comparison.
NO parallel execution, NO caching - clean and straightforward.
"""

import argparse
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from ..models.config import ExtendedConfig, load_config_from_yaml
from ..storage.chromadb_store import ChromaDBStore
from ..utils import setup_logging, get_logger
from .test_config import TestConfig, load_test_config
from .evaluation_runner import EvaluationRunner
from .model_comparator import ModelComparator

# Configure logging
setup_logging()
logger = get_logger(__name__)


class ComparisonRunner:
    """
    Orchestrates sequential model comparison.
    
    Simple, clean implementation without parallel execution or caching.
    """
    
    def __init__(self, test_config: TestConfig, base_config: ExtendedConfig):
        """
        Initialize comparison runner.
        
        Args:
            test_config: Test configuration with models to compare
            base_config: Base configuration for embeddings
        """
        self.test_config = test_config
        self.base_config = base_config
        self.results = {}
        
    def check_collection_exists(self, collection_name: str) -> bool:
        """
        Check if a ChromaDB collection exists.
        
        Args:
            collection_name: Name of collection to check
            
        Returns:
            True if collection exists
        """
        try:
            store = ChromaDBStore(self.base_config.chromadb)
            collections = store.client.list_collections()
            return any(c.name == collection_name for c in collections)
        except Exception as e:
            logger.error(f"Error checking collection {collection_name}: {e}")
            return False
    
    def run_comparison(self) -> Dict:
        """
        Run sequential evaluation on all configured models.
        
        Returns:
            Comparison results dictionary
        """
        logger.info("="*80)
        logger.info("MODEL COMPARISON - SEQUENTIAL EVALUATION")
        logger.info("="*80)
        logger.info(f"Dataset: {self.test_config.evaluation.dataset}")
        logger.info(f"Models to compare: {len(self.test_config.models)}")
        
        # Check all collections exist before starting
        logger.info("\nChecking collections...")
        for model_config in self.test_config.models:
            # Use generated collection name
            collection_name = model_config.collection_name or model_config.generate_collection_name()
            exists = self.check_collection_exists(collection_name)
            status = "✅ Found" if exists else "❌ Missing"
            logger.info(f"  {model_config.name}: {status} ({collection_name})")
            
            if not exists:
                logger.warning(f"Collection {collection_name} not found!")
                logger.info(f"Creating embeddings for {model_config.name}...")
                
                # Automatically create embeddings from gold articles
                try:
                    import subprocess
                    import sys
                    
                    # Determine dataset files based on test config
                    if self.test_config.evaluation.dataset == "gold":
                        articles_file = "common_embeddings/evaluate_data/gold_articles.json"
                    else:
                        articles_file = "common_embeddings/evaluate_data/evaluate_articles.json"
                    
                    # Create embeddings using main.py with evaluation data
                    cmd = [
                        sys.executable, "-m", "common_embeddings.main", "create",
                        "--collection-name", collection_name,
                        "--data-type", "evaluation",
                        "--evaluation-json", articles_file,
                        "--force-recreate"
                    ]
                    
                    # Add model-specific arguments based on provider
                    if model_config.provider == "ollama":
                        cmd.extend(["--provider", "ollama", "--ollama-model", model_config.name])
                    elif model_config.provider == "openai":
                        cmd.extend(["--provider", "openai", "--openai-model", model_config.name])
                    elif model_config.provider == "gemini":
                        cmd.extend(["--provider", "gemini", "--gemini-model", model_config.name])
                    elif model_config.provider == "voyage":
                        cmd.extend(["--provider", "voyage", "--voyage-model", model_config.name])
                    
                    # Use the eval config if specified
                    if self.test_config.base_config:
                        cmd.extend(["--config", self.test_config.base_config])
                    
                    logger.info(f"Creating embeddings with: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        logger.error(f"Failed to create embeddings: {result.stderr}")
                        logger.error(f"Error output: {result.stdout}")
                        return None
                    
                    logger.info(f"✅ Successfully created embeddings for {model_config.name}")
                    
                except Exception as e:
                    logger.error(f"Failed to create embeddings: {e}")
                    return None
        
        # Sequential evaluation of each model
        logger.info("\nStarting sequential evaluation...")
        logger.info("-"*40)
        
        for i, model_config in enumerate(self.test_config.models, 1):
            logger.info(f"\n[{i}/{len(self.test_config.models)}] Evaluating {model_config.name}")
            logger.info(f"  Collection: {model_config.collection_name}")
            
            try:
                # Run evaluation using existing EvaluationRunner
                runner = EvaluationRunner(self.base_config)
                
                # Determine dataset files
                if self.test_config.evaluation.dataset == "gold":
                    articles_json = Path("common_embeddings/evaluate_data/gold_articles.json")
                    queries_json = Path("common_embeddings/evaluate_data/gold_queries.json")
                else:
                    articles_json = Path("common_embeddings/evaluate_data/evaluate_articles.json")
                    queries_json = Path("common_embeddings/evaluate_data/evaluate_queries.json")
                
                # Use the generated collection name
                collection_name = model_config.collection_name or model_config.generate_collection_name()
                
                # Run evaluation
                metrics, report_path = runner.run_evaluation(
                    articles_json=articles_json,
                    queries_json=queries_json,
                    collection_name=collection_name,
                    output_dir=Path(self.test_config.reporting.output_directory) / model_config.name
                )
                
                # Store results
                self.results[model_config.name] = {
                    "metrics": metrics,
                    "report_path": str(report_path),
                    "collection_name": model_config.collection_name,
                    "provider": model_config.provider
                }
                
                # Log key metrics
                logger.info(f"  ✅ Complete - F1: {metrics.overall_f1:.3f}, Precision: {metrics.overall_precision:.3f}, Recall: {metrics.overall_recall:.3f}")
                
            except Exception as e:
                logger.error(f"  ❌ Failed: {e}")
                self.results[model_config.name] = {
                    "error": str(e),
                    "collection_name": model_config.collection_name,
                    "provider": model_config.provider
                }
        
        logger.info("\n" + "="*80)
        logger.info("EVALUATION COMPLETE")
        logger.info("="*80)
        
        # Compare results if all evaluations succeeded
        if all("metrics" in r for r in self.results.values()):
            comparator = ModelComparator(self.test_config)
            comparison_results = comparator.compare(self.results)
            
            # Save comparison results
            self._save_comparison_results(comparison_results)
            
            return comparison_results
        else:
            logger.error("Some evaluations failed - cannot perform comparison")
            return self.results
    
    def _save_comparison_results(self, comparison_results: Dict):
        """
        Save comparison results to output directory.
        
        Args:
            comparison_results: Comparison results to save
        """
        output_dir = Path(self.test_config.reporting.output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save JSON results
        output_file = output_dir / f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(comparison_results, f, indent=2, default=str)
        
        logger.info(f"\nComparison results saved to: {output_file}")


def main():
    """Main entry point for model comparison."""
    parser = argparse.ArgumentParser(
        description="Compare multiple embedding models"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(level=args.log_level)
    
    try:
        # Load configurations - always use test.config.yaml
        logger.info("Loading configurations...")
        test_config = load_test_config("common_embeddings/test.config.yaml")
        
        # Use base_config from test config if specified, otherwise default
        if test_config.base_config:
            base_config = load_config_from_yaml(test_config.base_config)
            logger.info(f"Using eval config: {test_config.base_config}")
        else:
            base_config = load_config_from_yaml("common_embeddings/config.yaml")
            logger.info("Using default config: common_embeddings/config.yaml")
        
        # Run comparison
        runner = ComparisonRunner(test_config, base_config)
        results = runner.run_comparison()
        
        if results and "winner" in results:
            logger.info(f"\n🏆 WINNER: {results['winner']}")
        
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())