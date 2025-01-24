from typing import List, Dict, Optional
from datetime import datetime, timedelta
import chromadb
from chromadb.config import Settings
from src.rag.retrievers.base_retriever import BaseRetriever
from src.embeddings.ollama_embeddings import MyOllamaEmbeddings
from src.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class LogRetriever(BaseRetriever):
    def __init__(
        self,
        collection_name: str = "vector_logs",
        embedding_fn: Optional[MyOllamaEmbeddings] = None
    ):
        self.collection_name = collection_name
        self.embedding_fn = embedding_fn or MyOllamaEmbeddings(
            base_url=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}",
            model=settings.MODEL_NAME
        )
        
        self.client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            settings=Settings(
                allow_reset=True,
                anonymized_telemetry=False
            )
        )
        
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Vector logs and events"},
            embedding_function=self.embedding_fn
        )
        
    async def retrieve(
        self,
        query: str,
        time_window: Optional[timedelta] = None,
        k: int = 5,
        min_relevance: float = 0.7,
        **kwargs
    ) -> List[Dict]:
        try:
            filter_dict = None
            if time_window:
                start_time = datetime.now() - time_window
                start_timestamp = start_time.timestamp()
                filter_dict = {
                    "timestamp_epoch": {
                        "$gte": start_timestamp
                    }
                }

            query_embedding = self.embedding_fn([query])[0]
            initial_k = min(k * 2, 20)  # Get more results initially for filtering

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=initial_k,
                where=filter_dict,
                include=['metadatas', 'documents', 'distances']
            )

            processed_results = []
            
            for i, (distance, doc, meta) in enumerate(zip(
                results['distances'][0],
                results['documents'][0],
                results['metadatas'][0]
            )):
                try:
                    relevance_score = 1 - (distance / 2)  # Convert distance to relevance
                    
                    if relevance_score >= min_relevance:
                        processed_results.append({
                            'content': doc,
                            'metadata': meta,
                            'relevance_score': relevance_score,
                            'type': 'log',
                            'retrieved_at': datetime.now().isoformat()
                        })
                except Exception as e:
                    logger.error(f"Error processing result {i}: {e}")
                    continue

            # Sort by relevance and return top k
            processed_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return processed_results[:k]

        except Exception as e:
            logger.error(f"Error retrieving logs: {e}", exc_info=True)
            return []
            
    async def get_metadata(self) -> Dict:
        try:
            return {
                "total_documents": self.collection.count(),
                "name": self.collection_name,
                "description": self.collection.metadata.get("description", ""),
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting metadata: {e}")
            return {}
            
    async def refresh(self) -> None:
        """Refresh the collection - implementation depends on needs"""
        # Could reload embeddings, clear caches, etc.
        pass