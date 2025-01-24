# src/embeddings/chroma_client.py
from typing import Optional
from chromadb import Client, Settings
from chromadb.config import System
import logging
from src.config.settings import settings

logger = logging.getLogger(__name__)

class ChromaDBClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if not self._initialized:
            self.client = Client(
                Settings(
                    chroma_api_impl="rest",
                    chroma_server_host=settings.CHROMA_HOST,
                    chroma_server_http_port=settings.CHROMA_PORT,
                    anonymized_telemetry=False
                )
            )
            self._collections = {}
            self._initialized = True
            
    def get_or_create_collection(self, name: str, **kwargs):
        """Get existing collection or create new one with caching"""
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                **kwargs
            )
        return self._collections[name]
        
    def reset(self):
        """Reset client state"""
        self._collections = {}
        if hasattr(self, 'client'):
            self.client.reset()
            
