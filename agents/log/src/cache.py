from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class LogAnalysisCache:
    def __init__(self):
        self._cache = {}

    async def get(self, key: str) -> Optional[Dict]:
        """Récupère une valeur du cache si elle existe"""
        if key in self._cache:
            logger.debug(f"Cache hit for key: {key}")
            return self._cache[key]
        logger.debug(f"Cache miss for key: {key}")
        return None

    async def set(self, key: str, value: Dict) -> None:
        """Met une valeur dans le cache"""
        logger.debug(f"Setting cache for key: {key}")
        self._cache[key] = value

    def clear(self) -> None:
        """Vide le cache"""
        logger.debug("Clearing cache")
        self._cache.clear()

    @property
    def size(self) -> int:
        """Retourne la taille du cache"""
        return len(self._cache)