from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from collections import OrderedDict
import asyncio
from src.rag.cache.base_cache import BaseCache

CACHE_TTL = timedelta(minutes=5)
class MemoryCache(BaseCache):
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict = OrderedDict()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
        
    async def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            self.stats['misses'] += 1
            return None
            
        value, expiry = self.cache[key]
        if expiry and datetime.now() > expiry:
            await self.delete(key)
            self.stats['misses'] += 1
            return None
            
        self.cache.move_to_end(key)
        self.stats['hits'] += 1
        return value
        
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        if len(self.cache) >= self.max_size:
            # Éviction du plus ancien
            self.cache.popitem(last=False)
            self.stats['evictions'] += 1
            
        expiry = None
        if ttl is not None:
            expiry = datetime.now() + timedelta(seconds=ttl)
        elif self.default_ttl:
            expiry = datetime.now() + timedelta(seconds=self.default_ttl)
            
        self.cache[key] = (value, expiry)
        self.cache.move_to_end(key)

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Récupère plusieurs éléments du cache"""
        results = {}
        for key in keys:
            if value := await self.get(key):
                results[key] = value
        return results

    async def set_many(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """Stocke plusieurs éléments dans le cache"""
        for key, value in items.items():
            await self.set(key, value, ttl, metadata)
        
    async def delete(self, key: str) -> bool:
        """Supprime un élément du cache"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
        
    async def clear(self) -> None:
        """Vide le cache"""
        self.cache.clear()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
        
    async def clear_expired(self) -> int:
        """Supprime les éléments expirés du cache"""
        now = datetime.now()
        expired_count = 0
        for key, (_, expiry) in list(self.cache.items()):
            if expiry and now > expiry:
                await self.delete(key)
                expired_count += 1
        return expired_count
            
    async def get_stats(self) -> Dict:
        """Retourne les statistiques du cache"""
        return {
            **self.stats,
            'size': len(self.cache),
            'max_size': self.max_size,
            'utilization': len(self.cache) / self.max_size * 100
        }