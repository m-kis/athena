import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func, and_
from src.models.metric_model import MetricProphetModel
from src.models.db_models import metrics as Metric
from .data_loader import MetricDataLoader
from src.config.settings import settings
from .model_registry import MetricModelRegistry
from dotenv import load_dotenv
import os 
logger = logging.getLogger(__name__)

class MetricModelTrainer:
    def __init__(self):
        try:
            db_url = settings.get_database_url()
            if not db_url:
                raise ValueError("Database URL not configured")
                
            self.engine = create_engine(db_url)
            logger.info("MetricModelTrainer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise RuntimeError(f"Database connection failed: {e}") from e
        
        self.data_loader = MetricDataLoader()
        self.model_registry = MetricModelRegistry()
        self.training_lock = asyncio.Lock()
        self.metrics_to_train = [
            'cpu_usage',
            'memory_usage',
            'disk_usage'
        ]
        self.engine = create_engine(os.getenv('DATABASE_URL'))

    def get_session(self):
        return Session(self.engine)

    async def train_all_models(
        self,
        force: bool = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Dict]:
        """Train all metric models"""
        results = {}
        
        for metric_type in self.metrics_to_train:
            try:
                result = await self.train_model(
                    metric_type,
                    force=force,
                    start_date=start_date,
                    end_date=end_date
                )
                results[metric_type] = result
            except Exception as e:
                logger.error(f"Error training model for {metric_type}: {e}")
                results[metric_type] = {
                    'status': 'error',
                    'error': str(e)
                }

        return results

    async def train_model(
        self,
        metric_type: str,
        force: bool = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Train model for specific metric type"""
        async with self.training_lock:
            try:
                # Check if we need to train
                if not force and not await self._should_train(metric_type):
                    logger.info(f"Skipping training for {metric_type} - model is up to date")
                    return {
                        'status': 'skipped',
                        'reason': 'model up to date'
                    }

                # Load training data
                df = await self.data_loader.load_training_data(
                    metric_type,
                    start_date=start_date,
                    end_date=end_date
                )

                if not self.data_loader.validate_data(df):
                    return {
                        'status': 'error',
                        'error': 'Invalid training data'
                    }

                # Initialize and train model
                model = MetricProphetModel()
                training_result = model.train(df)

                if training_result['status'] != 'success':
                    return training_result

                # Save model
                save_result = await self.model_registry.save_model(
                    metric_type,
                    model,
                    metadata=training_result
                )

                if not save_result:
                    return {
                        'status': 'error',
                        'error': 'Failed to save model'
                    }

                return {
                    'status': 'success',
                    'metrics': training_result['metrics'],
                    'training_info': {
                        'timestamp': datetime.now().isoformat(),
                        'samples': len(df),
                        'data_range': {
                            'start': df['timestamp'].min().isoformat(),
                            'end': df['timestamp'].max().isoformat()
                        }
                    }
                }

            except Exception as e:
                logger.error(f"Error in model training: {e}")
                return {
                    'status': 'error',
                    'error': str(e)
                }

    async def _should_train(self, metric_type: str) -> bool:
        """Determine if model needs training"""
        try:
            model_info = await self.model_registry.get_model_info(metric_type)
            
            # If no model exists
            if not model_info:
                return True
                
            last_trained = datetime.fromisoformat(model_info['last_trained'])
            training_frequency = timedelta(hours=model_info.get('training_frequency_hours', 24))
            
            # Check data volume since last training
            new_data_count = await self._get_new_data_count(metric_type, last_trained)
            min_new_samples = model_info.get('min_new_samples', 100)
            
            return (
                datetime.now() - last_trained > training_frequency and
                new_data_count >= min_new_samples
            )
        except Exception:
            return False

    async def _get_new_data_count(self, metric_type: str, since: datetime) -> int:
        """Count new data points since last training"""
        with self.get_session() as session:
            count = session.query(func.count()).filter(
                and_(
                    Metric.metric_name == metric_type,
                    Metric.timestamp > since
                )
            ).scalar()
            return count or 0
    async def start_periodic_training(self, interval_hours: int = 24):
        """Start periodic training of all models"""
        while True:
            try:
                logger.info("Starting periodic model training")
                await self.train_all_models()
                
            except Exception as e:
                logger.error(f"Error in periodic training: {e}")
                
            finally:
                # Wait for next training interval
                await asyncio.sleep(interval_hours * 3600)