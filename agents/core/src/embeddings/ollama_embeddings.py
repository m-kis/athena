# src/embeddings/ollama_embeddings.py
from typing import List, Union
from langchain_ollama import OllamaEmbeddings
from chromadb.api.types import EmbeddingFunction
import numpy as np
import logging

logger = logging.getLogger(__name__)

class MyOllamaEmbeddings(EmbeddingFunction):
    def __init__(self, base_url: str, model: str):
        self._embeddings = OllamaEmbeddings(
            base_url=base_url,
            model=model
        )

    def __call__(self, input: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        if isinstance(input, str):
            input = [input]
            
        embeddings = []
        for text in input:
            embedding = self._embeddings.embed_query(text)
            if isinstance(embedding, np.ndarray):
                embeddings.append(embedding.tolist())
            else:
                embeddings.append(embedding)
        return embeddings

    async def generate_embedding(self, text: Union[str, List[str]]) -> List[float]:
        """Generate embeddings for text(s)"""
        try:
            if isinstance(text, list):
                embeddings = [self._embeddings.embed_query(t) for t in text]
                return [self._normalize_embedding(e) for e in embeddings]
            else:
                embedding = self._embeddings.embed_query(text)
                return self._normalize_embedding(embedding)
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            # Return zero vector of appropriate size as fallback
            size = 384  # Default size for most models
            return [0.0] * size

    def _normalize_embedding(self, embedding: List[float]) -> List[float]:
        """Normalize embedding vector"""
        try:
            if not embedding:
                return []

            vector = np.array(embedding)
            norm = np.linalg.norm(vector)
            
            if norm == 0:
                return embedding
                
            normalized = vector / norm
            return normalized.tolist()
        except Exception as e:
            logger.error(f"Error normalizing embedding: {e}")
            return embedding

    @property
    def dimension(self) -> int:
        """Get embedding dimension"""
        return 384  # Default size, could be made configurable