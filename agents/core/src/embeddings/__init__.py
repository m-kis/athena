# src/embeddings/__init__.py
from .loki_client import LokiClient
from .ollama_embeddings import MyOllamaEmbeddings

__all__ = ['LokiClient', 'MyOllamaEmbeddings']