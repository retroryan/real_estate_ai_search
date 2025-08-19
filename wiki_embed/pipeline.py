"""
Wikipedia embedding pipeline using LlamaIndex and configurable vector stores.
Focused on location-based Wikipedia content with semantic chunking.
"""

from llama_index.core import Document
from llama_index.core.node_parser import SemanticSplitterNodeParser, SimpleNodeParser
from pathlib import Path
import time
from typing import List
from wiki_embed.models import Config, WikiArticle, PageSummary, EmbeddingProvider, EmbeddingMethod, ChunkingMethod
from wiki_embed.utils import load_wikipedia_articles, create_location_context, load_summaries_from_db, get_summary_for_article, build_summary_context, settings
from wiki_embed.embedding import create_embedding_model


class WikipediaEmbeddingPipeline:
    """Embedding pipeline for Wikipedia location content."""
    
    def __init__(self, config: Config):
        """
        Initialize pipeline with configuration.
        
        Args:
            config: Validated configuration from Config model
        """
        self.config = config
        
        # Load summaries from database if available
        self.summaries = load_summaries_from_db(config.data.wikipedia_db)
        self.has_summaries = len(self.summaries) > 0
        
        # Initialize embedding model using factory
        self.embed_model, self.model_identifier = create_embedding_model(config)
        
        # Use global vector store (configured via settings)
        self.vector_store = settings.vector_store
        if not self.vector_store:
            raise RuntimeError("No vector store configured. Call wiki_embed.configure_from_config(config) first.")
    
    def create_embeddings(self, force_recreate: bool = False, method: EmbeddingMethod = None) -> int:
        """
        Create embeddings for Wikipedia articles.
        
        Args:
            force_recreate: Delete existing embeddings and recreate
            method: Override config method - 'traditional', 'augmented', or 'both'
            
        Returns:
            Number of embeddings created or existing
        """
        # Determine which method(s) to use
        embedding_method = method or self.config.chunking.embedding_method
        
        if embedding_method == EmbeddingMethod.BOTH:
            # Create both types of embeddings
            total = 0
            total += self._create_embeddings_for_method(EmbeddingMethod.TRADITIONAL, force_recreate)
            if self.has_summaries:
                total += self._create_embeddings_for_method(EmbeddingMethod.AUGMENTED, force_recreate)
            else:
                print("Warning: No summaries found, skipping augmented embeddings")
            return total
        else:
            # Create single type
            if embedding_method == EmbeddingMethod.AUGMENTED and not self.has_summaries:
                print("Warning: No summaries found, falling back to traditional embeddings")
                embedding_method = EmbeddingMethod.TRADITIONAL
            return self._create_embeddings_for_method(embedding_method, force_recreate)
    
    def _create_embeddings_for_method(self, method: EmbeddingMethod, force_recreate: bool) -> int:
        """
        Create embeddings for a specific method.
        
        Args:
            method: 'traditional' or 'augmented'
            force_recreate: Delete existing embeddings and recreate
            
        Returns:
            Number of embeddings created
        """
        # Generate collection/index name based on provider
        provider = settings.config.vector_store.provider.value
        if provider == "elasticsearch":
            prefix = settings.config.vector_store.elasticsearch.index_prefix
        else:
            prefix = settings.config.vector_store.chromadb.collection_prefix
        
        collection_name = f"{prefix}_{self.model_identifier}_{method.value}"
        
        # Create collection/index metadata
        collection_metadata = {
            "provider": self.config.embedding.provider.value,
            "model": self.model_identifier,
            "method": method.value,
            "created_by": "wiki_embed",
            "chunk_method": self.config.chunking.method.value,
            "chunk_size": str(self.config.chunking.chunk_size)
        }
        
        # Add augmented-specific metadata if applicable
        if method == EmbeddingMethod.AUGMENTED:
            collection_metadata["max_summary_words"] = str(self.config.chunking.max_summary_words)
        
        # Create collection/index
        self.vector_store.create_collection(collection_name, collection_metadata, force_recreate)
        
        # Check for existing embeddings (caching)
        existing_count = self.vector_store.count()
        if existing_count > 0 and not force_recreate:
            print(f"✓ Using existing {existing_count} embeddings for {self.model_identifier}", flush=True)
            return existing_count
        
        print(f"\n=== Creating {method.value.capitalize()} Embeddings ===", flush=True)
        
        # Load Wikipedia articles
        print(f"Loading Wikipedia Articles...", flush=True)
        print(f"Source: {self.config.data.source_dir}", flush=True)
        
        # Check for max_articles setting in config
        max_articles = getattr(self.config.data, 'max_articles', None)
        
        articles = load_wikipedia_articles(
            self.config.data.source_dir,
            self.config.data.registry_path,
            max_articles=max_articles
        )
        
        if not articles:
            print("No Wikipedia articles found!", flush=True)
            return 0
        
        # Attach summary data to articles if using augmented method
        if method == EmbeddingMethod.AUGMENTED:
            for article in articles:
                summary = get_summary_for_article(article.page_id, self.summaries)
                article.summary_data = summary
        
        # Convert to LlamaIndex documents based on method
        print(f"\nProcessing {len(articles)} articles...", flush=True)
        
        if method == EmbeddingMethod.TRADITIONAL:
            documents = self._articles_to_documents(articles)
        elif method == EmbeddingMethod.AUGMENTED:
            documents = self._articles_to_augmented_documents(articles)
        else:
            raise ValueError(f"Invalid embedding method for processing: {method}")
        
        # Create chunks
        print(f"\nCreating chunks (chunking method: {self.config.chunking.method})...", flush=True)
        nodes = self._create_chunks(documents)
        
        # Optionally split oversized chunks
        if self.config.chunking.split_oversized_chunks:
            nodes = self._split_oversized_chunks(nodes)
        
        print(f"Created {len(nodes)} chunks from {len(articles)} articles", flush=True)
        
        # Log chunk size statistics
        if nodes:
            chunk_sizes = [len(node.text.split()) for node in nodes]
            avg_size = sum(chunk_sizes) / len(chunk_sizes)
            max_size = max(chunk_sizes)
            min_size = min(chunk_sizes)
            
            print(f"\nChunk size statistics (words):", flush=True)
            print(f"  Average: {avg_size:.0f} words", flush=True)
            print(f"  Maximum: {max_size} words", flush=True)
            print(f"  Minimum: {min_size} words", flush=True)
            
            # Check against limits
            target_max = getattr(self.config.chunking, 'max_total_words', 500)
            over_limit = sum(1 for size in chunk_sizes if size > target_max)
            
            if over_limit > 0:
                print(f"\n  ⚠️  {over_limit}/{len(nodes)} chunks exceed {target_max} words", flush=True)
                
                # Provide guidance based on method
                if method == EmbeddingMethod.AUGMENTED:
                    print(f"  Note: Large chunks in augmented mode include ~100 word summaries", flush=True)
                    actual_content_max = max_size - 100  # Approximate content without summary
                    if actual_content_max > 400:
                        print(f"  Consider: Reducing chunk_size in config (currently {self.config.chunking.chunk_size})", flush=True)
                else:
                    print(f"  Note: Semantic chunking preserves topic coherence", flush=True)
                    print(f"  Large chunks may indicate comprehensive topic sections", flush=True)
                    if over_limit > len(nodes) * 0.3:  # More than 30% over limit
                        print(f"  Consider: Lowering breakpoint_percentile (currently {self.config.chunking.breakpoint_percentile})", flush=True)
        
        # Generate and store embeddings
        self._generate_and_store_embeddings(nodes, method)
        
        return len(nodes)
    
    def _generate_and_store_embeddings(self, nodes: List, method: EmbeddingMethod) -> None:
        """
        Generate embeddings and store them in vector store.
        
        Args:
            nodes: List of document nodes to embed
            method: Embedding method being used
        """
        print(f"\n=== Generating Embeddings ===", flush=True)
        print(f"Provider: {self.config.embedding.provider}", flush=True)
        print(f"Model: {self.model_identifier}", flush=True)
        print(f"Total chunks: {len(nodes)}", flush=True)
        print("-" * 50, flush=True)
        
        start_time = time.time()
        
        # Collect all embeddings for batch processing
        embeddings = []
        texts = []
        metadatas = []
        ids = []
        
        for i, node in enumerate(nodes, 1):
            # Progress indicator
            if i % 5 == 1 or i == len(nodes):
                print(f"  Processing chunk {i}/{len(nodes)} ({i*100//len(nodes)}%)...", flush=True)
            
            try:
                # Generate embedding
                embedding = self.embed_model.get_text_embedding(node.text)
                
                # Collect for batch storage
                embeddings.append(embedding)
                texts.append(node.text)
                ids.append(node.node_id)
                metadatas.append({
                    **node.metadata,
                    "provider": self.config.embedding.provider.value,
                    "model": self.model_identifier,
                    "chunk_index": i-1,
                    "embedding_method": method.value
                })
                
            except Exception as e:
                print(f"  Error processing chunk {i}: {str(e)[:100]}", flush=True)
                raise
        
        # Batch store all embeddings
        print(f"  Storing {len(embeddings)} embeddings...", flush=True)
        self.vector_store.add_embeddings(embeddings, texts, metadatas, ids)
        
        total_time = time.time() - start_time
        print("-" * 50, flush=True)
        print(f"✓ Successfully created {len(nodes)} embeddings", flush=True)
        print(f"  Total time: {total_time:.2f}s", flush=True)
        print(f"  Average per chunk: {total_time/len(nodes):.2f}s", flush=True)
    
    def _articles_to_documents(self, articles: List[WikiArticle]) -> List[Document]:
        """
        Convert WikiArticle objects to LlamaIndex Documents.
        
        Args:
            articles: List of WikiArticle objects
            
        Returns:
            List of Document objects with metadata
        """
        documents = []
        
        for article in articles:
            # Create location context string
            location_context = create_location_context(article)
            
            # Combine title and content for better context
            full_text = f"{article.title}\n\n{article.content}"
            
            # Create document with rich metadata
            doc = Document(
                text=full_text,
                metadata={
                    "page_id": article.page_id,
                    "title": article.title,
                    "location": article.location or "Unknown",
                    "state": article.state or "Unknown",
                    "country": article.country or "Unknown",
                    "location_context": location_context,
                    "categories": ", ".join(article.categories[:5]) if article.categories else "",
                    "word_count": article.word_count,
                    "url": article.url or ""
                }
            )
            documents.append(doc)
        
        return documents
    
    def _articles_to_augmented_documents(self, articles: List[WikiArticle]) -> List[Document]:
        """
        Convert WikiArticle objects to LlamaIndex Documents with summary augmentation.
        
        Args:
            articles: List of WikiArticle objects with summary_data attached
            
        Returns:
            List of Document objects with augmented text and enhanced metadata
        """
        documents = []
        
        # Get max summary words from config or use default
        max_summary_words = getattr(self.config.chunking, 'max_summary_words', 100)
        
        for article in articles:
            # Get summary context if available (with word limit)
            summary_context = ""
            if article.summary_data:
                summary_context = build_summary_context(
                    article.summary_data, 
                    article.title,
                    max_words=max_summary_words
                )
            
            # Create location context string
            location_context = create_location_context(article)
            
            # For augmented method, prepend summary context to content
            # This ensures every chunk will have the summary
            if summary_context:
                full_text = f"{summary_context}\n\n{article.title}\n\n{article.content}"
            else:
                # Fallback to traditional if no summary
                full_text = f"{article.title}\n\n{article.content}"
            
            # Create document with enhanced metadata from summaries
            metadata = {
                "page_id": article.page_id,
                "title": article.title,
                "location": article.location or "Unknown",
                "state": article.state or "Unknown",
                "country": article.country or "Unknown",
                "location_context": location_context,
                "categories": ", ".join(article.categories[:5]) if article.categories else "",
                "word_count": article.word_count,
                "url": article.url or "",
                "has_summary": article.summary_data is not None
            }
            
            # Add enhanced metadata from summary if available
            if article.summary_data:
                metadata.update({
                    "summary": article.summary_data.summary,
                    "key_topics": ", ".join(article.summary_data.key_topics[:5]),
                    "best_city": article.summary_data.best_city or "",
                    "best_county": article.summary_data.best_county or "",
                    "best_state": article.summary_data.best_state or "",
                    "confidence": article.summary_data.overall_confidence
                })
            
            doc = Document(text=full_text, metadata=metadata)
            documents.append(doc)
        
        return documents
    
    def _create_chunks(self, documents: List[Document]) -> List:
        """
        Create chunks using configured method.
        
        Args:
            documents: List of Document objects
            
        Returns:
            List of chunks (nodes) with metadata preserved
        """
        if self.config.chunking.method == ChunkingMethod.SIMPLE:
            print(f"  Using simple chunking (size={self.config.chunking.chunk_size})", flush=True)
            parser = SimpleNodeParser.from_defaults(
                chunk_size=self.config.chunking.chunk_size,
                chunk_overlap=self.config.chunking.chunk_overlap
            )
            # Process all documents at once for simple chunking
            nodes = parser.get_nodes_from_documents(documents)
            
        elif self.config.chunking.method == ChunkingMethod.SEMANTIC:
            print(f"  Using semantic chunking (better for encyclopedia content)", flush=True)
            print(f"  Breakpoint percentile: {self.config.chunking.breakpoint_percentile}", flush=True)
            print(f"  Buffer size: {self.config.chunking.buffer_size}", flush=True)
            parser = SemanticSplitterNodeParser(
                embed_model=self.embed_model,
                breakpoint_percentile_threshold=self.config.chunking.breakpoint_percentile,
                buffer_size=self.config.chunking.buffer_size
            )
            print(f"  Analyzing semantic boundaries for {len(documents)} documents...", flush=True)
            
            # Process documents with progress updates for semantic chunking
            nodes = []
            for i, doc in enumerate(documents, 1):
                if i % 10 == 0 or i == 1 or i == len(documents):
                    print(f"    Processing document {i}/{len(documents)} ({i*100//len(documents)}%)...", flush=True)
                
                # Process single document to show progress
                doc_nodes = parser.get_nodes_from_documents([doc])
                nodes.extend(doc_nodes)
                
                # Show warning if this document created very large chunks
                if doc_nodes:
                    max_chunk_words = max(len(node.text.split()) for node in doc_nodes)
                    if max_chunk_words > self.config.chunking.max_total_words:
                        doc_title = doc.metadata.get('title', f'Document {i}')
                        print(f"    ⚠️  {doc_title}: largest chunk = {max_chunk_words} words", flush=True)
            
            print(f"  ✓ Semantic analysis complete", flush=True)
        else:
            raise ValueError(f"Unknown chunking method: {self.config.chunking.method}")
        
        return nodes
    
    def _split_oversized_chunks(self, nodes: List) -> List:
        """
        Split chunks that exceed max_total_words into smaller chunks.
        
        Args:
            nodes: List of nodes/chunks
            
        Returns:
            List of nodes with oversized ones split
        """
        max_words = self.config.chunking.max_total_words
        new_nodes = []
        split_count = 0
        
        for node in nodes:
            words = node.text.split()
            word_count = len(words)
            
            if word_count <= max_words:
                new_nodes.append(node)
            else:
                # Split oversized chunk
                split_count += 1
                num_splits = (word_count + max_words - 1) // max_words  # Ceiling division
                
                for i in range(num_splits):
                    start_idx = i * max_words
                    end_idx = min((i + 1) * max_words, word_count)
                    chunk_text = ' '.join(words[start_idx:end_idx])
                    
                    # Create new node with same metadata but updated text
                    from llama_index.core.schema import TextNode
                    new_node = TextNode(
                        text=chunk_text,
                        metadata={**node.metadata, 'split_index': i},
                        id_=f"{node.node_id}_split_{i}"
                    )
                    new_nodes.append(new_node)
        
        if split_count > 0:
            print(f"  Split {split_count} oversized chunks into {len(new_nodes) - len(nodes) + split_count} smaller chunks", flush=True)
        
        return new_nodes


# Keep compatibility with existing code
EmbeddingPipeline = WikipediaEmbeddingPipeline