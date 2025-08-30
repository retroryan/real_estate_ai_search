"""Embedding generation pipeline for SQUACK.

This module provides text embedding generation capabilities with support for:
- Multiple embedding providers (Voyage AI, OpenAI, Gemini, Ollama)
- Document conversion and text chunking
- Batch processing for efficiency
- Factory pattern for provider abstraction
- Clean integration with Pydantic models

The embedding pipeline transforms text content from properties, neighborhoods,
and Wikipedia articles into high-dimensional vectors for semantic search.
"""