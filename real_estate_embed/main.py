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

from .models import Config, TestQuery, ModelComparison
from .pipeline import EmbeddingPipeline
from .query import QueryTester


def create_embeddings(force_recreate: bool = False) -> None:
    """
    Create or update embeddings for configured provider.
    
    Args:
        force_recreate: Delete existing embeddings and recreate
    """
    print("\n" + "=" * 60, flush=True)
    print("EMBEDDING CREATION", flush=True)
    print("=" * 60, flush=True)
    
    # Load configuration
    print("Loading configuration...", flush=True)
    config_path = Path(__file__).parent / "config.yaml"
    config = Config.from_yaml(str(config_path))
    
    provider_info = config.embedding.provider
    if provider_info == "ollama":
        model_info = config.embedding.ollama_model
    elif provider_info == "gemini":
        model_info = "gemini_embedding"
    else:  # voyage
        model_info = f"voyage_{config.embedding.voyage_model}"
    
    print(f"Provider: {provider_info}", flush=True)
    print(f"Model: {model_info}", flush=True)
    
    if force_recreate:
        print("Mode: Force recreate (will delete existing)", flush=True)
    else:
        print("Mode: Normal (will reuse existing)", flush=True)
    print("=" * 60, flush=True)
    print(flush=True)
    
    # Create pipeline
    print("Initializing pipeline...", flush=True)
    pipeline = EmbeddingPipeline(config)
    print("Pipeline ready", flush=True)
    print(flush=True)
    
    # Create embeddings
    count = pipeline.create_embeddings(force_recreate=force_recreate)
    
    print(flush=True)
    print("=" * 60, flush=True)
    print(f"✅ COMPLETE! {count} embeddings ready for {provider_info}", flush=True)
    print("=" * 60, flush=True)


def test_embeddings() -> ModelComparison:
    """
    Test embedding quality for configured provider.
        
    Returns:
        ModelComparison with results
    """
    # Load configuration
    config_path = Path(__file__).parent / "config.yaml"
    config = Config.from_yaml(str(config_path))
    
    provider_info = config.embedding.provider
    if provider_info == "ollama":
        model_info = config.embedding.ollama_model
    elif provider_info == "gemini":
        model_info = "gemini_embedding"
    else:  # voyage
        model_info = f"voyage_{config.embedding.voyage_model}"
    
    print(f"\n=== Testing {provider_info} ({model_info}) ===\n")
    
    # Load test queries
    test_queries_file = Path("data/test_queries.json")
    if not test_queries_file.exists():
        print(f"Error: Test queries file not found: {test_queries_file}")
        sys.exit(1)
    
    with open(test_queries_file) as f:
        data = json.load(f)
    
    test_queries = [TestQuery(**q) for q in data["queries"]]
    
    # Create query tester
    tester = QueryTester(config)
    
    # Run tests
    results = tester.test_queries(test_queries)
    
    # Create comparison object
    comparison = ModelComparison(
        model_name=f"{provider_info}_{model_info}",
        avg_precision=0.0,
        avg_recall=0.0,
        avg_f1=0.0,
        total_queries=len(results),
        results=results
    )
    
    # Calculate averages
    comparison.calculate_averages()
    
    # Print summary
    print(f"\n--- Results for {provider_info} ({model_info}) ---")
    print(f"Average Precision: {comparison.avg_precision:.3f}")
    print(f"Average Recall:    {comparison.avg_recall:.3f}")
    print(f"Average F1 Score:  {comparison.avg_f1:.3f}")
    print(f"Total Queries:     {comparison.total_queries}")
    
    return comparison


