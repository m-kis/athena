from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from prophet import Prophet
from src.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class MetricAnalysisService:
    def __init__(self):
        self.models: Dict[str, Prophet] = {}
        self.thresholds = settings.METRIC_THRESHOLDS
        self.config = settings.METRIC_CONFIG
        
    async def analyze_metrics(
        self,
        metrics: List[Dict],
        prediction_horizon: int = 24
    ) -> Dict:
        """Analyze metrics and generate predictions/anomalies"""
        try:
            # Group metrics by type
            metric_groups = self._group_metrics(metrics)
            
            results = {
                'predictions': {},
                'anomalies': [],
                'trends': {},
                'correlations': {},
                'summary': {
                    'analyzed_metrics': len(metric_groups),
                    'timestamp': datetime.now().isoformat()
                }
            }

            for metric_type, metric_data in metric_groups.items():
                if len(metric_data) < self.config['min_training_samples']:
                    continue

                # Train/update model
                model = await self._get_or_train_model(metric_type, metric_data)
                
                # Generate predictions
                predictions = self._generate_predictions(model, prediction_horizon)
                results['predictions'][metric_type] = predictions

                # Detect anomalies
                anomalies = self._detect_anomalies(
                    metric_data, 
                    predictions,
                    self.thresholds.get(metric_type, self.thresholds['default'])
                )
                results['anomalies'].extend(anomalies)

                # Calculate trends
                results['trends'][metric_type] = self._analyze_trends(metric_data, predictions)

            # Calculate correlations between metrics
            results['correlations'] = self._calculate_correlations(metric_groups)

            return results

        except Exception as e:
            logger.error(f"Error in metric analysis: {e}")
            return {
                'predictions': {},
                'anomalies': [],
                'trends': {},
                'correlations': {}
            }

    def _group_metrics(self, metrics: List[Dict]) -> Dict[str, List[Dict]]:
        """Group metrics by type"""
        groups = {}
        for metric in metrics:
            metric_type = metric.get('name', 'unknown')
            if metric_type not in groups:
                groups[metric_type] = []
            groups[metric_type].append(metric)
        return groups

    async def _get_or_train_model(
        self, 
        metric_type: str,
        data: List[Dict]
    ) -> Prophet:
        """Get existing model or train new one"""
        if metric_type not in self.models:
            model = Prophet(**settings.PROPHET_CONFIG)
            
            # Prepare training data
            df = pd.DataFrame(data)
            df['ds'] = pd.to_datetime(df['timestamp'])
            df['y'] = df['value']
            
            model.fit(df)
            self.models[metric_type] = model
            
        return self.models[metric_type]

    def _generate_predictions(
        self,
        model: Prophet,
        horizon: int
    ) -> Dict:
        """Generate predictions using Prophet model"""
        future = model.make_future_dataframe(periods=horizon, freq='H')
        forecast = model.predict(future)
        
        return {
            'values': forecast['yhat'].tail(horizon).values.tolist(),
            'timestamps': [ts.isoformat() for ts in forecast['ds'].tail(horizon)],
            'lower_bounds': forecast['yhat_lower'].tail(horizon).values.tolist(),
            'upper_bounds': forecast['yhat_upper'].tail(horizon).values.tolist(),
            'components': {
                'trend': forecast['trend'].tail(horizon).values.tolist(),
                'seasonality': forecast['weekly'].tail(horizon).values.tolist() if 'weekly' in forecast else None
            }
        }

    def _detect_anomalies(
        self,
        data: List[Dict],
        predictions: Dict,
        threshold: float
    ) -> List[Dict]:
        """Detect anomalies using multiple methods"""
        anomalies = []
        
        # Method 1: Threshold-based detection
        actual_values = [d['value'] for d in data]
        for i, value in enumerate(actual_values):
            if value > threshold:
                anomalies.append({
                    'type': 'threshold',
                    'timestamp': data[i]['timestamp'],
                    'value': value,
                    'threshold': threshold,
                    'severity': self._calculate_severity(value, threshold)
                })

        # Method 2: Statistical detection (z-score)
        mean_val = np.mean(actual_values)
        std_val = np.std(actual_values)
        z_threshold = 3.0
        
        for i, value in enumerate(actual_values):
            z_score = abs((value - mean_val) / std_val) if std_val > 0 else 0
            if z_score > z_threshold:
                anomalies.append({
                    'type': 'statistical',
                    'timestamp': data[i]['timestamp'],
                    'value': value,
                    'z_score': z_score,
                    'severity': 'high' if z_score > 4 else 'medium'
                })

        # Method 3: Forecast-based detection
        if predictions['values']:
            for i, (actual, predicted, lower, upper) in enumerate(zip(
                actual_values[-len(predictions['values']):],
                predictions['values'],
                predictions['lower_bounds'],
                predictions['upper_bounds']
            )):
                if actual < lower or actual > upper:
                    anomalies.append({
                        'type': 'forecast',
                        'timestamp': data[i]['timestamp'],
                        'value': actual,
                        'predicted': predicted,
                        'bounds': {'lower': lower, 'upper': upper},
                        'severity': 'high' if abs(actual - predicted) > 2 * (upper - lower) else 'medium'
                    })

        return anomalies

    def _analyze_trends(
        self,
        data: List[Dict],
        predictions: Dict
    ) -> Dict:
        """Analyze metric trends"""
        values = [d['value'] for d in data]
        
        # Calculate trend direction and strength
        slope, trend_strength = self._calculate_trend(values)
        
        # Detect seasonality
        seasonality = self._detect_seasonality(values)
        
        # Calculate rate of change
        rate_of_change = self._calculate_rate_of_change(values)
        
        return {
            'direction': 'increasing' if slope > 0 else 'decreasing',
            'strength': trend_strength,
            'seasonality': seasonality,
            'rate_of_change': rate_of_change,
            'stability': 1.0 - min(1.0, np.std(values) / (np.mean(values) if np.mean(values) != 0 else 1))
        }

    def _calculate_correlations(
        self,
        metric_groups: Dict[str, List[Dict]]
    ) -> Dict[str, List[Dict]]:
        """Calculate correlations between metrics"""
        correlations = {}
        
        metric_types = list(metric_groups.keys())
        for i in range(len(metric_types)):
            for j in range(i + 1, len(metric_types)):
                type1, type2 = metric_types[i], metric_types[j]
                
                values1 = [m['value'] for m in metric_groups[type1]]
                values2 = [m['value'] for m in metric_groups[type2]]
                
                if len(values1) == len(values2) and len(values1) > 1:
                    corr = np.corrcoef(values1, values2)[0, 1]
                    if abs(corr) > 0.7:  # Only keep strong correlations
                        correlations[f"{type1}_vs_{type2}"] = {
                            'coefficient': float(corr),
                            'strength': 'strong' if abs(corr) > 0.8 else 'moderate'
                        }
        
        return correlations

    def _calculate_severity(self, value: float, threshold: float) -> str:
        """Calculate anomaly severity based on threshold deviation"""
        deviation = (value - threshold) / threshold
        if deviation > 0.5:
            return 'critical'
        elif deviation > 0.2:
            return 'high'
        return 'medium'