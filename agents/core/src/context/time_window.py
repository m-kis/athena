from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class TimeWindow:
    """Handle time windows for metrics and logs analysis"""
    
    def __init__(self, default_window: timedelta = timedelta(hours=1)):
        self.default_window = default_window

    def get_time_range(
        self,
        time_window: Optional[timedelta] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Tuple[datetime, datetime]:
        """Calculate time range based on provided parameters"""
        now = datetime.now()
        
        if end_time is None:
            end_time = now
            
        if start_time is not None:
            return start_time, end_time
            
        window = time_window or self.default_window
        start_time = end_time - window
        
        return start_time, end_time

    def to_prometheus_format(self, start_time: datetime, end_time: datetime) -> Dict[str, float]:
        """Convert timestamps for Prometheus"""
        return {
            'start': start_time.timestamp(),
            'end': end_time.timestamp()
        }
        
    def to_loki_format(self, start_time: datetime, end_time: datetime) -> Dict[str, str]:
        """Convert timestamps for Loki"""
        return {
            'start': str(int(start_time.timestamp() * 1e9)),
            'end': str(int(end_time.timestamp() * 1e9))
        }

    def to_human_readable(self, start_time: datetime, end_time: datetime) -> str:
        """Return a human readable representation of the time window"""
        duration = end_time - start_time
        hours = duration.total_seconds() / 3600
        
        if hours < 1:
            minutes = duration.total_seconds() / 60
            return f"last {int(minutes)} minutes"
        elif hours < 24:
            return f"last {int(hours)} hours"
        else:
            days = hours / 24
            return f"last {int(days)} days"

    def validate_range(self, start_time: datetime, end_time: datetime) -> bool:
        """Validate time range"""
        if start_time > end_time:
            logger.error("Start time is after end time")
            return False
            
        if end_time > datetime.now():
            logger.error("End time is in the future")
            return False
            
        max_window = timedelta(days=30)
        if end_time - start_time > max_window:
            logger.error(f"Time window exceeds maximum of {max_window}")
            return False
            
        return True