def compare_providers(collections_to_compare: List[str] = None) -> None:
    """Compare different embedding models/providers that have been created.
    
    Args:
        collections_to_compare: Optional list of collection names to compare.
                              If None, will auto-detect all available collections.
    """
    print("\n" + "=" * 60)
    print("MODEL COMPARISON")
    print("=" * 60)
    
    # Load configuration
    config_path = Path(__file__).parent / "config.yaml"
    config = Config.from_yaml(str(config_path))
    
    # Load test queries
    test_queries_path = Path(__file__).parent.parent / "data" / "test_queries.json"
    with open(test_queries_path) as f:
        data = json.load(f)
    test_queries = [TestQuery(**q) for q in data["queries"]]
    
    # Get available collections
    import chromadb
    client = chromadb.PersistentClient(path=config.chromadb.path)
    all_collections = [c.name for c in client.list_collections()]
    
    # Filter to embedding collections only
    embedding_collections = [c for c in all_collections if c.startswith(config.chromadb.collection_prefix)]
    
    if not embedding_collections:
        print("\n⚠️  No embedding collections found in ChromaDB.")
        print("Create embeddings first using: python -m real_estate_embed.main create")
        return
    
    print(f"\nAvailable collections: {', '.join(embedding_collections)}")
    
    # Use specified collections or all available
    if collections_to_compare:
        collections = [c for c in collections_to_compare if c in embedding_collections]
        if not collections:
            print(f"\n⚠️  None of the specified collections exist: {collections_to_compare}")
            return
    else:
        collections = embedding_collections
    
    print(f"Comparing: {', '.join(collections)}")
    
    results = {}
    
    # Test each collection
    for collection_name in collections:
        # Extract model info from collection name
        model_info = collection_name.replace(f"{config.chromadb.collection_prefix}_", "")
        print(f"\n--- Testing {model_info} ---")
        
        try:
            collection = client.get_collection(collection_name)
            doc_count = collection.count()
            
            # Try to get provider/model from collection metadata
            collection_metadata = collection.metadata
            if collection_metadata:
                print(f"Found {doc_count} embeddings (provider: {collection_metadata.get('provider', 'unknown')}, model: {collection_metadata.get('model', model_info)})")
            else:
                print(f"Found {doc_count} embeddings in {collection_name}")
            
            # Determine provider and model from collection metadata or name
            original_provider = config.embedding.provider
            original_ollama_model = config.embedding.ollama_model
            
            # Use metadata from collection (collections without metadata need to be recreated)
            if not collection_metadata or "provider" not in collection_metadata:
                print(f"⚠️  Collection {collection_name} lacks metadata. Please recreate with --force-recreate")
                continue
                
            config.embedding.provider = collection_metadata["provider"]
            if collection_metadata["provider"] == "ollama":
                config.embedding.ollama_model = collection_metadata.get("model", model_info)
            elif collection_metadata["provider"] == "voyage":
                # Extract voyage model from metadata
                voyage_model = collection_metadata.get("model", model_info)
                if voyage_model.startswith("voyage_"):
                    config.embedding.voyage_model = voyage_model.replace("voyage_", "")
            
            # Run tests
            tester = QueryTester(config)
            test_results = tester.test_queries(test_queries)
            
            # Create comparison object
            comparison = ModelComparison(
                model_name=model_info,
                avg_precision=0.0,
                avg_recall=0.0,
                avg_f1=0.0,
                total_queries=len(test_results),
                results=test_results
            )
            comparison.calculate_averages()
            
            results[model_info] = comparison
            
            # Restore original config
            config.embedding.provider = original_provider
            config.embedding.ollama_model = original_ollama_model
            
        except Exception as e:
            print(f"⚠️  Error testing {collection_name}: {str(e)}")
            continue
    
    # Display comparison results
    if len(results) > 1:
        print("\n" + "=" * 60)
        print("FINAL COMPARISON")
        print("=" * 60)
        
        for model_name, comparison in results.items():
            print(f"\n{model_name}:")
            print(f"  Precision: {comparison.avg_precision:.3f}")
            print(f"  Recall:    {comparison.avg_recall:.3f}")
            print(f"  F1 Score:  {comparison.avg_f1:.3f}")
        
        # Determine winner
        winner = max(results.items(), key=lambda x: x[1].avg_f1)
        print(f"\n🏆 Winner: {winner[0]} (F1: {winner[1].avg_f1:.3f})")
        
        # Save results to JSON
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)
        
        output_file = results_dir / "comparison.json"
        output_data = {
            model_name: {
                "precision": comp.avg_precision,
                "recall": comp.avg_recall,
                "f1_score": comp.avg_f1,
                "total_queries": comp.total_queries
            }
            for model_name, comp in results.items()
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
        
    elif len(results) == 1:
        model_name, comparison = list(results.items())[0]
        print(f"\n--- Results for {model_name} ---")
        print(f"Average Precision: {comparison.avg_precision:.3f}")
        print(f"Average Recall:    {comparison.avg_recall:.3f}")
        print(f"Average F1 Score:  {comparison.avg_f1:.3f}")
        print("\n⚠️  Need at least 2 models to compare.")
    else:
        print("\n⚠️  No valid collections could be tested.")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Embedding Pipeline - Compare embedding models for real estate data"
    )
    
    parser.add_argument(
        'command',
        choices=['create', 'test', 'compare'],
        help='Command to run'
    )
    
    parser.add_argument(
        '--force-recreate',
        action='store_true',
        help='Force recreate embeddings (delete existing)'
    )
    
    parser.add_argument(
        '--collections',
        nargs='+',
        help='Specific collections to compare (e.g., embeddings_nomic-embed-text embeddings_gemini_embedding)'
    )
    
    args = parser.parse_args()
    
    # Execute command
    if args.command == 'create':
        create_embeddings(args.force_recreate)
        
    elif args.command == 'test':
        test_embeddings()
        
    elif args.command == 'compare':
        compare_providers(args.collections if hasattr(args, 'collections') else None)


if __name__ == '__main__':
    main()