# Vector Embeddings for Graph-Real-Estate

## Executive Summary

This proposal outlines a comprehensive approach to add vector embeddings to the graph-real-estate module, enabling semantic search and similarity matching capabilities. By combining Neo4j's native vector indexes with LlamaIndex's embedding pipeline, we create a powerful hybrid system that leverages both graph relationships and semantic understanding.

## Architecture Overview

### Core Components

1. **Embedding Pipeline** (LlamaIndex-based)
   - Multiple provider support (Ollama, OpenAI, Gemini)
   - Configurable chunking strategies
   - Batch processing with progress tracking

2. **Neo4j Vector Index**
   - Native vector similarity search
   - Cosine/Euclidean similarity functions
   - Integrated with existing graph structure

3. **Hybrid Search**
   - Combine vector similarity with graph traversal
   - Multi-modal search (text + relationships)
   - Contextual ranking using graph metrics

## Implementation Design

### 1. Vector Index Architecture

The PropertyVectorManager class handles Neo4j vector index operations:
- Creates and manages vector indexes with configurable dimensions
- Supports cosine and euclidean similarity functions
- Provides vector search with Neo4j's native ANN capabilities
- Manages embedding storage and retrieval for properties

### 2. Embedding Pipeline with LlamaIndex

The PropertyEmbeddingPipeline class provides:
- Multi-provider support (Ollama, OpenAI, Gemini) following wiki_embed patterns
- Rich property text generation combining attributes, features, and descriptions
- Batch processing with tqdm progress tracking
- Error handling and retry logic from wiki_embed
- Automatic dimension detection based on model

### 3. Hybrid Search Implementation

The HybridPropertySearch class provides:
- Vector search using Neo4j's native ANN capabilities
- Graph metrics calculation (centrality, connections, features)
- Combined scoring algorithm (60% vector, 20% graph, 20% features)
- Advanced filtering by price, location, and property details
- Similar property discovery through graph relationships
- Contextual boosting for well-connected properties

### 4. Integration with Graph Builder

```python
# src/controllers/graph_builder.py (additions)

def create_vector_embeddings(self) -> bool:
    """Create vector embeddings for all properties (Phase 5)."""
    print("\n" + "="*60)
    print("VECTOR EMBEDDING GENERATION")
    print("="*60)
    
    # Initialize embedding pipeline
    config = EmbeddingConfig(
        provider="ollama",
        model_name="nomic-embed-text",
        base_url="http://localhost:11434"
    )
    pipeline = PropertyEmbeddingPipeline(config)
    
    # Process all properties
    print(f"Generating embeddings for {len(self.data['all'])} properties...")
    stats = pipeline.process_properties(self.data['all'])
    
    print(f"\n✓ Embedding Generation Complete:")
    print(f"  - Processed: {stats['processed']}")
    print(f"  - Errors: {stats['errors']}")
    print(f"  - Time: {stats['time']:.2f}s")
    print(f"  - Rate: {stats['rate']:.1f} properties/second")
    
    return stats['errors'] == 0

def semantic_search_demo(self) -> None:
    """Demonstrate semantic search capabilities."""
    print("\n" + "="*60)
    print("SEMANTIC SEARCH DEMONSTRATION")
    print("="*60)
    
    # Initialize search
    config = EmbeddingConfig(provider="ollama", model_name="nomic-embed-text")
    pipeline = PropertyEmbeddingPipeline(config)
    search = HybridPropertySearch(self.driver, pipeline)
    
    # Demo queries
    queries = [
        "Modern condo with mountain views near ski slopes",
        "Family home with good schools and parks nearby",
        "Luxury property with smart home features",
        "Affordable starter home for young professionals"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        print("-" * 40)
        
        results = search.search(query, top_k=3)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.address}")
            print(f"   Price: ${result.price:,.0f}")
            print(f"   Neighborhood: {result.neighborhood}, {result.city}")
            print(f"   Vector Score: {result.vector_score:.3f}")
            print(f"   Graph Score: {result.graph_score:.3f}")
            print(f"   Combined Score: {result.combined_score:.3f}")
            if result.features[:3]:
                print(f"   Top Features: {', '.join(result.features[:3])}")
```

### 5. Configuration System

```yaml
# config/vectors.yaml
embedding:
  provider: ollama  # Options: ollama, openai, gemini
  model_name: nomic-embed-text  # or mxbai-embed-large, text-embedding-3-small
  base_url: http://localhost:11434
  
vector_index:
  index_name: property_embeddings
  vector_dimensions: 768  # Automatically set based on model
  similarity_function: cosine  # or euclidean
  
search:
  default_top_k: 10
  use_graph_boost: true
  score_weights:
    vector: 0.6
    graph: 0.2
    features: 0.2
    
chunking:
  method: simple  # For property descriptions
  max_length: 500  # Maximum text length for embedding
  include_features: true
  include_neighborhood_context: true
```

