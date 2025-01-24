from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class BaseCache(ABC):
    """Abstract base class for cache implementations"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve item from cache
        
        Args:
            key: Cache key
        
        Returns:
            Optional[Any]: Cached value or None if not found
        """
        pass
        
    @abstractmethod
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Store item in cache with optional TTL and metadata
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            metadata: Optional metadata about the cached item
        """
        pass
        
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Remove item from cache
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if item was deleted, False if not found
        """
        pass
        
    @abstractmethod
    async def clear(self) -> None:
        """Clear all items from cache"""
        pass
        
    @abstractmethod
    async def clear_expired(self) -> int:
        """
        Clear expired items from cache
        
        Returns:
            int: Number of items cleared
        """
        pass

    @abstractmethod
    async def get_stats(self) -> Dict:
        """
        Get cache statistics
        
        Returns:
            Dict containing:
                - size: Current number of items
                - hits: Number of cache hits
                - misses: Number of cache misses
                - hit_rate: Cache hit rate
                - memory_usage: Estimated memory usage
                - evictions: Number of items evicted
        """
        pass
        
    @abstractmethod
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Retrieve multiple items from cache
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dict mapping keys to values (missing keys omitted)
        """
        pass

    @abstractmethod 
    async def set_many(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Store multiple items in cache
        
        Args:
            items: Dict mapping keys to values
            ttl: Optional TTL in seconds
            metadata: Optional metadata to attach to all items
        """
        pass
        
    async def touch(self, key: str, ttl: int) -> bool:
        """
        Update TTL for cached item
        
        Args:
            key: Cache key
            ttl: New TTL in seconds
            
        Returns:
            bool: True if item existed and was updated
        """
        pass

    async def get_metadata(self, key: str) -> Optional[Dict]:
        """
        Get metadata for cached item
        
        Args:
            key: Cache key
            
        Returns:
            Optional[Dict]: Item metadata if it exists
        """
        pass

    def validate_key(self, key: str) -> None:
        """
        Validate cache key format
        
        Raises:
            ValueError: If key is invalid
        """
        if not isinstance(key, str):
            raise ValueError("Cache key must be a string")
            
        if not key:
            raise ValueError("Cache key cannot be empty")
            
        if len(key) > 256:
            raise ValueError("Cache key too long (max 256 chars)")
            
    def validate_ttl(self, ttl: Optional[int]) -> None:
        """
        Validate TTL value
        
        Raises: 
            ValueError: If TTL is invalid
        """
        if ttl is not None:
            if not isinstance(ttl, int):
                raise ValueError("TTL must be an integer")
                
            if ttl < 0:
                raise ValueError("TTL cannot be negative")
                
    async def check_health(self) -> Dict:
        """
        Check cache health status
        
        Returns:
            Dict containing:
                - status: 'healthy' or 'unhealthy'
                - message: Status details
                - stats: Cache statistics
        """
        try:
            stats = await self.get_stats()
            return {
                'status': 'healthy',
                'message': 'Cache operating normally',
                'stats': stats
            }
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {
                'status': 'unhealthy',
                'message': str(e),
                'stats': {}
            }