from typing import List
import numpy as np
import logging
from src.embeddings.ollama_embeddings import MyOllamaEmbeddings
from src.config.settings import settings

logger = logging.getLogger(__name__)

class RAGEmbedder:
    MIN_EMBEDDING_DIMENSION = 384

    def __init__(self):
        logging.info("Initializing RAGEmbedder...")
        self.embedding_fn = MyOllamaEmbeddings(
            base_url=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}",
            model=settings.MODEL_NAME
        )
        logging.info("RAGEmbedder initialized successfully")

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        try:
            embedding = self.embedding_fn([text])[0]
            if isinstance(embedding, np.ndarray):
                return embedding.tolist()
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    def validate_embedding(self, embedding: List[float]) -> bool:
        """Validate embedding quality"""
        if not isinstance(embedding, list):
            return False
            
        if len(embedding) == 0:
            return False
            
        if len(embedding) < self.MIN_EMBEDDING_DIMENSION:
            return False
            
        # Vérifier que tous les éléments sont des nombres
        return all(isinstance(x, (int, float)) for x in embedding)

    def normalize_embedding(self, embedding: List[float]) -> List[float]:
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