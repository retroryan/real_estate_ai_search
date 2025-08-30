"""SQUACK Pipeline - DuckDB-based data processing pipeline with embedding generation.

This pipeline implements a medallion architecture (Bronze -> Silver -> Gold) 
for processing real estate, neighborhood, and Wikipedia data with:

- DuckDB for high-performance data processing
- Pydantic V2 for robust data modeling and validation
- Multiple embedding provider support (Voyage, OpenAI, Gemini, Ollama)
- Elasticsearch integration for search capabilities
- Clean modular architecture with clear separation of concerns

Key Components:
- orchestrator: Main pipeline coordination
- models: Pydantic data models and validation
- transformers: Data transformation for search engine compatibility
- writers: Output handling (Parquet, Elasticsearch)
- loaders: Data ingestion from various sources
- embeddings: Text embedding generation pipeline
- processors: Medallion tier processing logic
- config: Configuration management with environment variables
- utils: Shared utilities and helpers
"""