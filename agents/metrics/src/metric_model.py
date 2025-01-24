import pandas as pd
import numpy as np
from prophet import Prophet
from typing import Dict, Tuple
import logging
from datetime import datetime, timedelta
import joblib
import os

logger = logging.getLogger(__name__)

class MetricModel:
    def __init__(self, model_dir: str = "models/metrics"):
        self.model_dir = model_dir
        self.models: Dict[str, Prophet] = {}
        self._ensure_model_dir()
        
    def _ensure_model_dir(self):
        """Create model directory if it doesn't exist"""
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
            
    def train(
        self,
        data: pd.DataFrame,
        metric_name: str,
        seasonality_mode: str = 'additive',
        changepoint_prior_scale: float = 0.05
    ) -> Tuple[Prophet, Dict]:
        """Train Prophet model for a specific metric"""
        try:
            # Prepare data for Prophet
            df = pd.DataFrame({
                'ds': data['timestamp'],
                'y': data['value']
            })
            
            # Initialize and train model
            model = Prophet(
                seasonality_mode=seasonality_mode,
                changepoint_prior_scale=changepoint_prior_scale,
                weekly_seasonality=True,
                daily_seasonality=True
            )
            
            model.fit(df)
            
            # Save model
            model_path = os.path.join(self.model_dir, f"{metric_name}.joblib")
            joblib.dump(model, model_path)
            
            # Save model in memory
            self.models[metric_name] = model
            
            # Calculate model metrics
            metrics = self._calculate_model_metrics(model, df)
            
            return model, metrics
            
        except Exception as e:
            logger.error(f"Error training model for {metric_name}: {e}")
            raise
            
    def predict(
        self,
        model: Prophet,
        periods: int = 24,
        freq: str = 'H',
        return_components: bool = True
    ) -> Dict:
        """Generate predictions using trained model"""
        try:
            # Create future dataframe
            future = model.make_future_dataframe(
                periods=periods,
                freq=freq
            )
            
            # Generate predictions
            forecast = model.predict(future)
            
            result = {
                'predictions': forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']],
                'last_predicted': forecast['ds'].max(),
                'confidence_interval': (
                    forecast['yhat_upper'] - forecast['yhat_lower']
                ).mean()
            }
            
            if return_components:
                components = ['trend', 'weekly', 'daily']
                for component in components:
                    if component in forecast.columns:
                        result[f'{component}_component'] = forecast[component]
                        
            return result
            
        except Exception as e:
            logger.error(f"Error generating predictions: {e}")
            raise
            
    def load_model(self, metric_name: str) -> Prophet:
        """Load trained model from disk"""
        try:
            if metric_name in self.models:
                return self.models[metric_name]
                
            model_path = os.path.join(self.model_dir, f"{metric_name}.joblib")
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"No trained model found for {metric_name}")
                
            model = joblib.load(model_path)
            self.models[metric_name] = model
            return model
            
        except Exception as e:
            logger.error(f"Error loading model for {metric_name}: {e}")
            raise
            
    def _calculate_model_metrics(self, model: Prophet, df: pd.DataFrame) -> Dict:
        """Calculate model performance metrics"""
        try:
            # Generate predictions for training data
            forecast = model.predict(df)
            
            # Calculate metrics
            mse = np.mean((df['y'] - forecast['yhat'])**2)
            rmse = np.sqrt(mse)
            mae = np.mean(np.abs(df['y'] - forecast['yhat']))
            
            # Calculate R-squared
            ss_res = np.sum((df['y'] - forecast['yhat'])**2)
            ss_tot = np.sum((df['y'] - df['y'].mean())**2)
            r_squared = 1 - (ss_res / ss_tot)
            
            return {
                'mse': mse,
                'rmse': rmse,
                'mae': mae,
                'r_squared': r_squared
            }
            
        except Exception as e:
            logger.error(f"Error calculating model metrics: {e}")
            raise
            
    def delete_model(self, metric_name: str) -> bool:
        """Delete model from disk and memory"""
        try:
            model_path = os.path.join(self.model_dir, f"{metric_name}.joblib")
            if os.path.exists(model_path):
                os.remove(model_path)
                
            if metric_name in self.models:
                del self.models[metric_name]
                
            return True
            
        except Exception as e:
            logger.error(f"Error deleting model for {metric_name}: {e}")
            return False