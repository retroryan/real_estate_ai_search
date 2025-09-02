"""Test utilities for integration tests."""

from typing import List
from squack_pipeline_v2.embeddings.base import EmbeddingProvider, EmbeddingResponse


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing."""
    
    def __init__(self):
        """Initialize mock provider with test values."""
        super().__init__(api_key="test_key", model_name="test_model", dimension=3)
    
    def generate_embeddings(self, texts: List[str]) -> EmbeddingResponse:
        """Generate mock embeddings.
        
        Args:
            texts: Texts to embed
            
        Returns:
            Mock EmbeddingResponse with simple embeddings
        """
        # Generate simple mock embeddings (3-dimensional)
        embeddings = []
        for i, text in enumerate(texts):
            # Create a simple deterministic embedding based on text length
            text_len = float(len(text))
            embedding = [
                text_len / 100.0,  # Normalized length
                float(i) / 100.0,   # Position in batch
                0.5                 # Constant value
            ]
            embeddings.append(embedding)
        
        return EmbeddingResponse(
            embeddings=embeddings,
            model_name=self.model_name,
            dimension=self.dimension,
            token_count=sum(len(t.split()) for t in texts)
        )
    
    def get_batch_size(self) -> int:
        """Get recommended batch size."""
        return 100  # Large batch size for testing