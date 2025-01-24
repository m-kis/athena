import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta
from .metric_model import MetricModel
from .feature_eng import MetricFeatureProcessor

logger = logging.getLogger(__name__)

class MetricModelTrainer:
    def __init__(self):
        self.model = MetricModel()
        self.feature_processor = MetricFeatureProcessor()
        
    async def train_models(
        self,
        training_data: pd.DataFrame,
        metrics: Optional[List[str]] = None
    ) -> Dict:
        """Train models for specified or all metrics"""
        results = {}
        
        # Process features
        processed_data = self.feature_processor.process_context(training_data)
        
        # Get metrics to train
        if not metrics:
            metrics = processed_data['metric'].unique()
            
        # Train model for each metric
        for metric in metrics:
            try:
                logger.info(f"Training model for metric: {metric}")
                
                metric_data = processed_data[
                    processed_data['metric'] == metric
                ].copy()
                
                if len(metric_data) < 24:  # Minimum data requirement
                    logger.warning(
                        f"Insufficient data for {metric}. "
                        f"Need at least 24 points, got {len(metric_data)}"
                    )
                    continue
                
                # Determine seasonality based on data patterns
                seasonality_mode = self._detect_seasonality_mode(metric_data)
                
                # Train model
                model, metrics = self.model.train(
                    metric_data,
                    metric,
                    seasonality_mode=seasonality_mode
                )
                
                results[metric] = {
                    'status': 'success',
                    'samples': len(metric_data),
                    'metrics': metrics,
                    'seasonality': seasonality_mode
                }
                
            except Exception as e:
                logger.error(f"Error training model for {metric}: {e}")
                results[metric] = {
                    'status': 'error',
                    'error': str(e)
                }
                
        return results
    
    def _detect_seasonality_mode(self, data: pd.DataFrame) -> str:
        """Detect whether to use additive or multiplicative seasonality"""
        try:
            # Calculate rolling statistics
            rolling_mean = data['value'].rolling(
                window=24,
                min_periods=1
            ).mean()
            
            rolling_std = data['value'].rolling(
                window=24,
                min_periods=1
            ).std()
            
            # Calculate correlation between mean and std
            correlation = np.corrcoef(
                rolling_mean[24:],
                rolling_std[24:]
            )[0, 1]
            
            # If strong correlation, use multiplicative
            if abs(correlation) > 0.5:
                return 'multiplicative'
            return 'additive'
            
        except Exception:
            return 'additive'  # Default to additive
    
    def validate_model(
        self,
        model: MetricModel,
        validation_data: pd.DataFrame
    ) -> Dict:
        """Validate model performance"""
        try:
            # Generate predictions
            predictions = model.predict(validation_data)
            
            # Calculate metrics
            mae = np.mean(
                np.abs(
                    validation_data['value'] - 
                    predictions['predictions']['yhat']
                )
            )
            
            rmse = np.sqrt(
                np.mean(
                    np.square(
                        validation_data['value'] - 
                        predictions['predictions']['yhat']
                    )
                )
            )
            
            # Calculate R-squared
            ss_res = np.sum(
                np.square(
                    validation_data['value'] - 
                    predictions['predictions']['yhat']
                )
            )
            ss_tot = np.sum(
                np.square(
                    validation_data['value'] - 
                    validation_data['value'].mean()
                )
            )
            r2 = 1 - (ss_res / ss_tot)
            
            return {
                'mae': mae,
                'rmse': rmse,
                'r2': r2
            }
            
        except Exception as e:
            logger.error(f"Error validating model: {e}")
            return {
                'error': str(e)
            }
    
    def load_training_data(
        self,
        file_path: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Load and preprocess training data"""
        try:
            # Load data
            df = pd.read_csv(file_path)
            
            # Convert timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Filter by date range if specified
            if start_date:
                df = df[df['timestamp'] >= start_date]
            if end_date:
                df = df[df['timestamp'] <= end_date]
                
            return df
            
        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            raise