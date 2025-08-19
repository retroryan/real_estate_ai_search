"""
Embedding pipeline for creating and storing embeddings using LlamaIndex and ChromaDB.
Direct API usage without unnecessary abstractions.
"""

from llama_index.core import Document
from llama_index.core.node_parser import SemanticSplitterNodeParser, SimpleNodeParser
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.embeddings.google import GeminiEmbedding
from llama_index.embeddings.voyageai import VoyageEmbedding
import chromadb
from pathlib import Path
import json
import time
from typing import List
from .models import Config


class EmbeddingPipeline:
    """Simple embedding pipeline using LlamaIndex semantic chunking."""
    
    def __init__(self, config: Config):
        """
        Initialize pipeline with config.
        
        Args:
            config: Validated configuration from Config model
        """
        self.config = config
        
        # Initialize embedding model based on provider
        if config.embedding.provider == "ollama":
            self.embed_model = OllamaEmbedding(
                model_name=config.embedding.ollama_model,
                base_url=config.embedding.ollama_base_url
            )
            self.model_identifier = config.embedding.ollama_model
        elif config.embedding.provider == "gemini":
            self.embed_model = GeminiEmbedding(
                api_key=config.embedding.gemini_api_key,
                model_name=config.embedding.gemini_model
            )
            self.model_identifier = "gemini_embedding"
        else:  # voyage
            self.embed_model = VoyageEmbedding(
                api_key=config.embedding.voyage_api_key,
                model_name=config.embedding.voyage_model
            )
            self.model_identifier = f"voyage_{config.embedding.voyage_model}"
        
        # Direct use of ChromaDB client
        self.client = chromadb.PersistentClient(path=config.chromadb.path)
    
    def create_embeddings(self, force_recreate: bool = False) -> int:
        """
        Create or reuse embeddings for the configured model.
        
        Args:
            force_recreate: Delete existing embeddings and recreate
            
        Returns:
            Number of embeddings created or existing
        """
        # Each model gets its own collection
        collection_name = f"{self.config.chromadb.collection_prefix}_{self.model_identifier}"
        
        # Handle force recreate
        if force_recreate:
            try:
                self.client.delete_collection(collection_name)
                print(f"Deleted existing collection: {collection_name}", flush=True)
            except Exception:
                pass  # Collection doesn't exist
        
        # Get or create collection with metadata
        collection = self.client.get_or_create_collection(
            collection_name,
            metadata={
                "provider": self.config.embedding.provider,
                "model": self.model_identifier,
                "created_by": "real_estate_embed"
            }
        )
        
        # Smart caching - check for existing embeddings
        existing_count = collection.count()
        if existing_count > 0 and not force_recreate:
            print(f"✓ Using existing {existing_count} embeddings for {self.model_identifier}", flush=True)
            return existing_count
        
        # Load documents and create chunks
        print(f"Loading documents from {self.config.data.source_dir}...", flush=True)
        documents = self._load_documents()
        print(f"Loaded {len(documents)} documents", flush=True)
        
        print(f"Creating semantic chunks...", flush=True)
        nodes = self._create_semantic_chunks(documents)
        print(f"Created {len(nodes)} chunks", flush=True)
        
        # Generate and store embeddings with progress indicator
        print(f"\n=== Starting Embedding Generation ===", flush=True)
        print(f"Provider: {self.config.embedding.provider}", flush=True)
        print(f"Model: {self.model_identifier}", flush=True)
        print(f"Total chunks to process: {len(nodes)}", flush=True)
        print("-" * 50, flush=True)
        
        start_time = time.time()
        total_api_time = 0
        
        for i, node in enumerate(nodes, 1):
            # Show progress for every embedding
            chunk_start = time.time()
            print(f"  [{i}/{len(nodes)}] Processing chunk {i}...", end="", flush=True)
            
            try:
                # Direct embedding generation
                api_start = time.time()
                embedding = self.embed_model.get_text_embedding(node.text)
                api_time = time.time() - api_start
                total_api_time += api_time
                
                # Store in ChromaDB with metadata
                collection.add(
                    ids=[node.node_id],
                    embeddings=[embedding],
                    documents=[node.text],
                    metadatas={
                        **node.metadata,
                        "model": self.model_identifier,
                        "chunk_index": i-1
                    }
                )
                
                chunk_time = time.time() - chunk_start
                print(f" ✓ ({chunk_time:.2f}s)", flush=True)
                
                # Show milestone progress with timing
                if i % 10 == 0:
                    elapsed = time.time() - start_time
                    avg_time = elapsed / i
                    remaining = avg_time * (len(nodes) - i)
                    print(f"  --- Milestone: {i}/{len(nodes)} completed ({i*100//len(nodes)}%) ---", flush=True)
                    print(f"      Elapsed: {elapsed:.1f}s | Est. remaining: {remaining:.1f}s", flush=True)
                    
            except Exception as e:
                print(f" ✗ Error: {str(e)[:100]}", flush=True)
                raise
        
        total_time = time.time() - start_time
        print("-" * 50, flush=True)
        print(f"✓ Successfully created {len(nodes)} embeddings", flush=True)
        print(f"  Total time: {total_time:.2f}s", flush=True)
        print(f"  API time: {total_api_time:.2f}s", flush=True)
        print(f"  Average per chunk: {total_time/len(nodes):.2f}s", flush=True)
        return len(nodes)
    
    def _load_documents(self) -> List[Document]:
        """
        Load real estate data as LlamaIndex documents.
        
        Returns:
            List of Document objects with text and metadata
        """
        data_dir = Path(self.config.data.source_dir)
        documents = []
        
        # Load all neighborhoods data files
        for neighborhoods_file in data_dir.glob("neighborhoods_*.json"):
            with open(neighborhoods_file, 'r') as f:
                neighborhoods = json.load(f)
                for n in neighborhoods:
                    # Create readable text from neighborhood data
                    text = f"{n['name']} neighborhood in {n['city']}, {n['state']}. "
                    text += f"Median price: ${n.get('median_home_price', 'N/A')}. "
                    
                    if 'description' in n:
                        text += n['description']
                    
                    if 'demographics' in n:
                        demo = n['demographics']
                        text += f" Population: {demo.get('population', 'N/A')}."
                        if 'median_age' in demo:
                            text += f" Median age: {demo['median_age']}."
                    
                    if 'amenities' in n:
                        text += f" Amenities: {', '.join(n['amenities'])}."
                    
                    # Create document with metadata
                    documents.append(Document(
                        text=text,
                        metadata={
                            "type": "neighborhood",
                            "id": n.get('neighborhood_id', n['name']),
                            "name": n['name'],
                            "city": n['city'],
                            "state": n['state']
                        }
                    ))
        
        # Load all properties data files
        for properties_file in data_dir.glob("properties_*.json"):
            with open(properties_file, 'r') as f:
                properties = json.load(f)
                for p in properties:
                    # Create readable text from property data
                    address = p.get('address', {})
                    text = f"{p.get('property_type', 'Property')} at "
                    text += f"{address.get('street', '')}, {address.get('city', '')}, {address.get('state', '')}. "
                    text += f"Price: ${p.get('price', 'N/A')}. "
                    text += f"{p.get('bedrooms', 0)} beds, {p.get('bathrooms', 0)} baths. "
                    text += f"{p.get('square_feet', 0)} sq ft. "
                    
                    if 'description' in p:
                        text += p['description']
                    
                    if 'features' in p:
                        text += f" Features: {', '.join(p['features'])}."
                    
                    # Create document with metadata
                    documents.append(Document(
                        text=text,
                        metadata={
                            "type": "property",
                            "id": p.get('listing_id', str(p.get('price', ''))),
                            "property_type": p.get('property_type', 'unknown'),
                            "neighborhood_id": p.get('neighborhood_id', ''),
                            "price": p.get('price', 0)
                        }
                    ))
        
        return documents
    
    def _create_semantic_chunks(self, documents: List[Document]) -> List:
        """
        Create chunks using configured method (simple or semantic).
        
        Args:
            documents: List of Document objects to chunk
            
        Returns:
            List of chunks (nodes)
        """
        if self.config.chunking.method == "simple":
            print(f"  Using simple chunking (size={self.config.chunking.chunk_size}, overlap={self.config.chunking.chunk_overlap})...", flush=True)
            # Use SimpleNodeParser for faster, more predictable chunking
            parser = SimpleNodeParser.from_defaults(
                chunk_size=self.config.chunking.chunk_size,
                chunk_overlap=self.config.chunking.chunk_overlap
            )
            print(f"  Processing {len(documents)} documents into chunks...", flush=True)
        else:  # semantic
            print(f"  Using semantic chunking (may be slow with Gemini)...", flush=True)
            print(f"  Initializing semantic parser...", flush=True)
            # Use SemanticSplitterNodeParser for semantic boundaries
            parser = SemanticSplitterNodeParser(
                embed_model=self.embed_model,
                breakpoint_percentile_threshold=self.config.chunking.breakpoint_percentile,
                buffer_size=self.config.chunking.buffer_size
            )
            print(f"  Processing {len(documents)} documents into chunks...", flush=True)
            print(f"  (This may take several minutes as it analyzes semantic boundaries)", flush=True)
        
        # Get nodes from documents
        nodes = parser.get_nodes_from_documents(documents)
        
        print(f"  Chunking complete!", flush=True)
        
        return nodes