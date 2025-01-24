from typing import Dict, List, Union
from collections import defaultdict
import json
from datetime import datetime

class TrendAnalyzer:
    def analyze_trends(self, logs: List[Union[Dict, str]]) -> Dict:
        trends = defaultdict(lambda: defaultdict(int))
        for log in logs:
            if isinstance(log, dict):
                self._process_log_dict(log, trends)
            else:
                self._process_log_str(log, trends)
        return {k: dict(v) for k, v in trends.items()}

    def calculate_stats(self, logs: List[Union[Dict, str]]) -> Dict:
        if not logs:
            return self._get_empty_stats()

        severity_dist = self._calculate_severity_distribution(logs)
        
        return {
            'total_logs': len(logs),
            'error_rate': self._calculate_error_rate(logs),
            'unique_components': self._count_unique_components(logs),
            'time_span': self._calculate_time_span(logs),
            'severity_distribution': severity_dist
        }

    def _process_log_dict(self, log: Dict, trends: Dict) -> None:
        if timestamp := log.get('timestamp'):
            hour = timestamp.split('T')[1][:2] if 'T' in timestamp else '00'
            trends['temporal_distribution'][hour] += 1

        if component := log.get('labels', {}).get('component'):
            trends['component_distribution'][component] += 1

        message = self._normalize_message(log.get('message', ''))
        self._process_message_severity(message, trends)

    def _process_log_str(self, log: str, trends: Dict) -> None:
        message = str(log)
        self._process_message_severity(message, trends)
        trends['temporal_distribution']['unknown'] += 1

    def _process_message_severity(self, message: str, trends: Dict) -> None:
        message_lower = message.lower()
        if 'error' in message_lower:
            trends['severity_distribution']['error'] += 1
        elif 'warn' in message_lower:
            trends['severity_distribution']['warning'] += 1
        else:
            trends['severity_distribution']['info'] += 1

    def _calculate_severity_distribution(self, logs: List[Union[Dict, str]]) -> Dict[str, int]:
        distribution = {'error': 0, 'warning': 0, 'info': 0}
        
        for log in logs:
            message = (log.get('message', '') if isinstance(log, dict) else str(log)).lower()
            if 'error' in message:
                distribution['error'] += 1
            elif 'warn' in message:
                distribution['warning'] += 1
            else:
                distribution['info'] += 1
                
        return distribution

    def _calculate_error_rate(self, logs: List[Union[Dict, str]]) -> float:
        error_count = 0
        for log in logs:
            message = log.get('message', '') if isinstance(log, dict) else str(log)
            if 'error' in self._normalize_message(message).lower():
                error_count += 1
        return error_count / len(logs) if logs else 0

    def _count_unique_components(self, logs: List[Union[Dict, str]]) -> int:
        components = set()
        for log in logs:
            if isinstance(log, dict):
                component = log.get('labels', {}).get('component')
                if component:
                    components.add(component)
        return len(components)

    def _calculate_time_span(self, logs: List[Union[Dict, str]]) -> Dict:
        timestamps = []
        for log in logs:
            if isinstance(log, dict) and 'timestamp' in log:
                timestamps.append(log['timestamp'])
        return {
            'start': min(timestamps) if timestamps else None,
            'end': max(timestamps) if timestamps else None
        }

    def _normalize_message(self, message: any) -> str:
        if isinstance(message, dict):
            return json.dumps(message)
        return str(message)

    def _get_empty_stats(self) -> Dict:
        return {
            'total_logs': 0,
            'error_rate': 0,
            'unique_components': 0,
            'time_span': {'start': None, 'end': None},
            'severity_distribution': {'error': 0, 'warning': 0, 'info': 0}
        }