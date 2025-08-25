"""
Metrics calculator for embedding evaluation.

Calculates Precision, Recall, F1 Score, and other IR metrics.
"""

import math
from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class QueryMetrics:
    """Metrics for a single query."""
    query_id: str
    precision_at_k: Dict[int, float] = field(default_factory=dict)
    recall_at_k: Dict[int, float] = field(default_factory=dict)
    f1_at_k: Dict[int, float] = field(default_factory=dict)
    map_score: float = 0.0  # Mean Average Precision
    mrr_score: float = 0.0  # Mean Reciprocal Rank
    ndcg_at_k: Dict[int, float] = field(default_factory=dict)
    relevant_retrieved: int = 0
    total_retrieved: int = 0
    total_relevant: int = 0


@dataclass
class AggregateMetrics:
    """Aggregate metrics across all queries."""
    mean_precision_at_k: Dict[int, float] = field(default_factory=dict)
    mean_recall_at_k: Dict[int, float] = field(default_factory=dict)
    mean_f1_at_k: Dict[int, float] = field(default_factory=dict)
    mean_map: float = 0.0
    mean_mrr: float = 0.0
    mean_ndcg_at_k: Dict[int, float] = field(default_factory=dict)
    
    # Category-wise metrics
    category_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Overall metrics
    overall_precision: float = 0.0
    overall_recall: float = 0.0
    overall_f1: float = 0.0


