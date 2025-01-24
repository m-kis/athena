# src/rag/processors/context_processor.py
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json
import logging
from chromadb.api import Collection

# Local imports
from src.rag.retrievers.log_retriever import LogRetriever
from src.rag.retrievers.metric_retriever import MetricRetriever
from src.rag.cache.memory_cache import MemoryCache
from src.embeddings.ollama_embeddings import MyOllamaEmbeddings
from src.config.settings import settings
from src.embeddings.chroma_manager import chroma_manager

logger = logging.getLogger(__name__)

class ContextProcessor:
    def __init__(self):
        self.log_retriever = LogRetriever()
        self.metric_retriever = MetricRetriever()
        self.embedder = MyOllamaEmbeddings(
            base_url=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}",
            model=settings.MODEL_NAME
        )
        self.cache = MemoryCache(max_size=1000, default_ttl=300)
        
        # Initialize collections
        self.logs_collection: Collection = chroma_manager.get_collection("vector_logs")
        self.metrics_collection: Collection = chroma_manager.get_collection("vector_metrics")

    async def retrieve_context(
        self,
        query: str,
        time_window: Optional[timedelta] = None,
        k: int = 5,
        min_relevance: float = 0.7,
        include_metrics: bool = True
    ) -> Dict[str, Any]:
        """Retrieve relevant context based on query"""
        try:
            # Generate cache key
            cache_key = f"context:{query}:{time_window}:{k}:{include_metrics}"
            cached = await self.cache.get(cache_key)
            if cached:
                return cached

            # Generate query embedding
            query_embedding = await self.embedder.generate_embedding(query)
            if not query_embedding:
                logger.warning("Failed to generate embedding for query")
                return self._get_empty_context()

            # Get log results
            log_results = await self.log_retriever.retrieve(
                query=query,
                time_window=time_window,
                k=k,
                min_relevance=min_relevance
            )

            # Get metrics if requested
            metric_results = []
            if include_metrics:
                metric_results = await self.metric_retriever.retrieve(
                    query=query,
                    time_window=time_window,
                    k=k // 2
                )

            # Process results
            combined_results = self._combine_results(log_results, metric_results)
            processed_context = self._process_context(combined_results)

            # Cache results
            await self.cache.set(cache_key, processed_context)
            return processed_context

        except Exception as e:
            logger.error(f"Error retrieving context: {e}", exc_info=True)
            return self._get_empty_context()

    def _get_empty_context(self) -> Dict[str, Any]:
        """Return empty context structure"""
        return {
            'logs': [],
            'metrics': [],
            'summary': {
                'total_items': 0,
                'log_count': 0,
                'metric_count': 0,
                'avg_relevance': 0,
                'timestamp_range': {
                    'start': None,
                    'end': None
                }
            }
        }

    def _prepare_time_filter(self, time_window: Optional[timedelta]) -> Dict[str, Any]:
        """Prepare time filter for queries"""
        if not time_window:
            return {}

        now = datetime.now()
        start_time = now - time_window
        return {
            "timestamp": {
                "$gte": start_time.timestamp(),
                "$lte": now.timestamp()
            }
        }

    def _combine_results(self, log_results: List[Dict], metric_results: List[Dict]) -> List[Dict]:
        """Combine and sort results by relevance"""
        combined = []
        
        for result in log_results:
            result['source'] = 'log'
            combined.append(result)
            
        for result in metric_results:
            result['source'] = 'metric'
            combined.append(result)
            
        combined.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return combined

    def _process_context(self, combined_results: List[Dict]) -> Dict[str, Any]:
        """Process combined results into structured context"""
        context = self._get_empty_context()
        context['summary']['total_items'] = len(combined_results)

        relevance_sum = 0
        timestamps = []

        for result in combined_results:
            if ts := result.get('metadata', {}).get('timestamp'):
                timestamps.append(datetime.fromisoformat(ts))

            if result['source'] == 'log':
                context['logs'].append(result)
                context['summary']['log_count'] += 1
            else:
                context['metrics'].append(result)
                context['summary']['metric_count'] += 1

            relevance_sum += result.get('relevance_score', 0)

        if timestamps:
            context['summary']['timestamp_range'] = {
                'start': min(timestamps).isoformat(),
                'end': max(timestamps).isoformat()
            }

        if combined_results:
            context['summary']['avg_relevance'] = relevance_sum / len(combined_results)

        return context