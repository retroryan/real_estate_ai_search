"""
Evaluation runner for Wikipedia embeddings.

Orchestrates the evaluation process.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime

from ..models import Config
from ..services import CollectionManager
from ..storage import ChromaDBStore
from .metrics_calculator import MetricsCalculator, AggregateMetrics
from .report_generator import ReportGenerator


class EvaluationRunner:
    """Runs evaluation on Wikipedia embeddings."""
    
    def __init__(self, config: Config):
        """
        Initialize evaluation runner.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.collection_manager = CollectionManager(config)
        self.metrics_calculator = MetricsCalculator()
        self.report_generator = ReportGenerator()
        
        # Initialize ChromaDB store
        self.chroma_store = ChromaDBStore(config.chromadb)
    
    def run_evaluation(
        self,
        articles_json: Path,
        queries_json: Path,
        collection_name: str,
        output_dir: Path = Path("common_embeddings/evaluate_results")
    ) -> Tuple[AggregateMetrics, str]:
        """
        Run complete evaluation.
        
        Args:
            articles_json: Path to articles JSON file
            queries_json: Path to queries JSON file
            collection_name: Name of ChromaDB collection to query
            output_dir: Directory for output files
            
        Returns:
            Tuple of (metrics, report_path)
        """
        # Load queries
        with open(queries_json) as f:
            queries_data = json.load(f)
        
        queries = queries_data["queries"]
        
        # Execute queries against collection
        results = self._execute_queries(queries, collection_name)
        
        # Calculate metrics
        metrics = self.metrics_calculator.calculate(results, queries_data)
        
        # Generate report
        report_path = self.report_generator.generate(
            metrics=metrics,
            queries_json=queries_json,
            articles_json=articles_json,
            output_dir=output_dir
        )
        
        # Save metrics to JSON
        metrics_path = output_dir / "metrics_summary.json"
        self._save_metrics(metrics, metrics_path)
        
        # Save detailed results
        results_path = output_dir / "detailed_results.json"
        self._save_results(results, queries, metrics, results_path)
        
        return metrics, report_path
    
    def _execute_queries(
        self,
        queries: List[Dict[str, Any]],
        collection_name: str
    ) -> Dict[str, List[Tuple[int, float]]]:
        """
        Execute queries against ChromaDB collection.
        
        Args:
            queries: List of query dictionaries
            collection_name: Name of collection to query
            
        Returns:
            Dict mapping query_id to list of (page_id, similarity) tuples
        """
        results = {}
        
        # Get collection
        self.chroma_store.create_collection(
            name=collection_name,
            metadata={"evaluation": True},
            force_recreate=False
        )
        collection = self.chroma_store.collection
        
        # Create embedding function to match what was used during indexing
        from common_embeddings import EmbeddingPipeline
        pipeline = EmbeddingPipeline(self.config)
        
        for query in queries:
            query_id = query["query_id"]
            query_text = query["query_text"]
            
            # Generate embedding for query using the same model
            query_embedding = pipeline.embed_model.get_query_embedding(query_text)
            
            # Query collection with pre-computed embedding
            query_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=10  # Get top 10 results
            )
            
            # Extract page_ids and distances
            retrieved = []
            if query_results["ids"] and len(query_results["ids"]) > 0:
                ids = query_results["ids"][0]
                distances = query_results["distances"][0] if "distances" in query_results else []
                metadatas = query_results["metadatas"][0] if "metadatas" in query_results else []
                
                for i, doc_id in enumerate(ids):
                    # Extract page_id from metadata or document ID
                    if metadatas and i < len(metadatas):
                        page_id = int(metadatas[i].get("page_id", doc_id.split("_")[0]))
                    else:
                        page_id = int(doc_id.split("_")[0])
                    
                    # Convert distance to similarity (1 - distance for cosine)
                    similarity = 1 - distances[i] if distances and i < len(distances) else 0.5
                    
                    retrieved.append((page_id, similarity))
            
            results[query_id] = retrieved
        
        return results
    
    def _save_metrics(self, metrics: AggregateMetrics, output_path: Path):
        """
        Save metrics to JSON file.
        
        Args:
            metrics: Aggregate metrics
            output_path: Path to save JSON
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        metrics_dict = {
            "overall": {
                "precision": metrics.overall_precision,
                "recall": metrics.overall_recall,
                "f1_score": metrics.overall_f1,
                "mean_map": metrics.mean_map,
                "mean_mrr": metrics.mean_mrr
            },
            "at_k_metrics": {
                "precision": metrics.mean_precision_at_k,
                "recall": metrics.mean_recall_at_k,
                "f1": metrics.mean_f1_at_k,
                "ndcg": metrics.mean_ndcg_at_k
            },
            "category_metrics": metrics.category_metrics,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(output_path, 'w') as f:
            json.dump(metrics_dict, f, indent=2)
    
    def _save_results(
        self,
        results: Dict[str, List[Tuple[int, float]]],
        queries: List[Dict[str, Any]],
        metrics: AggregateMetrics,
        output_path: Path
    ):
        """
        Save detailed results to JSON file.
        
        Args:
            results: Query results
            queries: Original queries
            metrics: Calculated metrics
            output_path: Path to save JSON
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        detailed_results = {
            "queries": [],
            "summary": {
                "total_queries": len(queries),
                "mean_precision_at_5": metrics.mean_precision_at_k.get(5, 0),
                "mean_recall_at_10": metrics.mean_recall_at_k.get(10, 0),
                "mean_f1_at_5": metrics.mean_f1_at_k.get(5, 0)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        for query in queries:
            query_id = query["query_id"]
            query_results = results.get(query_id, [])
            
            detailed_results["queries"].append({
                "query_id": query_id,
                "query_text": query["query_text"],
                "category": query["category"],
                "expected_results": query["expected_results"],
                "retrieved_results": [
                    {"page_id": page_id, "similarity": sim}
                    for page_id, sim in query_results
                ],
                "relevant_retrieved": len([
                    page_id for page_id, _ in query_results
                    if str(page_id) in query["relevance_annotations"]
                    and query["relevance_annotations"][str(page_id)] > 0
                ])
            })
        
        with open(output_path, 'w') as f:
            json.dump(detailed_results, f, indent=2)