## Advanced Features

### 1. Multi-Modal Embeddings

Combine text with structured data for richer embeddings:

```python
class MultiModalPropertyEmbedding:
    """Create embeddings that combine text and numerical features."""
    
    def create_hybrid_embedding(self, property: Property) -> np.ndarray:
        # Text embedding (768 dims)
        text_embedding = self.get_text_embedding(property)
        
        # Numerical features (normalized)
        numerical_features = np.array([
            property.listing_price / 1_000_000,  # Normalize price
            property.get_bedrooms() / 10,
            property.get_bathrooms() / 5,
            property.get_square_feet() / 10_000,
            property.year_built / 2024 if property.year_built else 0.5
        ])
        
        # Concatenate for hybrid embedding
        hybrid = np.concatenate([text_embedding, numerical_features])
        return hybrid
```

### 2. Contextual Reranking

Use graph context to rerank search results:

```python
class ContextualReranker:
    """Rerank search results using graph context."""
    
    def rerank(self, results: List[SearchResult], user_context: Dict) -> List[SearchResult]:
        """
        Rerank based on user preferences and graph patterns.
        
        Args:
            results: Initial search results
            user_context: User preferences (price range, preferred neighborhoods)
        """
        for result in results:
            # Boost score if in preferred neighborhood
            if result.neighborhood in user_context.get('preferred_neighborhoods', []):
                result.combined_score *= 1.2
            
            # Boost if similar to previously viewed
            if self._similar_to_history(result, user_context.get('view_history', [])):
                result.combined_score *= 1.1
        
        return sorted(results, key=lambda x: x.combined_score, reverse=True)
```

### 3. Incremental Updates

Support adding new properties without full reindexing:

```python
class IncrementalVectorUpdater:
    """Handle incremental updates to vector embeddings."""
    
    def add_property_embedding(self, property: Property):
        """Add embedding for a single new property."""
        # Generate embedding
        text = self._create_property_text(property)
        embedding = self.embed_model.get_text_embedding(text)
        
        # Store in Neo4j
        query = """
        MATCH (p:Property {listing_id: $listing_id})
        SET p.descriptionEmbedding = $embedding
        """
        
        with self.driver.session() as session:
            session.run(query, listing_id=property.listing_id, embedding=embedding)
    
    def update_changed_properties(self, since_timestamp: str):
        """Update embeddings for properties modified since timestamp."""
        query = """
        MATCH (p:Property)
        WHERE p.last_modified > $timestamp
        AND p.descriptionEmbedding IS NULL
        RETURN p
        """
        # Process only changed properties
```

## Demo Scenarios

### Scenario 1: Natural Language Property Search
```
User: "I need a modern home with mountain views near ski resorts"
System: 
  1. Deer Valley Luxury Chalet - Score: 0.92
     - Vector match: "mountain views", "ski"
     - Graph boost: High-end neighborhood cluster
  
  2. Park City Modern Retreat - Score: 0.88
     - Vector match: "modern", "mountain"
     - Graph boost: Similar to other ski properties
```

### Scenario 2: Similar Property Discovery
```
User views: Property #123
System: "Based on this property, you might also like:"
  - Uses vector similarity for description matching
  - Uses graph SIMILAR_TO relationships
  - Combines both for best recommendations
```

### Scenario 3: Neighborhood Analysis
```
Query: "What makes Nob Hill unique?"
System:
  - Aggregates embeddings from all Nob Hill properties
  - Identifies distinctive features via vector clustering
  - Returns: "Historic architecture, bay views, walkability"
```

## Phased Implementation Plan

### Phase 1: Core Infrastructure (Days 1-2) ✅ COMPLETED

**Goal:** Set up foundation for vector embeddings in Neo4j

**Completed Tasks:**
1. ✅ **Install dependencies** - Added LlamaIndex packages to requirements.txt
2. ✅ **Create PropertyVectorManager** - Built class to manage Neo4j vector indexes with proper dimension handling  
3. ✅ **Copy configuration patterns** - Adapted wiki_embed/config.yaml structure for graph-real-estate vectors
4. ✅ **Review & Test** - Verified Neo4j connection, validated vector index creation

**Results:**
- Created `src/vectors/` module with clean architecture
- Implemented Pydantic models for type-safe configuration
- Successfully created Neo4j vector index with 768 dimensions
- Verified connection to 84 properties in database

### Phase 2: Embedding Pipeline (Days 3-4) ✅ COMPLETED

