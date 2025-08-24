#!/usr/bin/env python
"""
Run evaluation on Wikipedia embeddings with support for gold and generated datasets.

This script:
1. Creates embeddings from evaluation dataset (if needed)
2. Runs queries against the embeddings
3. Calculates metrics
4. Generates reports
"""

import sys
import argparse
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common_embeddings.models.config import ExtendedConfig, load_config_from_yaml
from common_embeddings.evaluate import EvaluationRunner
from common_embeddings.utils import setup_logging, get_logger
import yaml


def main():
    """Main evaluation function."""
    parser = argparse.ArgumentParser(
        description="Run evaluation on Wikipedia embeddings"
    )
    parser.add_argument(
        "--config",
        default="common_embeddings/config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--dataset",
        default="gold",
        choices=["gold", "generated", "both"],
        help="Which dataset to use: 'gold' (curated), 'generated' (automatic), or 'both' (compare)"
    )
    parser.add_argument(
        "--articles-json",
        help="Path to evaluation articles JSON (overrides --dataset)"
    )
    parser.add_argument(
        "--queries-json",
        help="Path to evaluation queries JSON (overrides --dataset)"
    )
    parser.add_argument(
        "--collection-name",
        help="ChromaDB collection name (auto-detected if not provided)"
    )
    parser.add_argument(
        "--output-dir",
        default="common_embeddings/evaluate_results",
        help="Output directory for results"
    )
    parser.add_argument(
        "--create-embeddings",
        action="store_true",
        help="Create embeddings before evaluation"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(level=args.log_level)
    logger = get_logger(__name__)
    
    logger.info("=" * 60)
    logger.info("Wikipedia Embeddings Evaluation")
    logger.info("=" * 60)
    
    # Load configuration using existing utility
    config = load_config_from_yaml(args.config)
    logger.info(f"Loaded configuration: provider={config.embedding.provider}")
    
    # Determine which dataset files to use
    if args.articles_json and args.queries_json:
        # Custom files provided
        articles_json = Path(args.articles_json)
        queries_json = Path(args.queries_json)
        dataset_type = "custom"
    elif args.dataset == "gold":
        # Use gold standard dataset
        articles_json = Path("common_embeddings/evaluate_data/gold_articles.json")
        queries_json = Path("common_embeddings/evaluate_data/gold_queries.json")
        dataset_type = "gold"
        
        # Create gold files if they don't exist
        if not articles_json.exists() or not queries_json.exists():
            logger.info("Gold standard files not found. Creating them...")
            from common_embeddings.evaluate.create_gold_standard import create_gold_standard
            create_gold_standard()
    elif args.dataset == "generated":
        # Use generated dataset
        articles_json = Path("common_embeddings/evaluate_data/evaluate_articles.json")
        queries_json = Path("common_embeddings/evaluate_data/evaluate_queries.json")
        dataset_type = "generated"
    else:
        # Compare both datasets
        dataset_type = "both"
    
    logger.info(f"Using dataset: {dataset_type}")
    
    # Create embeddings if requested
    if args.create_embeddings:
        logger.info("\n--- Creating Embeddings ---")
        import subprocess
        result = subprocess.run([
            sys.executable, "-m", "common_embeddings.main",
            "--data-type=evaluation",
            "--force-recreate",
            "--config", args.config
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Failed to create embeddings: {result.stderr}")
            sys.exit(1)
        
        logger.info("Successfully created embeddings")
    
    # Determine collection name if not provided
    collection_name = args.collection_name
    if not collection_name:
        # Auto-detect based on config
        from common_embeddings import EmbeddingPipeline
        pipeline = EmbeddingPipeline(config)
        model_id = pipeline.model_identifier
        collection_name = f"wikipedia_{model_id}_v1"
        logger.info(f"Using collection: {collection_name}")
    
    # Handle comparison mode
    if dataset_type == "both":
        logger.info("\n--- Comparing Gold vs Generated Datasets ---")
        
        # Run evaluation on gold dataset
        logger.info("\n📊 Evaluating Gold Standard Dataset...")
        runner = EvaluationRunner(config)
        gold_metrics, gold_report = runner.run_evaluation(
            articles_json=Path("common_embeddings/evaluate_data/gold_articles.json"),
            queries_json=Path("common_embeddings/evaluate_data/gold_queries.json"),
            collection_name=collection_name,
            output_dir=Path(args.output_dir) / "gold"
        )
        
        # Run evaluation on generated dataset
        logger.info("\n📊 Evaluating Generated Dataset...")
        gen_metrics, gen_report = runner.run_evaluation(
            articles_json=Path("common_embeddings/evaluate_data/evaluate_articles.json"),
            queries_json=Path("common_embeddings/evaluate_data/evaluate_queries.json"),
            collection_name=collection_name,
            output_dir=Path(args.output_dir) / "generated"
        )
        
        # Compare results
        logger.info("\n" + "=" * 80)
        logger.info("COMPARISON RESULTS")
        logger.info("=" * 80)
        
        logger.info("\nOverall Metrics:")
        logger.info(f"{'Metric':<25} {'Gold Standard':>15} {'Generated':>15} {'Difference':>15}")
        logger.info("-" * 70)
        
        metrics_to_compare = [
            ("Precision", "overall_precision"),
            ("Recall", "overall_recall"),
            ("F1 Score", "overall_f1"),
            ("MAP", "mean_map"),
            ("MRR", "mean_mrr")
        ]
        
        for display_name, attr_name in metrics_to_compare:
            gold_val = getattr(gold_metrics, attr_name)
            gen_val = getattr(gen_metrics, attr_name)
            diff = gold_val - gen_val
            logger.info(f"{display_name:<25} {gold_val:>15.3f} {gen_val:>15.3f} {diff:>+15.3f}")
        
        logger.info(f"\nGold report: {gold_report}")
        logger.info(f"Generated report: {gen_report}")
        
        # Exit after comparison
        logger.info("\n" + "=" * 60)
        logger.info("Comparison complete!")
        logger.info("=" * 60)
        return
    
    # Single dataset evaluation
    runner = EvaluationRunner(config)
    
    # Run evaluation
    logger.info("\n--- Running Evaluation ---")
    logger.info(f"Articles: {articles_json}")
    logger.info(f"Queries: {queries_json}")
    
    metrics, report_path = runner.run_evaluation(
        articles_json=articles_json,
        queries_json=queries_json,
        collection_name=collection_name,
        output_dir=Path(args.output_dir)
    )
    
    # Display metrics
    from common_embeddings.evaluate import MetricsCalculator
    calculator = MetricsCalculator()
    logger.info("\n" + calculator.format_metrics(metrics))
    
    # Display report path
    logger.info(f"\nEvaluation report saved to: {report_path}")
    logger.info(f"Open in browser: file://{report_path.absolute()}")
    
    # Save summary
    summary = {
        "collection_name": collection_name,
        "overall_precision": metrics.overall_precision,
        "overall_recall": metrics.overall_recall,
        "overall_f1": metrics.overall_f1,
        "mean_map": metrics.mean_map,
        "mean_mrr": metrics.mean_mrr,
        "precision_at_5": metrics.mean_precision_at_k.get(5, 0),
        "recall_at_10": metrics.mean_recall_at_k.get(10, 0)
    }
    
    logger.info("\n--- Evaluation Summary ---")
    for key, value in summary.items():
        if isinstance(value, float):
            logger.info(f"{key}: {value:.3f}")
        else:
            logger.info(f"{key}: {value}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Evaluation complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)