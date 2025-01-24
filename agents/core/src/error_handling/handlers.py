from functools import wraps
from typing import Callable, TypeVar, Any, Optional
import asyncio
from datetime import datetime
import httpx
import logging
from chromadb.errors import ChromaError

logger = logging.getLogger(__name__)

T = TypeVar('T')

class ServiceError(Exception):
    def __init__(self, service: str, error: str, details: Optional[dict] = None):
        self.service = service
        self.error = error
        self.details = details or {}
        self.timestamp = datetime.now()
        super().__init__(f"{service} error: {error}")

class LokiError(ServiceError):
    def __init__(self, error: str, details: Optional[dict] = None):
        super().__init__("Loki", error, details)

class ChromaDBError(ServiceError):
    def __init__(self, error: str, details: Optional[dict] = None):
        super().__init__("ChromaDB", error, details)

def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential: bool = True
) -> Callable:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            delay = initial_delay

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (httpx.HTTPError, ChromaError) as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {str(e)}"
                    )

                    if attempt < max_retries - 1:
                        # Calculate next delay
                        if exponential:
                            delay = min(delay * 2, max_delay)
                        
                        logger.info(f"Retrying in {delay} seconds...")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All retries failed for {func.__name__}",
                            exc_info=True
                        )
                except Exception as e:
                    # Don't retry on non-HTTP/ChromaDB errors
                    logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                    raise

            # If we get here, all retries failed
            if isinstance(last_exception, httpx.HTTPError):
                raise LokiError(
                    f"Failed after {max_retries} retries",
                    {
                        "original_error": str(last_exception),
                        "status_code": getattr(last_exception, 'response', {}).get('status_code')
                    }
                )
            elif isinstance(last_exception, ChromaError):
                raise ChromaDBError(
                    f"Failed after {max_retries} retries",
                    {"original_error": str(last_exception)}
                )
            else:
                raise last_exception

        return wrapper
    return decorator

class ErrorHandler:
    @staticmethod
    async def handle_loki_error(error: Exception) -> dict:
        if isinstance(error, LokiError):
            return {
                "error": "Log retrieval failed",
                "details": error.details,
                "timestamp": error.timestamp.isoformat()
            }
        return {
            "error": "Unknown error during log retrieval",
            "details": {"message": str(error)}
        }

    @staticmethod
    async def handle_chromadb_error(error: Exception) -> dict:
        if isinstance(error, ChromaDBError):
            return {
                "error": "Vector database operation failed",
                "details": error.details,
                "timestamp": error.timestamp.isoformat()
            }
        return {
            "error": "Unknown error during vector database operation",
            "details": {"message": str(error)}
        }

    @staticmethod
    async def handle_service_error(error: Exception) -> dict:
        if isinstance(error, ServiceError):
            return {
                "service": error.service,
                "error": error.error,
                "details": error.details,
                "timestamp": error.timestamp.isoformat()
            }
        return {
            "error": "Internal service error",
            "details": {"message": str(error)}
        }

# Example usage:
class LokiClient:
    @with_retry(max_retries=3, initial_delay=1.0)
    async def query_logs(self, query: str) -> dict:
        async with httpx.AsyncClient() as client:
            # Your actual implementation here
            response = await client.get("/query", params={"query": query})
            response.raise_for_status()
            return response.json()

class ChromaDBClient:
    @with_retry(max_retries=3, initial_delay=1.0)
    async def query_embeddings(self, query: str) -> dict:
        try:
            # Your actual implementation here
            results = await self.collection.query(query_texts=[query])
            return results
        except Exception as e:
            raise ChromaDBError("Query failed", {"query": query, "error": str(e)})