**Goal:** Generate embeddings using wiki_embed's proven patterns

**Completed Tasks:**
1. ✅ **Copy embedding setup from wiki_embed/** - Reused provider initialization, error handling from wiki_embed/main.py
2. ✅ **Create PropertyEmbeddingPipeline** - Adapted wiki_embed.main.EmbeddingPipeline for property data
3. ✅ **Implement text generation** - Created rich property text with location, details, features
4. ✅ **Add batch processing** - Implemented tqdm progress tracking and batch size optimization
5. ✅ **Review & Test** - Tested embedding generation, verified Ollama integration

**Results:**
- Successfully created PropertyEmbeddingPipeline with multi-provider support
- Implemented property text generation combining 7+ attributes
- Added batch processing with progress tracking
- Verified with 84 properties in test database
- Ready to generate 768-dimension embeddings with nomic-embed-text

### Phase 3: Search Implementation (Days 5-6) ✅ COMPLETED

**Goal:** Build hybrid search with wiki_embed's evaluation framework

**Completed Tasks:**
1. ✅ **Implement vector_search** - Created Cypher queries using db.index.vector.queryNodes (Neo4j's native ANN search)
2. ✅ **Create HybridPropertySearch** - Built class combining vector similarity with graph metrics
3. ✅ **Implement scoring algorithm** - Weighted vector (60%), graph centrality (20%), features (20%)
4. ✅ **Add filtering** - Supports price range, city, neighborhood, bedrooms, bathrooms, sqft filters
5. ✅ **Copy test evaluation** - Adapted patterns for search validation
6. ✅ **Review & Test** - Validated search with graph metrics and filtering

**Results:**
- Successfully created HybridPropertySearch with graph metric integration
- Implemented comprehensive filtering system with 7+ filter types
- Added combined scoring with contextual boosting
- Created standalone scripts: create_embeddings.py and search_properties.py
- Verified with 84 properties, ready for production use

### Phase 4: Integration & Demo (Days 7-8)

**Goal:** Integrate with graph builder using wiki_embed's CLI patterns

**Detailed Tasks:**
1. **Integrate with GraphBuilder** - Add create_vector_embeddings() method as Phase 5 of graph building
2. **Create semantic_search_demo** - Build demo using wiki_embed's test query categories  
3. **Add CLI commands** - Follow wiki_embed.main's pattern: `create`, `test`, `compare`
4. **End-to-end testing** - Run full pipeline, collect metrics like wiki_embed

**CLI Pattern to Copy:**
```python
# From wiki_embed/main.py
if args.command == "create":
    pipeline.create_embeddings()
elif args.command == "test":
    pipeline.test_retrieval()
elif args.command == "compare":
    pipeline.compare_models()
```

### Phase 5: Advanced Features (Days 9-10)

**Goal:** Add sophisticated features with wiki_embed's evaluation framework

**Detailed Tasks:**
1. **Multi-modal embeddings** - Combine text embeddings with normalized numerical features
2. **Incremental updates** - Support adding new properties without full reindexing
3. **Contextual reranking** - Rerank based on user preferences and view history
4. **Add metrics collection** - Use wiki_embed's evaluation framework for performance tracking
5. **Final review** - Performance testing, update README, add usage examples

## Code Reuse Strategy

**From wiki_embed, directly copy/adapt:**
- Provider initialization (`_create_embedding_model()`)
- Configuration loading patterns
- Batch processing with tqdm
- Error handling and retry logic
- Test evaluation framework
- CLI command structure
- Metrics calculation (precision, recall, F1)

**Key Patterns to Maintain:**
- Use same embedding providers (Ollama, OpenAI, Gemini, Voyage)
- Keep consistent configuration structure
- Preserve chunking strategies
- Maintain evaluation metrics approach
- Follow same CLI interface design

This approach ensures consistency across the codebase and leverages proven, tested patterns from wiki_embed.

## Success Metrics

1. **Search Quality**
   - Relevance score > 0.8 for test queries
   - User satisfaction in A/B testing

2. **Performance**
   - Embedding generation: < 0.1s per property
   - Search latency: < 100ms for top-10 results
   - Index creation: < 5 minutes for 10K properties

3. **Scalability**
   - Support 100K+ properties
   - Handle 100+ concurrent searches
   - Incremental updates < 1s per property

## Conclusion

This vector embedding integration transforms graph-real-estate into a powerful semantic search platform. By combining Neo4j's graph capabilities with LlamaIndex's embedding pipeline, we create a system that understands both the meaning of property descriptions and the relationships between properties. The hybrid approach delivers superior search results while maintaining the benefits of graph-based analysis.