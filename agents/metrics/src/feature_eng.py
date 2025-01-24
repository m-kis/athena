from typing import Dict, List, Union
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from scipy import stats
import json

logger = logging.getLogger(__name__)

class MetricFeatureProcessor:
    def __init__(self):
        self.required_columns = ['timestamp', 'value', 'metric']
        
    # src/agents/metrics/feature_eng.py

    def process_context(self, context: List[Dict]) -> pd.DataFrame:
        """Convert context data to DataFrame and process features"""
        try:
            if not context:
                logger.warning("Empty context provided")
                return pd.DataFrame(columns=self.required_columns)

            logger.debug(f"Processing context with {len(context)} items")
            
            metrics_data = []
            for item in context:
                try:
                    # Handle string items by trying to parse as JSON
                    if isinstance(item, str):
                        try:
                            item = json.loads(item)
                        except json.JSONDecodeError:
                            logger.debug(f"Skipping non-JSON string item: {item[:100]}...")
                            continue

                    # Extract timestamp
                    timestamp = None
                    if isinstance(item, dict):
                        timestamp = (
                            item.get('timestamp') or 
                            item.get('metadata', {}).get('timestamp') or
                            datetime.now().isoformat()
                        )
                    
                    # Extract metrics based on item type
                    if isinstance(item, dict):
                        # Try different metric locations
                        metrics = (
                            item.get('metrics') or 
                            item.get('data', {}).get('metrics') or
                            {'value': item.get('value')} if 'value' in item else None
                        )
                        
                        if metrics:
                            if isinstance(metrics, dict):
                                for name, value in metrics.items():
                                    if isinstance(value, (int, float)):
                                        metrics_data.append({
                                            'timestamp': timestamp,
                                            'value': float(value),
                                            'metric': name
                                        })
                            elif isinstance(metrics, list):
                                metrics_data.extend([{
                                    'timestamp': timestamp,
                                    'value': float(m['value']),
                                    'metric': m['name']
                                } for m in metrics if 'value' in m and 'name' in m])
                                
                except Exception as e:
                    logger.warning(f"Error processing context item: {e}")
                    continue

            if not metrics_data:
                logger.warning("No valid metrics found in context")
                return pd.DataFrame(columns=self.required_columns)

            df = pd.DataFrame(metrics_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            return df
            
        except Exception as e:
            logger.error(f"Error processing metric features: {e}")
            return pd.DataFrame(columns=self.required_columns)
    def calculate_trends(self, data: pd.DataFrame) -> Dict:
        """Calculate trends for each metric"""
        trends = {}
        
        for metric in data['metric'].unique():
            metric_data = data[data['metric'] == metric]
            
            if len(metric_data) < 2:
                continue
                
            try:
                # Calculate trend using linear regression
                x = np.arange(len(metric_data))
                y = metric_data['value'].values
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                
                # Determine trend direction and confidence
                direction = 'increasing' if slope > 0 else 'decreasing'
                confidence = abs(r_value)
                
                trends[metric] = {
                    'direction': direction,
                    'slope': float(slope),
                    'confidence': float(confidence),
                    'p_value': float(p_value),
                    'std_err': float(std_err)
                }
                
            except Exception as e:
                logger.error(f"Error calculating trend for {metric}: {e}")
                continue
                
        return trends

    def calculate_stats(self, data: pd.DataFrame) -> Dict:
        """Calculate statistics for each metric"""
        stats = {}
        
        for metric in data['metric'].unique():
            metric_data = data[data['metric'] == metric]
            
            try:
                # Basic statistics
                basic_stats = metric_data['value'].describe()
                
                # Add additional statistics
                stats[metric] = {
                    'mean': float(basic_stats['mean']),
                    'std': float(basic_stats['std']),
                    'min': float(basic_stats['min']),
                    'max': float(basic_stats['max']),
                    'current': float(metric_data['value'].iloc[-1]),
                    'samples': int(len(metric_data)),
                    'last_update': metric_data['timestamp'].max().isoformat()
                }
                
                # Calculate rate of change
                if len(metric_data) > 1:
                    rate_of_change = (
                        metric_data['value'].diff() / 
                        metric_data['timestamp'].diff().dt.total_seconds()
                    ).mean()
                    stats[metric]['rate_of_change'] = float(rate_of_change)
                    
            except Exception as e:
                logger.error(f"Error calculating stats for {metric}: {e}")
                continue
                
        return stats

    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add time-based features"""
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        df['is_business_hour'] = df['hour'].between(9, 17).astype(int)
        return df

    def _add_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add rolling window features"""
        if len(df) < 2:
            return df
            
        windows = [5, 15, 30]  # minutes
        
        for window in windows:
            df[f'rolling_mean_{window}m'] = (
                df.groupby('metric')['value']
                .rolling(window, min_periods=1)
                .mean()
                .reset_index(0, drop=True)
            )
            
            df[f'rolling_std_{window}m'] = (
                df.groupby('metric')['value']
                .rolling(window, min_periods=1)
                .std()
                .fillna(0)
                .reset_index(0, drop=True)
            )
            
        return df