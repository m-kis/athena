from typing import Dict, Optional, Any, List
import asyncio
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class EnhancedCache:
    def __init__(self, default_ttl: int = 300, cleanup_interval: int = 60):
        self.cache: Dict[str, Dict] = {}
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }

    async def start_cleanup(self) -> None:
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Cache cleanup task started")

    async def stop_cleanup(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Cache cleanup task stopped")

    async def _cleanup_loop(self) -> None:
        while True:
            try:
                await self._cleanup_expired()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(self.cleanup_interval)

    async def _cleanup_expired(self) -> None:
        now = datetime.now()
        keys_to_delete = [
            key for key, item in self.cache.items()
            if item['expiry'] and now > item['expiry']
        ]
        for key in keys_to_delete:
            await self.delete(key)
            self.stats['evictions'] += 1

    async def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            self.stats['misses'] += 1
            return None

        item = self.cache[key]
        if item['expiry'] and datetime.now() > item['expiry']:
            await self.delete(key)
            self.stats['misses'] += 1
            return None

        self.stats['hits'] += 1
        return item['value']

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache"""
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
        """Set multiple values in cache"""
        for key, value in items.items():
            await self.set(key, value, ttl, metadata)

    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        expiry = None
        if ttl is not None:
            expiry = datetime.now() + timedelta(seconds=ttl)
        elif self.default_ttl:
            expiry = datetime.now() + timedelta(seconds=self.default_ttl)

        self.cache[key] = {
            'value': value,
            'expiry': expiry,
            'metadata': metadata or {},
            'created_at': datetime.now()
        }

    async def delete(self, key: str) -> None:
        self.cache.pop(key, None)

    async def clear(self) -> None:
        self.cache.clear()
        self.stats = {'hits': 0, 'misses': 0, 'evictions': 0}

    async def get_stats(self) -> Dict:
        return {
            **self.stats,
            'size': len(self.cache),
            'hit_rate': self._calculate_hit_rate(),
            'memory_usage': len(self.cache)
        }

    def _calculate_hit_rate(self) -> float:
        total = self.stats['hits'] + self.stats['misses']
        if total == 0:
            return 0.0
        return self.stats['hits'] / total

# Create instance
cache = EnhancedCache()