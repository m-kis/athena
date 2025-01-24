# src/agents/metrics/metrics_processor.py
from typing import Dict, List, Any
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import json
from src.monitoring.metrics_collector import MetricsCollector
logger = logging.getLogger(__name__)

class MetricsProcessor:
    def __init__(self):
        self.required_columns = ['timestamp', 'metric', 'value', 'unit']
        self.metrics_collector = MetricsCollector()

    async def get_performance_metrics(self) -> List[Dict]:
        """Get current system performance metrics"""
        try:
            # Get metrics from collector
            metrics = await self.metrics_collector.get_performance_metrics()
            
            # Format metrics
            formatted_metrics = []
            timestamp = datetime.now().isoformat()
            
            for metric in metrics:
                formatted_metrics.append({
                    'name': metric['name'],
                    'value': metric['value'],
                    'unit': metric.get('unit', ''),
                    'timestamp': timestamp,
                    'metadata': metric.get('metadata', {})
                })
                
            return formatted_metrics
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return []

    def process_metrics(self, raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Process raw metrics data into a DataFrame"""
        try:
            metrics = []
            
            for item in raw_data:
                if isinstance(item, str):
                    try:
                        item = json.loads(item)
                    except json.JSONDecodeError:
                        continue

                if not isinstance(item, dict):
                    continue

                # Extract basic metric information
                metric = {
                    'timestamp': item.get('timestamp', datetime.now().isoformat()),
                    'metric': item.get('name', 'unknown'),
                    'value': item.get('value', 0.0),
                    'unit': item.get('unit', ''),
                    'metadata': item.get('metadata', {})
                }

                # Convert timestamp if it's a Unix timestamp
                if isinstance(metric['timestamp'], (int, float)):
                    metric['timestamp'] = datetime.fromtimestamp(
                        metric['timestamp']
                    ).isoformat()

                metrics.append(metric)

            # Convert to DataFrame
            if not metrics:
                return pd.DataFrame(columns=self.required_columns)

            df = pd.DataFrame(metrics)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            return df

        except Exception as e:
            logger.error(f"Error processing metrics: {e}")
            return pd.DataFrame(columns=self.required_columns)

    def get_statistics(self, df: pd.DataFrame) -> Dict:
        """Calculate statistics for metrics"""
        try:
            if df.empty:
                return {}

            stats = {}
            for metric in df['metric'].unique():
                metric_data = df[df['metric'] == metric]
                stats[metric] = {
                    'count': len(metric_data),
                    'mean': float(metric_data['value'].mean()),
                    'std': float(metric_data['value'].std()),
                    'min': float(metric_data['value'].min()),
                    'max': float(metric_data['value'].max()),
                    'last_value': float(metric_data['value'].iloc[-1]),
                    'last_update': metric_data['timestamp'].max().isoformat()
                }

            return stats

        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            return {}