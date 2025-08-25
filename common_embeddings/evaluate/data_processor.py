#!/usr/bin/env python3
"""
Data processor for evaluation datasets.

Handles loading and processing evaluation JSON files into embeddings.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from ..models import Config, EntityType, SourceType
from ..models.eval_config import load_eval_config
from ..pipeline import EmbeddingPipeline
from ..utils import get_logger
from ..utils.progress import create_progress_indicator
from ..services import CollectionManager
from ..storage import ChromaDBStore
from llama_index.core import Document

logger = get_logger(__name__)


def process_eval_config(config_path: str, force_recreate: bool = False) -> Optional[Dict[str, Any]]:
    """
    Process evaluation data using a specific eval config file.
    
    Args:
        config_path: Path to eval config YAML file
        force_recreate: Whether to recreate collections
        
    Returns:
        Statistics dictionary or None if failed
    """
    logger.info(f"Processing evaluation data with config: {config_path}")
    
    # Load eval configuration
    config = load_eval_config(config_path)
    logger.info(f"Loaded eval config: provider={config.embedding.provider}, collection={config.chromadb.collection_name}")
    
    # Determine JSON path from config
    if hasattr(config, 'evaluation_data') and hasattr(config.evaluation_data, 'articles_path'):
        json_path = Path(config.evaluation_data.articles_path)
    else:
        json_path = Path("common_embeddings/evaluate_data/gold_articles.json")
    
    if not json_path.exists():
        logger.error(f"Evaluation JSON file not found: {json_path}")
        return None
    
    # Process the JSON articles
    return process_json_articles(config, json_path, force_recreate)


def process_json_articles(config: Config, json_path: Path, force_recreate: bool = False) -> Optional[Dict[str, Any]]:
    """
    Process Wikipedia articles from evaluation JSON file.
    
    Args:
        config: Configuration object
        json_path: Path to JSON file with articles
        force_recreate: Whether to recreate collections
        
    Returns:
        Statistics dictionary
    """
    logger.info(f"Processing articles from JSON: {json_path}")
    
    # Load articles from JSON
    with open(json_path) as f:
        data = json.load(f)
    
    if "articles" in data:
        articles = data["articles"]
    else:
        articles = data
    
    if not articles:
        logger.warning(f"No articles found in {json_path}")
        return None
        
    logger.info(f"Loaded {len(articles)} articles from JSON")
    
    # Convert to Document objects  
    documents = []
    for article in articles:
        content = article.get('long_summary', '')
        
        if not content or not content.strip():
            logger.warning(f"Skipping article with empty content: {article.get('title', 'Unknown')}")
            continue
            
        # Create document with metadata
        doc_metadata = {
            "page_id": article.get("page_id", 0),
            "article_id": article.get("article_id", 0), 
            "title": article.get("title", "Unknown"),
            "url": article.get("url", ""),
            "city": article.get("city", ""),
            "state": article.get("state", ""),
            "categories": ", ".join(article.get("categories", [])),
            "source": "evaluation_set",
            "source_file": article.get("html_file", "")
        }
        
        documents.append(Document(
            text=content, 
            metadata=doc_metadata
        ))
    
    logger.info(f"Created {len(documents)} documents from articles")
    
    # Initialize pipeline for embedding generation
    pipeline = EmbeddingPipeline(config)
    
    # Process documents with progress indicator
    logger.info(f"Processing {len(documents)} evaluation articles...")
    progress = create_progress_indicator(
        total=len(documents),
        operation="Processing evaluation articles",
        show_console=True
    )
    
    # Store in collection first
    logger.info("Setting up ChromaDB collection for evaluation...")
    collection_manager = CollectionManager(config)
    
    # Get collection name from config
    eval_collection = config.chromadb.collection_name
    logger.info(f"Using collection name: {eval_collection}")
    
    # Create the collection
    collection_manager.store.create_collection(
        name=eval_collection,
        metadata={
            "source": "evaluation_set",
            "json_path": str(json_path),
            "article_count": len(articles),
        },
        force_recreate=force_recreate
    )
    
    # Store using ChromaDB directly
    chroma_store = ChromaDBStore(config.chromadb)
    chroma_store.collection = chroma_store.client.get_collection(eval_collection)
    
    doc_count = 0
    embeddings_to_add = []
    
    for result in pipeline.process_documents(
        documents,
        EntityType.WIKIPEDIA_ARTICLE,
        SourceType.EVALUATION_JSON,
        str(json_path)
    ):
        # Collect embeddings to batch add
        # Convert Pydantic model to dict for ChromaDB
        metadata_dict = result.metadata.model_dump()
        
        doc_id = metadata_dict.get("page_id", f"doc_{doc_count}")
        
        embeddings_to_add.append({
            "embedding": result.embedding,
            "metadata": metadata_dict,
            "document_id": f"{doc_id}_{doc_count}"
        })
        
        doc_count += 1
        
        # Add to ChromaDB in batches
        if len(embeddings_to_add) >= config.processing.batch_size:
            # Extract just what ChromaDB needs
            ids = [item["document_id"] for item in embeddings_to_add]
            embeddings = [item["embedding"] for item in embeddings_to_add]
            metadatas = [item["metadata"] for item in embeddings_to_add]
            documents_texts = [documents[i % len(documents)].text[:1000] for i in range(len(embeddings_to_add))]
            
            chroma_store.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_texts
            )
            
            logger.info(f"Added batch of {len(embeddings_to_add)} embeddings to collection")
            embeddings_to_add.clear()
        
        progress.update(doc_count)
    
    # Add remaining embeddings
    if embeddings_to_add:
        ids = [item["document_id"] for item in embeddings_to_add]
        embeddings = [item["embedding"] for item in embeddings_to_add]
        metadatas = [item["metadata"] for item in embeddings_to_add]
        documents_texts = [documents[i % len(documents)].text[:1000] for i in range(len(embeddings_to_add))]
        
        chroma_store.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents_texts
        )
    
    progress.complete()
    logger.info(f"Completed processing and storing {doc_count} evaluation embeddings")
    logger.info(f"Created evaluation collection: {eval_collection}")
    
    # Get statistics
    stats = pipeline.get_statistics()
    logger.info("Pipeline Statistics:")
    stats_dict = stats.model_dump()
    for key, value in stats_dict.items():
        logger.info(f"  {key}: {value}")
    
    return {
        'collection_name': eval_collection,
        'embeddings_created': doc_count,
        'statistics': stats_dict
    }