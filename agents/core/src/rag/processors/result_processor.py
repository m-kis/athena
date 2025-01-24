# src/rag/embedders/rag_embedder.py
from typing import List, Any
import logging
from src.embeddings.ollama_embeddings import MyOllamaEmbeddings
from src.config.settings import settings

logger = logging.getLogger(__name__)

class RAGEmbedder:
    MIN_EMBEDDING_DIMENSION = 384

    def __init__(self):
        self.embedding_fn = MyOllamaEmbeddings(
            base_url=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}",
            model=settings.MODEL_NAME
        )

    async def generate_embedding(self, text: str) -> List[float]:
        try:
            embedding = self.embedding_fn([text])[0]
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    def validate_embedding(self, embedding: List[float]) -> bool:
        if not embedding or len(embedding) < self.MIN_EMBEDDING_DIMENSION:
            return False
        return all(isinstance(x, (int, float)) for x in embedding)

# src/rag/processors/result_processor.py
from typing import Dict, List
import logging
from datetime import datetime
import math

logger = logging.getLogger(__name__)

class ResultProcessor:
    def process_results(self, results: List[Any], min_relevance: float = 0.7) -> List[Dict]:
        processed_results = []
        for result in results:
            try:
                # Si le résultat est une chaîne, le convertir en dict
                if isinstance(result, str):
                    processed_result = {
                        'content': result,
                        'relevance': min_relevance
                    }
                else:
                    processed_result = result

                if processed_result.get('relevance', 0) >= min_relevance:
                    processed_results.append(processed_result)
                    
            except Exception as e:
                logger.error(f"Error processing result: {e}")
                continue
                
        return processed_results

    def _calculate_base_relevance(self, result: Dict) -> float:
        try:
            distance = result.get('distance', 1.0)
            return 1.0 - (distance / 2)
        except Exception:
            return 0.0

    def _calculate_context_boost(self, result: Dict) -> float:
        boost = 0.0
        meta = result.get('metadata', {})
        
        if meta.get('level', '').upper() in ['ERROR', 'CRITICAL']:
            boost += 0.2
        elif meta.get('level', '').upper() == 'WARNING':
            boost += 0.1
            
        if meta.get('source') in ['system', 'monitoring']:
            boost += 0.1
            
        return min(0.3, boost)

    def _calculate_time_boost(self, result: Dict) -> float:
        try:
            timestamp = result.get('metadata', {}).get('timestamp')
            if not timestamp:
                return 0.0
                
            age_hours = (datetime.now() - datetime.fromisoformat(timestamp)).total_seconds() / 3600
            return max(0, 0.2 * math.exp(-age_hours / 24))
        except Exception:
            return 0.0
