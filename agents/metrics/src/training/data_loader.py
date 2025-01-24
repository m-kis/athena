from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from src.config.database import get_session
from .prometheus_loader import PrometheusDataLoader

logger = logging.getLogger(__name__)

class MetricDataLoader:
    def __init__(self):
        self.required_columns = ['timestamp', 'value', 'metric']

    async def load_training_data(
        self,
        metric_type: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_samples: int = 24
    ) -> pd.DataFrame:
        """Load historical metric data from Prometheus"""
        try:
            prometheus_loader = PrometheusDataLoader()
            df = await prometheus_loader.load_training_data(
                metric_type=metric_type,
                start_time=start_date,
                end_time=end_date
            )
            with get_session() as session:
                # Query metrics table for historical data
                query = self._build_query(metric_type, start_date, end_date)
                df = pd.read_sql(query, session.bind)

                if len(df) < min_samples:
                    logger.warning(
                        f"Insufficient data for {metric_type}. "
                        f"Got {len(df)} samples, need {min_samples}"
                    )
                    return pd.DataFrame(columns=self.required_columns)

                # Process timestamps
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Sort by timestamp
                df = df.sort_values('timestamp')

                return df

        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            return pd.DataFrame(columns=self.required_columns)

    def _build_query(
        self,
        metric_type: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> str:
        """Build SQL query for metric data"""
        query = f"""
            SELECT timestamp, value, '{metric_type}' as metric
            FROM metrics
            WHERE metric_name = '{metric_type}'
        """

        if start_date:
            query += f" AND timestamp >= '{start_date}'"
        if end_date:
            query += f" AND timestamp <= '{end_date}'"

        query += " ORDER BY timestamp"
        return query

    def validate_data(self, df: pd.DataFrame) -> bool:
        """Validate loaded data"""
        if df.empty:
            return False

        # Check required columns
        if not all(col in df.columns for col in self.required_columns):
            return False

        # Check for nulls
        if df[self.required_columns].isnull().any().any():
            return False

        # Check timestamps
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            return False

        # Check values are numeric
        if not pd.api.types.is_numeric_dtype(df['value']):
            return False

        return True

    async def save_metrics(self, metrics: List[Dict]) -> bool:
        """Save new metrics to database"""
        try:
            with get_session() as session:
                # Convert to DataFrame
                df = pd.DataFrame(metrics)
                
                # Write to database
                df.to_sql(
                    'metrics',
                    session.bind,
                    if_exists='append',
                    index=False
                )
                
                session.commit()
                return True

        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
            return False