"""
Model comparison logic.

Simple, clean comparison of multiple model evaluation results.
NO statistical significance testing - just straightforward winner determination.
"""

import logging
from typing import Dict, List, Any
from datetime import datetime

from .test_config import TestConfig

logger = logging.getLogger(__name__)


class ModelComparator:
    """
    Compares evaluation results from multiple models.
    
    Simple winner determination based on primary metric.
    """
    
    def __init__(self, test_config: TestConfig):
        """
        Initialize comparator.
        
        Args:
            test_config: Test configuration with comparison settings
        """
        self.test_config = test_config
        
    def compare(self, results: Dict[str, Dict]) -> Dict:
        """
        Compare model results and determine winner.
        
        Simple comparison based on primary metric without complex statistics.
        
        Args:
            results: Dictionary of model results
            
        Returns:
            Comparison results with winner
        """
        logger.info("\n" + "="*80)
        logger.info("MODEL COMPARISON RESULTS")
        logger.info("="*80)
        
        # Extract metrics for comparison
        model_metrics = {}
        for model_name, result in results.items():
            if "metrics" in result:
                metrics = result["metrics"]
                model_metrics[model_name] = {
                    "precision": metrics.overall_precision,
                    "recall": metrics.overall_recall,
                    "f1_score": metrics.overall_f1,
                    "map": metrics.mean_map,
                    "mrr": metrics.mean_mrr
                }
        
        if not model_metrics:
            logger.error("No valid metrics to compare")
            return {"error": "No valid metrics"}
        
        # Determine overall winner based on primary metric
        primary_metric = self.test_config.comparison.primary_metric
        winner = self._determine_winner(model_metrics, primary_metric)
        
        # Create ranking
        ranking = self._create_ranking(model_metrics, primary_metric)
        
        # Category winners (if available)
        category_winners = self._determine_category_winners(results)
        
        # Build comparison results
        comparison_results = {
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "dataset": self.test_config.evaluation.dataset,
                "top_k": self.test_config.evaluation.top_k,
                "primary_metric": primary_metric,
                "models_compared": len(model_metrics)
            },
            "overall_winner": winner,
            "ranking": ranking,
            "model_metrics": model_metrics,
            "category_winners": category_winners,
            "winner": winner  # For backward compatibility
        }
        
        # Print summary
        self._print_summary(comparison_results)
        
        return comparison_results
    
    def _determine_winner(self, model_metrics: Dict, primary_metric: str) -> str:
        """
        Determine overall winner based on primary metric.
        
        Args:
            model_metrics: Dictionary of model metrics
            primary_metric: Metric to use for winner determination
            
        Returns:
            Name of winning model
        """
        winner = None
        best_score = -1
        
        for model_name, metrics in model_metrics.items():
            score = metrics.get(primary_metric, 0)
            if score > best_score:
                best_score = score
                winner = model_name
        
        return winner
    
    def _create_ranking(self, model_metrics: Dict, primary_metric: str) -> List[Dict]:
        """
        Create ranking of models based on primary metric.
        
        Args:
            model_metrics: Dictionary of model metrics
            primary_metric: Metric to use for ranking
            
        Returns:
            List of models ranked by performance
        """
        ranking = []
        
        # Sort models by primary metric
        sorted_models = sorted(
            model_metrics.items(),
            key=lambda x: x[1].get(primary_metric, 0),
            reverse=True
        )
        
        for rank, (model_name, metrics) in enumerate(sorted_models, 1):
            ranking.append({
                "rank": rank,
                "model": model_name,
                primary_metric: metrics.get(primary_metric, 0),
                "precision": metrics.get("precision", 0),
                "recall": metrics.get("recall", 0),
                "f1_score": metrics.get("f1_score", 0)
            })
        
        return ranking
    
    def _determine_category_winners(self, results: Dict) -> Dict:
        """
        Determine winners for each category.
        
        Args:
            results: Full evaluation results
            
        Returns:
            Dictionary of category winners
        """
        category_winners = {}
        categories = ["geographic", "landmark", "historical", "administrative", "semantic"]
        
        for category in categories:
            best_model = None
            best_score = -1
            
            for model_name, result in results.items():
                if "metrics" in result and hasattr(result["metrics"], "category_metrics"):
                    cat_metrics = result["metrics"].category_metrics.get(category, {})
                    score = cat_metrics.get("f1_at_5", 0)
                    
                    if score > best_score:
                        best_score = score
                        best_model = model_name
            
            if best_model:
                category_winners[category] = {
                    "winner": best_model,
                    "f1_score": best_score
                }
        
        return category_winners
    
    def _print_summary(self, comparison_results: Dict):
        """
        Print comparison summary.
        
        Args:
            comparison_results: Comparison results to summarize
        """
        logger.info(f"\nDataset: {comparison_results['configuration']['dataset'].upper()}")
        logger.info(f"Primary Metric: {comparison_results['configuration']['primary_metric']}")
        logger.info(f"Models Compared: {comparison_results['configuration']['models_compared']}")
        
        logger.info("\n" + "-"*40)
        logger.info("OVERALL RANKING")
        logger.info("-"*40)
        
        for item in comparison_results["ranking"]:
            metric_value = item[comparison_results['configuration']['primary_metric']]
            logger.info(
                f"{item['rank']}. {item['model']:<20} "
                f"{comparison_results['configuration']['primary_metric'].upper()}: {metric_value:.3f} | "
                f"P: {item['precision']:.3f} | R: {item['recall']:.3f} | F1: {item['f1_score']:.3f}"
            )
        
        if comparison_results.get("category_winners"):
            logger.info("\n" + "-"*40)
            logger.info("CATEGORY WINNERS")
            logger.info("-"*40)
            
            for category, winner_info in comparison_results["category_winners"].items():
                logger.info(
                    f"{category.capitalize():<15} → {winner_info['winner']} "
                    f"(F1: {winner_info['f1_score']:.3f})"
                )
        
        logger.info("\n" + "="*40)
        logger.info(f"🏆 OVERALL WINNER: {comparison_results['overall_winner']}")
        logger.info("="*40)