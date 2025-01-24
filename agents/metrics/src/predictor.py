from typing import Dict, List
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from .metric_model import MetricModel

logger = logging.getLogger(__name__)

class MetricPredictor:
    def __init__(self):
        self.model = MetricModel()
        self.anomaly_threshold = 3.0  # Standard deviations for anomaly detection
        
    async def predict(self, data: pd.DataFrame) -> Dict:
        """Generate predictions for each metric"""
        predictions = {}
        
        for metric in data['metric'].unique():
            try:
                metric_data = data[data['metric'] == metric].copy()
                
                # Load or train model
                try:
                    prophet_model = self.model.load_model(metric)
                except FileNotFoundError:
                    prophet_model, _ = self.model.train(metric_data, metric)
                
                # Generate predictions
                forecast = self.model.predict(
                    prophet_model,
                    periods=24,  # 24 hours ahead
                    freq='H'
                )
                
                # Format predictions
                predictions[metric] = {
                    'timestamp': forecast['last_predicted'],
                    'value': forecast['predictions']['yhat'].iloc[-1],
                    'confidence_interval': forecast['confidence_interval'],
                    'components': {
                        'trend': forecast.get('trend_component', []).iloc[-1],
                        'weekly': forecast.get('weekly_component', []).iloc[-1],
                        'daily': forecast.get('daily_component', []).iloc[-1]
                    }
                }
                
            except Exception as e:
                logger.error(f"Error predicting {metric}: {e}")
                continue
                
        return predictions
    
    def detect_anomalies(
        self,
        data: pd.DataFrame,
        predictions: Dict
    ) -> List[Dict]:
        """Detect anomalies in metric data"""
        anomalies = []
        
        for metric in data['metric'].unique():
            try:
                metric_data = data[data['metric'] == metric].copy()
                
                if len(metric_data) < 2:
                    continue
                    
                # Calculate rolling statistics
                rolling_mean = metric_data['value'].rolling(
                    window=5,
                    min_periods=1
                ).mean()
                
                rolling_std = metric_data['value'].rolling(
                    window=5,
                    min_periods=1
                ).std()
                
                # Z-score based detection
                z_scores = np.abs(
                    (metric_data['value'] - rolling_mean) / rolling_std
                )
                
                # Find anomalies
                anomaly_points = metric_data[
                    z_scores > self.anomaly_threshold
                ].copy()
                
                for _, point in anomaly_points.iterrows():
                    # Determine severity based on z-score
                    z_score = z_scores[point.name]
                    if z_score > 5:
                        severity = 'critical'
                    elif z_score > 4:
                        severity = 'high'
                    else:
                        severity = 'medium'
                    
                    anomalies.append({
                        'metric': metric,
                        'timestamp': point['timestamp'].isoformat(),
                        'value': point['value'],
                        'expected_value': rolling_mean[point.name],
                        'deviation': z_score,
                        'severity': severity
                    })
                    
            except Exception as e:
                logger.error(f"Error detecting anomalies for {metric}: {e}")
                continue
                
        return anomalies
    
    def _calculate_change_points(
        self,
        data: pd.DataFrame,
        window: int = 5
    ) -> List[Dict]:
        """Detect significant change points in metrics"""
        change_points = []
        
        for metric in data['metric'].unique():
            metric_data = data[data['metric'] == metric].copy()
            
            if len(metric_data) < window * 2:
                continue
                
            try:
                # Calculate rolling statistics
                rolling_mean = metric_data['value'].rolling(
                    window=window,
                    min_periods=1
                ).mean()
                
                # Calculate percent change
                pct_change = rolling_mean.pct_change()
                
                # Find significant changes
                significant_changes = metric_data[
                    abs(pct_change) > 0.1  # 10% change threshold
                ].copy()
                
                for _, point in significant_changes.iterrows():
                    change_points.append({
                        'metric': metric,
                        'timestamp': point['timestamp'].isoformat(),
                        'value': point['value'],
                        'change_percentage': pct_change[point.name] * 100
                    })
                    
            except Exception as e:
                logger.error(
                    f"Error calculating change points for {metric}: {e}"
                )
                continue
                
        return change_points