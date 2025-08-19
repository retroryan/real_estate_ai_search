#!/usr/bin/env python3
"""
Main CLI for the embedding pipeline comparison tool.
Simple interface for creating embeddings and comparing models.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from wiki_embed.models import Config, ModelComparison, EmbeddingProvider, EmbeddingMethod
from wiki_embed.pipeline import WikipediaEmbeddingPipeline
from wiki_embed.query import WikipediaQueryTester
from wiki_embed.utils import configure_from_config
from wiki_embed.embedding import get_model_display_name
from datetime import datetime


def create_embeddings(force_recreate: bool = False, method: EmbeddingMethod = None) -> None:
    """
    Create or update embeddings for configured provider.
    
    Args:
        force_recreate: Delete existing embeddings and recreate
        method: Override config method - 'traditional', 'augmented', or 'both'
    """
    print("\n" + "=" * 60, flush=True)
    print("EMBEDDING CREATION", flush=True)
    print("=" * 60, flush=True)
    
    # Load configuration
    print("Loading configuration...", flush=True)
    config = Config.from_yaml("wiki_embed/config.yaml")
    
    # Configure global settings (like DSPy)
    print("Configuring global settings...", flush=True)
    configure_from_config(config)
    
    provider_info = config.embedding.provider
    model_info = get_model_display_name(config)
    
    print(f"Provider: {provider_info}", flush=True)
    print(f"Model: {model_info}", flush=True)
    print(f"Vector Store: {config.vector_store.provider}", flush=True)
    
    if force_recreate:
        print("Mode: Force recreate (will delete existing)", flush=True)
    else:
        print("Mode: Normal (will reuse existing)", flush=True)
    print("=" * 60, flush=True)
    print(flush=True)
    
    # Create pipeline (now uses global settings)
    print("Initializing pipeline...", flush=True)
    pipeline = WikipediaEmbeddingPipeline(config)
    print("Pipeline ready", flush=True)
    print(flush=True)
    
    # Create embeddings
    count = pipeline.create_embeddings(force_recreate=force_recreate, method=method)
    
    print(flush=True)
    print("=" * 60, flush=True)
    print(f"✅ COMPLETE! {count} embeddings ready for {provider_info}", flush=True)
    print("=" * 60, flush=True)


def test_embeddings(method: EmbeddingMethod = None) -> ModelComparison:
    """
    Test Wikipedia embedding quality for configured provider.
    
    Args:
        method: Override config method - 'traditional' or 'augmented'
        
    Returns:
        ModelComparison with results
    """
    # Load configuration
    config = Config.from_yaml("wiki_embed/config.yaml")
    
    # Configure global settings (like DSPy)
    configure_from_config(config)
    
    provider_info = config.embedding.provider
    model_info = get_model_display_name(config)
    
    print(f"\n=== Testing Wikipedia Embeddings ===", flush=True)
    print(f"Provider: {provider_info}", flush=True)
    print(f"Model: {model_info}", flush=True)
    print(f"Vector Store: {config.vector_store.provider}", flush=True)
    print("=" * 50, flush=True)
    
    # Load test queries
    test_queries_file = Path(config.testing.queries_path)
    if not test_queries_file.exists():
        print(f"Error: Test queries file not found: {test_queries_file}")
        sys.exit(1)
    
    with open(test_queries_file) as f:
        data = json.load(f)
    
    # Use LocationQuery instead of TestQuery
    from wiki_embed.models import LocationQuery, QueryType
    test_queries = []
    for q in data["queries"]:
        # Convert query_type string to enum
        query_type = QueryType(q["query_type"]) if "query_type" in q else QueryType.GEOGRAPHIC
        test_queries.append(LocationQuery(
            query=q["query"],
            expected_articles=q["expected_articles"],
            location_context=q.get("location_context"),
            query_type=query_type,
            description=q.get("description")
        ))
    
    print(f"\nLoaded {len(test_queries)} location-based test queries", flush=True)
    
    # Create query tester (now uses global settings)
    tester = WikipediaQueryTester(config, method=method)
    
    # Run tests
    results = tester.test_queries(test_queries)
    
    # Determine which method was actually used
    actual_method = method or config.chunking.embedding_method
    
    # Create comparison object
    comparison = ModelComparison(
        model_name=f"{provider_info}_{model_info}",
        embedding_method=actual_method,
        avg_precision=0.0,
        avg_recall=0.0,
        avg_f1=0.0,
        total_queries=len(results),
        results=results
    )
    
    # Calculate averages (including by type)
    comparison.calculate_averages()
    
    # Print summary
    print(f"\n{'=' * 50}", flush=True)
    print(f"OVERALL RESULTS for {provider_info} ({model_info})", flush=True)
    print(f"{'=' * 50}", flush=True)
    print(f"Average Precision: {comparison.avg_precision:.3f}", flush=True)
    print(f"Average Recall:    {comparison.avg_recall:.3f}", flush=True)
    print(f"Average F1 Score:  {comparison.avg_f1:.3f}", flush=True)
    print(f"Total Queries:     {comparison.total_queries}", flush=True)
    
    # Print results by query type
    if comparison.results_by_type:
        print(f"\n--- Results by Query Type ---", flush=True)
        for query_type, metrics in comparison.results_by_type.items():
            print(f"\n{query_type.capitalize()}:", flush=True)
            print(f"  Precision: {metrics['avg_precision']:.3f}", flush=True)
            print(f"  Recall:    {metrics['avg_recall']:.3f}", flush=True)
            print(f"  F1 Score:  {metrics['avg_f1']:.3f}", flush=True)
            print(f"  Count:     {metrics['count']}", flush=True)
    
    # Save results to JSON
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    # Include method in filename
    method_suffix = f"_{actual_method.value}" if actual_method else ""
    results_file = results_dir / f"wiki_comparison_{model_info}{method_suffix}.json"
    
    with open(results_file, 'w') as f:
        json.dump(comparison.dict(), f, indent=2)
    print(f"\nResults saved to: {results_file}", flush=True)
    
    return comparison


def _write_evaluation_report(traditional: ModelComparison, augmented: ModelComparison) -> None:
    """
    Write evaluation report comparing traditional and augmented methods.
    
    Args:
        traditional: Results from traditional embedding method
        augmented: Results from augmented embedding method
    """
    report_path = Path("EVAL_RESULTS.md")
    
    with open(report_path, 'w') as f:
        f.write("# Embedding Method Evaluation Results\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Model**: {traditional.model_name}\n")
        f.write(f"**Total Queries**: {traditional.total_queries}\n\n")
        
        f.write("## Executive Summary\n\n")
        
        # Calculate improvements
        precision_imp = (augmented.avg_precision - traditional.avg_precision) * 100
        recall_imp = (augmented.avg_recall - traditional.avg_recall) * 100
        f1_imp = (augmented.avg_f1 - traditional.avg_f1) * 100
        
        if f1_imp > 0:
            f.write(f"The augmented embedding method shows a **{f1_imp:.1f}% improvement** in overall F1 score ")
            f.write(f"compared to the traditional method. This improvement is driven by better recall ")
            f.write(f"({recall_imp:+.1f}%) with minimal impact on precision ({precision_imp:+.1f}%).\n\n")
        else:
            f.write(f"The traditional embedding method performs **{-f1_imp:.1f}% better** in overall F1 score ")
            f.write(f"compared to the augmented method.\n\n")
        
        f.write("## Overall Performance Metrics\n\n")
        f.write("| Metric | Traditional | Augmented | Improvement |\n")
        f.write("|--------|------------|-----------|-------------|\n")
        f.write(f"| Precision | {traditional.avg_precision:.3f} | {augmented.avg_precision:.3f} | {precision_imp:+.1f}% |\n")
        f.write(f"| Recall | {traditional.avg_recall:.3f} | {augmented.avg_recall:.3f} | {recall_imp:+.1f}% |\n")
        f.write(f"| F1 Score | {traditional.avg_f1:.3f} | {augmented.avg_f1:.3f} | {f1_imp:+.1f}% |\n\n")
        
        f.write("## Performance by Query Type\n\n")
        
        if traditional.results_by_type and augmented.results_by_type:
            all_types = set(traditional.results_by_type.keys()) | set(augmented.results_by_type.keys())
            
            for query_type in sorted(all_types):
                f.write(f"### {query_type.title()}\n\n")
                
                trad = traditional.results_by_type.get(query_type, {})
                aug = augmented.results_by_type.get(query_type, {})
                
                if trad and aug:
                    f.write("| Metric | Traditional | Augmented | Improvement |\n")
                    f.write("|--------|------------|-----------|-------------|\n")
                    
                    p_imp = (aug['avg_precision'] - trad['avg_precision']) * 100
                    r_imp = (aug['avg_recall'] - trad['avg_recall']) * 100
                    f_imp = (aug['avg_f1'] - trad['avg_f1']) * 100
                    
                    f.write(f"| Precision | {trad['avg_precision']:.3f} | {aug['avg_precision']:.3f} | {p_imp:+.1f}% |\n")
                    f.write(f"| Recall | {trad['avg_recall']:.3f} | {aug['avg_recall']:.3f} | {r_imp:+.1f}% |\n")
                    f.write(f"| F1 Score | {trad['avg_f1']:.3f} | {aug['avg_f1']:.3f} | {f_imp:+.1f}% |\n")
                    f.write(f"| Query Count | {trad['count']} | {aug['count']} | - |\n\n")
        
        f.write("## Key Findings\n\n")
        
        # Identify best performing query types for each method
        if traditional.results_by_type and augmented.results_by_type:
            improvements = []
            for query_type in all_types:
                trad = traditional.results_by_type.get(query_type, {})
                aug = augmented.results_by_type.get(query_type, {})
                if trad and aug:
                    imp = (aug.get('avg_f1', 0) - trad.get('avg_f1', 0)) * 100
                    improvements.append((query_type, imp))
            
            improvements.sort(key=lambda x: x[1], reverse=True)
            
            f.write("### Query Types with Most Improvement (Augmented vs Traditional)\n\n")
            for i, (qtype, imp) in enumerate(improvements[:3], 1):
                if imp > 0:
                    f.write(f"{i}. **{qtype.title()}**: +{imp:.1f}% F1 improvement\n")
            
            f.write("\n### Query Types Where Traditional Performs Better\n\n")
            negative_improvements = [x for x in improvements if x[1] < 0]
            if negative_improvements:
                for i, (qtype, imp) in enumerate(negative_improvements[:3], 1):
                    f.write(f"{i}. **{qtype.title()}**: {imp:.1f}% F1 difference\n")
            else:
                f.write("None - augmented method performs better across all query types.\n")
        
        f.write("\n## Methodology\n\n")
        f.write("This evaluation compared two embedding methods:\n\n")
        f.write("1. **Traditional Method**: Standard semantic chunking without additional context\n")
        f.write("2. **Augmented Method**: Chunks prepended with article summaries and metadata\n\n")
        f.write("Each method was tested on the same set of queries covering various query types ")
        f.write("(geographic, landmark, historical, recreational, cultural, administrative).\n\n")
        
        f.write("## Recommendations\n\n")
        
        if f1_imp > 5:
            f.write("Based on these results, **the augmented embedding method is recommended** for this dataset. ")
            f.write("The summary context significantly improves retrieval, especially for broad queries.\n\n")
        elif f1_imp > 0:
            f.write("The augmented method shows modest improvements. Consider using it for applications ")
            f.write("where recall is more important than precision.\n\n")
        else:
            f.write("The traditional method currently performs better. Consider investigating why ")
            f.write("the augmented context is not improving results.\n\n")
        
        f.write("## Configuration Used\n\n")
        f.write("- **Embedding Model**: " + traditional.model_name.split('_')[1] + "\n")
        f.write("- **Chunking Method**: Semantic\n")
        f.write("- **Max Summary Words**: 100 (augmented only)\n")
        f.write("- **Max Total Words**: 500 (augmented only)\n")
    
    print(f"\n✓ Evaluation report saved to: {report_path}")


def compare_methods() -> None:
    """
    Compare traditional vs augmented embedding methods side-by-side.
    Runs both methods on the same queries and generates comparison report.
    """
    print("\n=== Comparative Evaluation: Traditional vs Augmented ===\n")
    
    # Load configuration
    config = Config.from_yaml("wiki_embed/config.yaml")
    
    # Configure global settings (like DSPy)
    configure_from_config(config)
    
    # Check if we have summaries for augmented method
    from wiki_embed.utils import load_summaries_from_db
    summaries = load_summaries_from_db(config.data.wikipedia_db)
    if not summaries:
        print("Error: No summaries found in database. Cannot run augmented method comparison.")
        print("Please ensure wikipedia.db contains page_summaries data.")
        return
    
    print(f"Found {len(summaries)} summaries for augmented embeddings\n")
    
    # Load test queries
    test_queries_file = Path(config.testing.queries_path)
    if not test_queries_file.exists():
        print(f"Error: Test queries file not found: {test_queries_file}")
        return
    
    with open(test_queries_file) as f:
        data = json.load(f)
    
    # Parse queries
    from wiki_embed.models import LocationQuery, QueryType
    test_queries = []
    for q in data["queries"]:
        query_type = QueryType(q["query_type"]) if "query_type" in q else QueryType.GEOGRAPHIC
        test_queries.append(LocationQuery(
            query=q["query"],
            expected_articles=q["expected_articles"],
            location_context=q.get("location_context"),
            query_type=query_type,
            description=q.get("description")
        ))
    
    print(f"Testing {len(test_queries)} queries on both methods\n")
    print("-" * 60)
    
    # Test traditional method
    print("\n1. Testing TRADITIONAL embeddings...")
    traditional_comparison = test_embeddings(method=EmbeddingMethod.TRADITIONAL)
    
    # Test augmented method
    print("\n2. Testing AUGMENTED embeddings...")
    augmented_comparison = test_embeddings(method=EmbeddingMethod.AUGMENTED)
    
    # Generate comparison report
    print("\n" + "=" * 60)
    print("SIDE-BY-SIDE COMPARISON RESULTS")
    print("=" * 60)
    
    # Overall metrics comparison
    print("\nOverall Performance:")
    print(f"{'Metric':<15} {'Traditional':>12} {'Augmented':>12} {'Improvement':>12}")
    print("-" * 51)
    
    precision_imp = (augmented_comparison.avg_precision - traditional_comparison.avg_precision) * 100
    recall_imp = (augmented_comparison.avg_recall - traditional_comparison.avg_recall) * 100
    f1_imp = (augmented_comparison.avg_f1 - traditional_comparison.avg_f1) * 100
    
    print(f"{'Precision':<15} {traditional_comparison.avg_precision:>12.3f} "
          f"{augmented_comparison.avg_precision:>12.3f} {precision_imp:>+11.1f}%")
    print(f"{'Recall':<15} {traditional_comparison.avg_recall:>12.3f} "
          f"{augmented_comparison.avg_recall:>12.3f} {recall_imp:>+11.1f}%")
    print(f"{'F1 Score':<15} {traditional_comparison.avg_f1:>12.3f} "
          f"{augmented_comparison.avg_f1:>12.3f} {f1_imp:>+11.1f}%")
    
    # Performance by query type
    if traditional_comparison.results_by_type and augmented_comparison.results_by_type:
        print("\n\nPerformance by Query Type:")
        
        all_types = set(traditional_comparison.results_by_type.keys()) | \
                   set(augmented_comparison.results_by_type.keys())
        
        for query_type in sorted(all_types):
            print(f"\n{query_type.upper()}:")
            print(f"{'Metric':<15} {'Traditional':>12} {'Augmented':>12} {'Improvement':>12}")
            print("-" * 51)
            
            trad_metrics = traditional_comparison.results_by_type.get(query_type, {})
            aug_metrics = augmented_comparison.results_by_type.get(query_type, {})
            
            if trad_metrics and aug_metrics:
                p_imp = (aug_metrics['avg_precision'] - trad_metrics['avg_precision']) * 100
                r_imp = (aug_metrics['avg_recall'] - trad_metrics['avg_recall']) * 100
                f_imp = (aug_metrics['avg_f1'] - trad_metrics['avg_f1']) * 100
                
                print(f"{'Precision':<15} {trad_metrics['avg_precision']:>12.3f} "
                      f"{aug_metrics['avg_precision']:>12.3f} {p_imp:>+11.1f}%")
                print(f"{'Recall':<15} {trad_metrics['avg_recall']:>12.3f} "
                      f"{aug_metrics['avg_recall']:>12.3f} {r_imp:>+11.1f}%")
                print(f"{'F1 Score':<15} {trad_metrics['avg_f1']:>12.3f} "
                      f"{aug_metrics['avg_f1']:>12.3f} {f_imp:>+11.1f}%")
                print(f"{'Query Count':<15} {trad_metrics['count']:>12} "
                      f"{aug_metrics['count']:>12} {'':>12}")
    
    # Summary findings
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if f1_imp > 0:
        print(f"✓ Augmented embeddings show {f1_imp:.1f}% improvement in F1 score")
    else:
        print(f"⚠ Traditional embeddings perform better by {-f1_imp:.1f}% in F1 score")
    
    # Identify which query types benefit most
    if traditional_comparison.results_by_type and augmented_comparison.results_by_type:
        improvements = []
        for query_type in all_types:
            trad = traditional_comparison.results_by_type.get(query_type, {})
            aug = augmented_comparison.results_by_type.get(query_type, {})
            if trad and aug:
                imp = (aug.get('avg_f1', 0) - trad.get('avg_f1', 0)) * 100
                improvements.append((query_type, imp))
        
        improvements.sort(key=lambda x: x[1], reverse=True)
        
        if improvements:
            print("\nQuery types with most improvement:")
            for qtype, imp in improvements[:3]:
                if imp > 0:
                    print(f"  • {qtype}: +{imp:.1f}%")
    
    print("\nComparative evaluation complete!")
    
    # Write evaluation report to file
    _write_evaluation_report(traditional_comparison, augmented_comparison)


def compare_providers() -> None:
    """Compare Wikipedia embedding models."""
    print("\n=== Wikipedia Embedding Model Comparison ===\n")
    
    # Load existing results
    results_dir = Path("results")
    if not results_dir.exists():
        print("No results found. Run 'test' command first for each model.")
        return
    
    # Find all wiki comparison files
    comparison_files = list(results_dir.glob("wiki_comparison_*.json"))
    
    if not comparison_files:
        print("No comparison results found.")
        print("\nTo generate results:")
        print("1. python -m wiki_embed.main create  # Create embeddings")
        print("2. python -m wiki_embed.main test    # Test embeddings")
        return
    
    # Load and display all results
    comparisons = []
    for file in comparison_files:
        with open(file) as f:
            data = json.load(f)
            comparisons.append(data)
    
    # Sort by F1 score
    comparisons.sort(key=lambda x: x['avg_f1'], reverse=True)
    
    print(f"Found {len(comparisons)} model results:\n")
    print("-" * 60)
    
    for i, comp in enumerate(comparisons, 1):
        model_name = comp['model_name']
        print(f"\n{i}. {model_name}")
        print(f"   Precision: {comp['avg_precision']:.3f}")
        print(f"   Recall:    {comp['avg_recall']:.3f}")
        print(f"   F1 Score:  {comp['avg_f1']:.3f}")
        print(f"   Queries:   {comp['total_queries']}")
    
    if comparisons:
        print("\n" + "=" * 60)
        print(f"🏆 WINNER: {comparisons[0]['model_name']}")
        print(f"   Best F1 Score: {comparisons[0]['avg_f1']:.3f}")
        print("=" * 60)
    
    print("\nTo test another model:")
    print("1. Update 'provider' in wiki_embed/config.yaml")
    print("2. Run: python -m wiki_embed.main create --force-recreate")
    print("3. Run: python -m wiki_embed.main test")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Wikipedia Embedding Pipeline - Compare embedding models for Wikipedia location data"
    )
    
    parser.add_argument(
        'command',
        choices=['create', 'test', 'compare', 'compare-methods'],
        help='Command to run (compare-methods: compare traditional vs augmented)'
    )
    
    parser.add_argument(
        '--force-recreate',
        action='store_true',
        help='Force recreate embeddings (delete existing)'
    )
    
    parser.add_argument(
        '--method',
        type=str,
        choices=['traditional', 'augmented', 'both'],
        help='Embedding method to use (overrides config)'
    )
    
    args = parser.parse_args()
    
    # Execute command
    if args.command == 'create':
        # Convert string to enum if provided
        method = EmbeddingMethod(args.method) if args.method else None
        create_embeddings(args.force_recreate, method=method)
        
    elif args.command == 'test':
        # Convert string to enum if provided
        method = EmbeddingMethod(args.method) if args.method else None
        test_embeddings(method=method)
        
    elif args.command == 'compare':
        compare_providers()
    
    elif args.command == 'compare-methods':
        compare_methods()


if __name__ == '__main__':
    main()