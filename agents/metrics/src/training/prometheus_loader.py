from typing import Dict, List, Optional
from datetime import datetime, timedelta
import httpx
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class PrometheusDataLoader:
    def __init__(self, base_url: str = "http://localhost:9090"):
        self.base_url = base_url
        self.metrics = {
            'cpu_usage': 'athena_system_cpu_usage',
            'memory_usage': 'system_memory_usage_bytes',
            'disk_usage': 'system_disk_usage_bytes'
        }

    async def load_training_data(
        self,
        metric_type: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        step: str = "1h"
    ) -> pd.DataFrame:
        if not start_time:
            start_time = datetime.now() - timedelta(days=7)
        if not end_time:
            end_time = datetime.now()

        metric_name = self.metrics.get(metric_type)
        if not metric_name:
            raise ValueError(f"Unknown metric type: {metric_type}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/query_range",
                    params={
                        "query": metric_name,
                        "start": int(start_time.timestamp()),
                        "end": int(end_time.timestamp()),
                        "step": step
                    }
                )
                response.raise_for_status()
                data = response.json()

                if "data" in data and "result" in data["data"]:
                    values = []
                    for result in data["data"]["result"]:
                        for value in result["values"]:
                            values.append({
                                'timestamp': datetime.fromtimestamp(value[0]),
                                'value': float(value[1]),
                                'metric': metric_type
                            })
                    
                    return pd.DataFrame(values)
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error loading data from Prometheus: {e}")
            return pd.DataFrame()