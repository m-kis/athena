from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
import time
import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, rate_limit: int = 100, window: int = 60):
        self.rate_limit = rate_limit  # requests per window
        self.window = window  # window in seconds
        self.requests = defaultdict(list)  # IP -> list of timestamps
        self._cleanup_task = None

    def is_allowed(self, ip: str) -> bool:
        now = time.time()
        # Remove old requests
        self.requests[ip] = [ts for ts in self.requests[ip] if ts > now - self.window]
        
        # Check if under limit
        if len(self.requests[ip]) < self.rate_limit:
            self.requests[ip].append(now)
            return True
        return False

    async def cleanup(self):
        while True:
            try:
                now = time.time()
                # Remove entries older than window
                for ip in list(self.requests.keys()):
                    self.requests[ip] = [ts for ts in self.requests[ip] if ts > now - self.window]
                    if not self.requests[ip]:
                        del self.requests[ip]
            except Exception as e:
                logger.error(f"Error in rate limiter cleanup: {e}")
            await asyncio.sleep(self.window)

    def start_cleanup(self):
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self.cleanup())

    def stop_cleanup(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None

class EnhancedCache:
    def __init__(self, default_ttl: int = 300, cleanup_interval: int = 60):
        self.cache: Dict[str, Dict] = {}
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self._cleanup_task = None
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }

    async def get(self, key: str) -> Optional[Dict]:
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

    async def set(self, key: str, value: Dict, ttl: Optional[int] = None):
        expiry = None
        if ttl is not None:
            expiry = datetime.now() + timedelta(seconds=ttl)
        elif self.default_ttl:
            expiry = datetime.now() + timedelta(seconds=self.default_ttl)

        self.cache[key] = {
            'value': value,
            'expiry': expiry,
            'created_at': datetime.now()
        }

    async def delete(self, key: str):
        if key in self.cache:
            del self.cache[key]
            self.stats['evictions'] += 1

    async def cleanup(self):
        while True:
            try:
                now = datetime.now()
                keys_to_delete = [
                    key for key, item in self.cache.items()
                    if item['expiry'] and now > item['expiry']
                ]
                for key in keys_to_delete:
                    await self.delete(key)
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
            await asyncio.sleep(self.cleanup_interval)

    def start_cleanup(self):
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self.cleanup())

    def stop_cleanup(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self, 
        app: FastAPI, 
        rate_limit: int = 100,
        window: int = 60
    ):
        super().__init__(app)
        self.rate_limiter = RateLimiter(rate_limit, window)
        self.rate_limiter.start_cleanup()

    async def dispatch(self, request: Request, call_next):
        # Get client IP
        ip = request.client.host
        
        # Check rate limit
        if not self.rate_limiter.is_allowed(ip):
            raise HTTPException(
                status_code=429, 
                detail="Too many requests. Please try again later."
            )
            
        try:
            # Process request
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            raise

    async def shutdown(self):
        self.rate_limiter.stop_cleanup()