class MetricsCalculator:
    """Calculates IR metrics for embedding evaluation."""
    
    def __init__(self, k_values: List[int] = None):
        """
        Initialize metrics calculator.
        
        Args:
            k_values: List of k values for Precision@K, Recall@K calculations
        """
        self.k_values = k_values or [1, 3, 5, 10]
    
    def calculate(
        self,
        results: Dict[str, List[Tuple[int, float]]],
        ground_truth: Dict[str, Any]
    ) -> AggregateMetrics:
        """
        Calculate metrics for all queries.
        
        Args:
            results: Dict mapping query_id to list of (page_id, similarity_score) tuples
            ground_truth: Ground truth data with relevance annotations
            
        Returns:
            AggregateMetrics object
        """
        query_metrics = []
        category_results = {}
        
        for query_data in ground_truth.get("queries", []):
            query_id = query_data["query_id"]
            category = query_data["category"]
            relevance_annotations = query_data["relevance_annotations"]
            
            # Get retrieved results for this query
            retrieved = results.get(query_id, [])
            
            # Calculate metrics for this query
            metrics = self.calculate_query_metrics(
                retrieved=retrieved,
                relevance_annotations=relevance_annotations,
                query_id=query_id
            )
            
            query_metrics.append(metrics)
            
            # Track by category
            if category not in category_results:
                category_results[category] = []
            category_results[category].append(metrics)
        
        # Calculate aggregate metrics
        aggregate = self.aggregate_metrics(query_metrics, category_results)
        
        return aggregate
    
    def calculate_query_metrics(
        self,
        retrieved: List[Tuple[int, float]],
        relevance_annotations: Dict[str, int],
        query_id: str
    ) -> QueryMetrics:
        """
        Calculate metrics for a single query.
        
        Args:
            retrieved: List of (page_id, similarity_score) tuples
            relevance_annotations: Dict mapping page_id (as string) to relevance score
            query_id: Query identifier
            
        Returns:
            QueryMetrics object
        """
        metrics = QueryMetrics(query_id=query_id)
        
        # Convert relevance annotations keys to int
        relevance_scores = {
            int(page_id): score 
            for page_id, score in relevance_annotations.items()
        }
        
        # Get relevant documents (score > 0)
        relevant_ids = {
            page_id for page_id, score in relevance_scores.items() 
            if score > 0
        }
        
        # Extract retrieved page IDs
        retrieved_ids = [page_id for page_id, _ in retrieved]
        
        # Calculate metrics at different k values
        for k in self.k_values:
            metrics.precision_at_k[k] = self.calculate_precision_at_k(
                retrieved_ids, relevant_ids, k
            )
            metrics.recall_at_k[k] = self.calculate_recall_at_k(
                retrieved_ids, relevant_ids, k
            )
            metrics.f1_at_k[k] = self.calculate_f1_at_k(
                metrics.precision_at_k[k], 
                metrics.recall_at_k[k]
            )
            metrics.ndcg_at_k[k] = self.calculate_ndcg(
                retrieved_ids, relevance_scores, k
            )
        
        # Calculate MAP and MRR
        metrics.map_score = self.calculate_average_precision(
            retrieved_ids, relevant_ids
        )
        metrics.mrr_score = self.calculate_reciprocal_rank(
            retrieved_ids, relevant_ids
        )
        
        # Overall counts
        metrics.total_retrieved = len(retrieved_ids)
        metrics.total_relevant = len(relevant_ids)
        metrics.relevant_retrieved = len(
            [id for id in retrieved_ids if id in relevant_ids]
        )
        
        return metrics
    
    def calculate_precision_at_k(
        self,
        retrieved_ids: List[int],
        relevant_ids: Set[int],
        k: int
    ) -> float:
        """
        Calculate precision at rank K.
        
        Args:
            retrieved_ids: List of retrieved document IDs
            relevant_ids: Set of relevant document IDs
            k: Cutoff rank
            
        Returns:
            Precision@K score
        """
        if k == 0 or len(retrieved_ids) == 0:
            return 0.0
        
        retrieved_at_k = retrieved_ids[:k]
        relevant_retrieved = len([id for id in retrieved_at_k if id in relevant_ids])
        
        return relevant_retrieved / min(k, len(retrieved_at_k))
    
    def calculate_recall_at_k(
        self,
        retrieved_ids: List[int],
        relevant_ids: Set[int],
        k: int
    ) -> float:
        """
        Calculate recall at rank K.
        
        Args:
            retrieved_ids: List of retrieved document IDs
            relevant_ids: Set of relevant document IDs
            k: Cutoff rank
            
        Returns:
            Recall@K score
        """
        if len(relevant_ids) == 0:
            return 0.0
        
        retrieved_at_k = retrieved_ids[:k]
        relevant_retrieved = len([id for id in retrieved_at_k if id in relevant_ids])
        
        return relevant_retrieved / len(relevant_ids)
    
    def calculate_f1_at_k(self, precision: float, recall: float) -> float:
        """
        Calculate F1 score from precision and recall.
        
        Args:
            precision: Precision score
            recall: Recall score
            
        Returns:
            F1 score
        """
        if precision + recall == 0:
            return 0.0
        
        return 2 * (precision * recall) / (precision + recall)
    
    def calculate_average_precision(
        self,
        retrieved_ids: List[int],
        relevant_ids: Set[int]
    ) -> float:
        """
        Calculate Average Precision (AP).
        
        Args:
            retrieved_ids: List of retrieved document IDs
            relevant_ids: Set of relevant document IDs
            
        Returns:
            Average Precision score
        """
        if len(relevant_ids) == 0:
            return 0.0
        
        precision_sum = 0.0
        relevant_count = 0
        
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in relevant_ids:
                relevant_count += 1
                precision_sum += relevant_count / (i + 1)
        
        if relevant_count == 0:
            return 0.0
        
        return precision_sum / len(relevant_ids)
    
    def calculate_reciprocal_rank(
        self,
        retrieved_ids: List[int],
        relevant_ids: Set[int]
    ) -> float:
        """
        Calculate Reciprocal Rank (RR).
        
        Args:
            retrieved_ids: List of retrieved document IDs
            relevant_ids: Set of relevant document IDs
            
        Returns:
            Reciprocal Rank score
        """
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in relevant_ids:
                return 1.0 / (i + 1)
        
        return 0.0
    
    def calculate_ndcg(
        self,
        retrieved_ids: List[int],
        relevance_scores: Dict[int, int],
        k: int
    ) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain (NDCG).
        
        Args:
            retrieved_ids: List of retrieved document IDs
            relevance_scores: Dict mapping document ID to relevance score
            k: Cutoff rank
            
        Returns:
            NDCG@K score
        """
        # Calculate DCG
        dcg = 0.0
        for i, doc_id in enumerate(retrieved_ids[:k]):
            relevance = relevance_scores.get(doc_id, 0)
            if i == 0:
                dcg += relevance
            else:
                dcg += relevance / math.log2(i + 1)
        
        # Calculate ideal DCG
        ideal_scores = sorted(relevance_scores.values(), reverse=True)[:k]
        idcg = 0.0
        for i, score in enumerate(ideal_scores):
            if i == 0:
                idcg += score
            else:
                idcg += score / math.log2(i + 1)
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    def aggregate_metrics(
        self,
        query_metrics: List[QueryMetrics],
        category_results: Dict[str, List[QueryMetrics]]
    ) -> AggregateMetrics:
        """
        Aggregate metrics across all queries.
        
        Args:
            query_metrics: List of QueryMetrics for all queries
            category_results: Metrics grouped by category
            
        Returns:
            AggregateMetrics object
        """
        aggregate = AggregateMetrics()
        
        if not query_metrics:
            return aggregate
        
        # Calculate mean metrics across all queries
        for k in self.k_values:
            precisions = [m.precision_at_k.get(k, 0) for m in query_metrics]
            recalls = [m.recall_at_k.get(k, 0) for m in query_metrics]
            f1s = [m.f1_at_k.get(k, 0) for m in query_metrics]
            ndcgs = [m.ndcg_at_k.get(k, 0) for m in query_metrics]
            
            aggregate.mean_precision_at_k[k] = sum(precisions) / len(precisions)
            aggregate.mean_recall_at_k[k] = sum(recalls) / len(recalls)
            aggregate.mean_f1_at_k[k] = sum(f1s) / len(f1s)
            aggregate.mean_ndcg_at_k[k] = sum(ndcgs) / len(ndcgs)
        
        # Calculate mean MAP and MRR
        maps = [m.map_score for m in query_metrics]
        mrrs = [m.mrr_score for m in query_metrics]
        aggregate.mean_map = sum(maps) / len(maps)
        aggregate.mean_mrr = sum(mrrs) / len(mrrs)
        
        # Calculate overall precision, recall, F1
        total_relevant_retrieved = sum(m.relevant_retrieved for m in query_metrics)
        total_retrieved = sum(m.total_retrieved for m in query_metrics)
        total_relevant = sum(m.total_relevant for m in query_metrics)
        
        if total_retrieved > 0:
            aggregate.overall_precision = total_relevant_retrieved / total_retrieved
        
        if total_relevant > 0:
            aggregate.overall_recall = total_relevant_retrieved / total_relevant
        
        if aggregate.overall_precision + aggregate.overall_recall > 0:
            aggregate.overall_f1 = (
                2 * (aggregate.overall_precision * aggregate.overall_recall) /
                (aggregate.overall_precision + aggregate.overall_recall)
            )
        
        # Calculate category-wise metrics
        for category, metrics_list in category_results.items():
            if not metrics_list:
                continue
            
            cat_metrics = {}
            
            # Mean precision@5 for category
            p5s = [m.precision_at_k.get(5, 0) for m in metrics_list]
            cat_metrics["precision_at_5"] = sum(p5s) / len(p5s) if p5s else 0
            
            # Mean recall@10 for category
            r10s = [m.recall_at_k.get(10, 0) for m in metrics_list]
            cat_metrics["recall_at_10"] = sum(r10s) / len(r10s) if r10s else 0
            
            # Mean F1@5 for category
            f5s = [m.f1_at_k.get(5, 0) for m in metrics_list]
            cat_metrics["f1_at_5"] = sum(f5s) / len(f5s) if f5s else 0
            
            # Mean MAP for category
            cat_maps = [m.map_score for m in metrics_list]
            cat_metrics["map"] = sum(cat_maps) / len(cat_maps) if cat_maps else 0
            
            aggregate.category_metrics[category] = cat_metrics
        
        return aggregate
    
    def format_metrics(self, metrics: AggregateMetrics) -> str:
        """
        Format metrics for display.
        
        Args:
            metrics: AggregateMetrics object
            
        Returns:
            Formatted string representation
        """
        lines = []
        lines.append("=" * 60)
        lines.append("EVALUATION METRICS")
        lines.append("=" * 60)
        
        # Overall metrics
        lines.append("\nOVERALL METRICS:")
        lines.append(f"  Precision: {metrics.overall_precision:.3f}")
        lines.append(f"  Recall: {metrics.overall_recall:.3f}")
        lines.append(f"  F1 Score: {metrics.overall_f1:.3f}")
        lines.append(f"  Mean Average Precision (MAP): {metrics.mean_map:.3f}")
        lines.append(f"  Mean Reciprocal Rank (MRR): {metrics.mean_mrr:.3f}")
        
        # Metrics at different K values
        lines.append("\nMETRICS AT DIFFERENT K VALUES:")
        for k in sorted(metrics.mean_precision_at_k.keys()):
            lines.append(f"\n  @K={k}:")
            lines.append(f"    Precision: {metrics.mean_precision_at_k[k]:.3f}")
            lines.append(f"    Recall: {metrics.mean_recall_at_k[k]:.3f}")
            lines.append(f"    F1: {metrics.mean_f1_at_k[k]:.3f}")
            lines.append(f"    NDCG: {metrics.mean_ndcg_at_k[k]:.3f}")
        
        # Category-wise metrics
        if metrics.category_metrics:
            lines.append("\nCATEGORY-WISE METRICS:")
            for category, cat_metrics in metrics.category_metrics.items():
                lines.append(f"\n  {category.upper()}:")
                for metric_name, value in cat_metrics.items():
                    lines.append(f"    {metric_name}: {value:.3f}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)