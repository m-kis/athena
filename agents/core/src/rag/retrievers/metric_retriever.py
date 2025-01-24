from typing import List, Dict, Optional
from datetime import datetime, timedelta
import chromadb
from chromadb.config import Settings
from src.rag.retrievers.base_retriever import BaseRetriever
from src.embeddings.ollama_embeddings import MyOllamaEmbeddings
from src.config.settings import settings
import logging
import json

logger = logging.getLogger(__name__)

class MetricRetriever(BaseRetriever):
    def __init__(
        self,
        collection_name: str = "vector_metrics",
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
            metadata={"description": "Performance metrics and statistics"},
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
                filter_dict = {
                    "timestamp_epoch": {
                        "$gte": start_time.timestamp()
                    }
                }

            # Add metric-specific filters from kwargs
            metric_type = kwargs.get('metric_type')
            if metric_type:
                if not filter_dict:
                    filter_dict = {}
                filter_dict["type"] = metric_type

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
                    # Convert distance to relevance score
                    relevance_score = 1 - (distance / 2)
                    
                    if relevance_score >= min_relevance:
                        # Parse metric content
                        metric_content = json.loads(doc) if isinstance(doc, str) else doc
                        
                        processed_results.append({
                            'content': metric_content,
                            'metadata': meta,
                            'relevance_score': relevance_score,
                            'type': 'metric',
                            'metric_type': metric_content.get('name', 'unknown'),
                            'value': metric_content.get('value'),
                            'unit': metric_content.get('unit', ''),
                            'retrieved_at': datetime.now().isoformat()
                        })
                except Exception as e:
                    logger.error(f"Error processing metric result {i}: {e}")
                    continue

            # Sort by relevance and return top k
            processed_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return processed_results[:k]

        except Exception as e:
            logger.error(f"Error retrieving metrics: {e}", exc_info=True)
            return []

    async def get_metadata(self) -> Dict:
        try:
            total_docs = self.collection.count()
            # Get unique metric types
            results = self.collection.get()
            metric_types = set()
            
            for meta in results['metadatas']:
                if 'type' in meta:
                    metric_types.add(meta['type'])

            return {
                "total_documents": total_docs,
                "metric_types": list(metric_types),
                "name": self.collection_name,
                "description": self.collection.metadata.get("description", ""),
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting metadata: {e}")
            return {}

    async def refresh(self) -> None:
        """Refresh metric collection if needed"""
        pass