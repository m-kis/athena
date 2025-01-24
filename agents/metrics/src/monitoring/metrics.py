from prometheus_client import Counter, Histogram, Summary, Gauge, CollectorRegistry
from typing import Dict, Optional
from contextlib import contextmanager
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

class MetricsManager:
    _instance = None
    _initialized = False
    _registry = CollectorRegistry()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._init_metrics()
            MetricsManager._initialized = True

    def _init_metrics(self):
        """Initialize metrics only once"""
        # Request metrics
        self.request_count = Counter(
            'athena_requests_total',
            'Total requests',
            ['endpoint', 'status'],
            registry=self._registry
        )
        
        self.request_duration = Histogram(
            'athena_request_duration_seconds',
            'Request duration',
            ['endpoint'],
            registry=self._registry
        )
        
        # RAG metrics
        self.rag_query_duration = Histogram(
            'athena_rag_query_duration_seconds',
            'RAG query duration',
            ['query_type'],
            registry=self._registry
        )
        
        self.rag_cache_hits = Counter(
            'athena_rag_cache_hits_total',
            'RAG cache hits',
            registry=self._registry
        )
        
        # Agent metrics
        self.agent_processing_duration = Histogram(
            'athena_agent_processing_seconds',
            'Agent processing time',
            ['agent_type'],
            registry=self._registry
        )
        
        # LLM metrics
        self.llm_requests = Counter(
            'athena_llm_requests_total',
            'LLM requests',
            ['model', 'operation'],
            registry=self._registry
        )
        
        # System metrics
        self.memory_usage = Gauge(
            'athena_memory_usage_bytes',
            'Memory usage',
            registry=self._registry
        )
        
        self.active_connections = Gauge(
            'athena_active_connections',
            'Active connections',
            registry=self._registry
        )

        logger.info("Metrics initialized successfully")

    def track_request(self, endpoint: str, start_time: float, status: str = 'success'):
        duration = time.time() - start_time
        self.request_duration.labels(endpoint=endpoint).observe(duration)
        self.request_count.labels(endpoint=endpoint, status=status).inc()
    
    def track_rag_query(self, query_type: str, duration: float):
        self.rag_query_duration.labels(query_type=query_type).observe(duration)
    
    def track_agent_processing(self, agent_type: str, duration: float):
        self.agent_processing_duration.labels(agent_type=agent_type).observe(duration)
    
    @contextmanager
    def track_llm_request(self, model: str, operation: str):
        """Context manager for tracking LLM requests"""
        start_time = time.time()
        self.llm_requests.labels(model=model, operation=operation).inc()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.request_duration.labels(endpoint=f"llm_{operation}").observe(duration)
        
    def update_system_metrics(self, memory_usage: int, connections: int):
        self.memory_usage.set(memory_usage)
        self.active_connections.set(connections)

    @property
    def registry(self):
        """Get the metrics registry"""
        return self._registry

# Global metrics manager instance
metrics_manager = MetricsManager()

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking request metrics"""
    def __init__(self, app):
        super().__init__(app)
        self.metrics = metrics_manager

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.time()
        try:
            response = await call_next(request)
            self.metrics.track_request(
                request.url.path,
                start_time,
                str(response.status_code)
            )
            return response
        except Exception as e:
            self.metrics.track_request(
                request.url.path,
                start_time,
                'error'
            )
            raise