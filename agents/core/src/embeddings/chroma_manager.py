# src/embeddings/chroma_manager.py
from typing import Optional, Dict
import chromadb
from chromadb.config import Settings
import logging
from functools import lru_cache
from src.config.settings import settings

logger = logging.getLogger(__name__)

def __init__(self):
    if not self._initialized:
        try:
            self.client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT
            )
            self._collections = {}
            self._initialized = True
        except Exception as e:
            logger.error(f"ChromaDB init failed: {e}")
            raise
class ChromaManager:
    _instance = None
    _client = None
    _collections: Dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def client(self):
        if self._client is None:
            self._client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
                settings=Settings(
                    allow_reset=True,
                    anonymized_telemetry=False
                )
            )
        return self._client

    @lru_cache(maxsize=32)
    def get_collection(self, name: str, **kwargs):
        """Get or create a collection with caching"""
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                **kwargs
            )
        return self._collections[name]

    def reset(self):
        """Reset the client and collections"""
        self._collections.clear()
        self.get_collection.cache_clear()
        if self._client:
            self._client.reset()
            self._client = None

# Create a global instance
chroma_manager = ChromaManager()