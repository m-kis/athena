import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from src.config.settings import settings
import logging
from src.context.time_window import TimeWindow
import json 
logger = logging.getLogger(__name__)

class LokiClient:
    def __init__(self):
        self.base_url = settings.LOKI_URL
        self.timeout = httpx.Timeout(30.0)
        self.max_retries = 3
        self.retry_delay = 1.0  # secondes
        self.time_window = TimeWindow()
        
    async def query_logs(
        self,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        metric_name: Optional[str] = None,
        limit: int = 1000
    ) -> Dict:
        """
        Query logs with retry logic and better error handling
        """
        if not end_time:
            end_time = datetime.now()

        if not self.time_window.validate_range(start_time, end_time):
            raise ValueError("Invalid time range")

        # Construire la requête Loki
        base_query = '{job="vector"}'
        if metric_name:
            base_query += f',metric_name="{metric_name}"'

        # Convertir les timestamps au format Loki
        time_range = self.time_window.to_loki_format(start_time, end_time)

        params = {
            "query": base_query,
            "start": time_range['start'],
            "end": time_range['end'],
            "limit": str(limit),
            "step": "15s"
        }

        retry_count = 0
        last_exception = None

        while retry_count < self.max_retries:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        f"{self.base_url}/loki/api/v1/query_range",
                        params=params
                    )
                    
                    response.raise_for_status()
                    result = response.json()
                    
                    formatted_logs = self._format_response(result)
                    stats = self._compute_stats(result)
                    
                    return {
                        "logs": formatted_logs,
                        "stats": stats,
                        "metadata": {
                            "query": base_query,
                            "time_range": self.time_window.to_human_readable(start_time, end_time)
                        }
                    }

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error occurred: {e.response.status_code}")
                if e.response.status_code == 429:  # Rate limit
                    retry_delay = float(e.response.headers.get('Retry-After', self.retry_delay))
                    await asyncio.sleep(retry_delay)
                elif e.response.status_code >= 500:  # Server error
                    await asyncio.sleep(self.retry_delay * (2 ** retry_count))
                else:
                    raise
                    
            except httpx.ConnectError:
                logger.error("Connection error, retrying...")
                await asyncio.sleep(self.retry_delay * (2 ** retry_count))
                
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                last_exception = e
                await asyncio.sleep(self.retry_delay)
                
            retry_count += 1

        raise Exception(f"Failed after {self.max_retries} retries. Last error: {last_exception}")

    def _format_response(self, result: Dict) -> List[Dict]:
        """Format Loki response into structured logs"""
        formatted_logs = []
        
        try:
            if "data" not in result or "result" not in result["data"]:
                return formatted_logs

            for stream in result["data"]["result"]:
                labels = stream.get("stream", {})
                
                for timestamp, message in stream.get("values", []):
                    try:
                        # Convert timestamp
                        ts = int(timestamp) / 1e9  # Convert from nanoseconds
                        formatted_time = datetime.fromtimestamp(ts)

                        # Try to parse message as JSON
                        try:
                            message_content = json.loads(message)
                        except json.JSONDecodeError:
                            message_content = message

                        formatted_logs.append({
                            "timestamp": formatted_time.isoformat(),
                            "message": message_content,
                            "labels": labels,
                            "raw_timestamp": timestamp
                        })
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error formatting log entry: {e}")
                        continue
                        
            return formatted_logs
            
        except Exception as e:
            logger.error(f"Error formatting response: {e}")
            return formatted_logs

    def _compute_stats(self, result: Dict) -> Dict:
        """Compute response statistics"""
        stats = {
            "total_streams": 0,
            "total_logs": 0,
            "unique_labels": set(),
            "time_range": {
                "start": None,
                "end": None
            }
        }
        
        try:
            if "data" in result and "result" in result["data"]:
                stats["total_streams"] = len(result["data"]["result"])
                
                for stream in result["data"]["result"]:
                    if "values" in stream:
                        stats["total_logs"] += len(stream["values"])
                        
                    if "stream" in stream:
                        stats["unique_labels"].update(stream["stream"].keys())

            stats["unique_labels"] = list(stats["unique_labels"])
            return stats
            
        except Exception as e:
            logger.error(f"Error computing stats: {e}")
            return stats