from typing import Dict, Optional
from datetime import datetime
import os
import json
import joblib
import logging
from src.models.metric_model import MetricProphetModel
from src.config.settings import settings

logger = logging.getLogger(__name__)

class MetricModelRegistry:
    def __init__(self):
        self.model_dir = settings.METRIC_CONFIG['model_dir']
        self._ensure_model_dir()
        self.models: Dict[str, MetricProphetModel] = {}

    def _ensure_model_dir(self):
        """Create model directory if it doesn't exist"""
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
            logger.info(f"Created model directory: {self.model_dir}")

    def _get_model_path(self, metric_type: str) -> str:
        """Get path for model file"""
        return os.path.join(self.model_dir, f"{metric_type}_model.joblib")

    def _get_metadata_path(self, metric_type: str) -> str:
        """Get path for model metadata file"""
        return os.path.join(self.model_dir, f"{metric_type}_metadata.json")

    async def save_model(
        self,
        metric_type: str,
        model: MetricProphetModel,
        metadata: Dict
    ) -> bool:
        """Save model and metadata to disk"""
        try:
            # Save model
            model_path = self._get_model_path(metric_type)
            joblib.dump(model, model_path)

            # Update metadata
            metadata.update({
                'last_trained': datetime.now().isoformat(),
                'model_path': model_path
            })

            # Save metadata
            metadata_path = self._get_metadata_path(metric_type)
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            # Update in-memory cache
            self.models[metric_type] = model

            logger.info(f"Saved model for {metric_type}")
            return True

        except Exception as e:
            logger.error(f"Error saving model {metric_type}: {e}")
            return False

    async def load_model(self, metric_type: str) -> Optional[MetricProphetModel]:
        """Load model from disk or memory"""
        try:
            # Check in-memory cache
            if metric_type in self.models:
                return self.models[metric_type]

            # Load from disk
            model_path = self._get_model_path(metric_type)
            if not os.path.exists(model_path):
                logger.warning(f"No model found for {metric_type}")
                return None

            model = joblib.load(model_path)
            
            # Update cache
            self.models[metric_type] = model
            
            return model

        except Exception as e:
            logger.error(f"Error loading model {metric_type}: {e}")
            return None

    async def get_model_info(self, metric_type: str) -> Optional[Dict]:
        """Get model metadata"""
        try:
            metadata_path = self._get_metadata_path(metric_type)
            if not os.path.exists(metadata_path):
                return None

            with open(metadata_path, 'r') as f:
                return json.load(f)

        except Exception as e:
            logger.error(f"Error loading model info for {metric_type}: {e}")
            return None

    async def delete_model(self, metric_type: str) -> bool:
        """Delete model and metadata"""
        try:
            # Remove from cache
            self.models.pop(metric_type, None)

            # Delete files
            model_path = self._get_model_path(metric_type)
            metadata_path = self._get_metadata_path(metric_type)

            if os.path.exists(model_path):
                os.remove(model_path)
            if os.path.exists(metadata_path):
                os.remove(metadata_path)

            return True

        except Exception as e:
            logger.error(f"Error deleting model {metric_type}: {e}")
            return False

    async def list_models(self) -> Dict[str, Dict]:
        """List all available models and their metadata"""
        models = {}
        try:
            for file in os.listdir(self.model_dir):
                if file.endswith('_metadata.json'):
                    metric_type = file.replace('_metadata.json', '')
                    if info := await self.get_model_info(metric_type):
                        models[metric_type] = info

            return models

        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return {}