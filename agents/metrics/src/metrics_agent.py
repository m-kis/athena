from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from src.agents.base_agent import BaseAgent
from src.monitoring.metrics_collector import metrics_collector

logger = logging.getLogger(__name__)

class MetricAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.metrics_collector = metrics_collector
        self.thresholds = {
            'cpu_usage': {'warning': 70, 'critical': 85},
            'memory_usage': {'warning': 80, 'critical': 90},
            'disk_usage': {'warning': 85, 'critical': 95}
        }

    async def _analyze_impl(
        self,
        query: str,
        context: List[Dict],
        time_window: timedelta,
        nlu_context: Optional[Dict] = None
    ) -> Dict:
        try:
            # Collecter les métriques
            metrics = await self.metrics_collector.get_performance_metrics()
            
            if not metrics:
                return self._get_empty_response("Unable to collect system metrics")

            # Analyser en fonction du type de requête
            if 'cpu' in query.lower():
                return await self.analyze_cpu(metrics)
            elif 'memory' in query.lower():
                return await self.analyze_memory(metrics)
            elif 'disk' in query.lower():
                return await self.analyze_disk(metrics)
            else:
                return await self.analyze_all(metrics)

        except Exception as e:
            logger.error(f"Error in metric analysis: {e}")
            return self._get_empty_response(str(e))

    async def analyze_cpu(self, metrics: List[Dict]) -> Dict:
        cpu_metrics = [m for m in metrics if m['name'] == 'cpu_usage']
        if not cpu_metrics:
            return self._get_empty_response("No CPU metrics available")

        current_cpu = cpu_metrics[0]
        processes = await self._get_top_processes()
        peak_usage = current_cpu['value']
        status = self._determine_status('cpu_usage', peak_usage)

        return {
            "summary": f"CPU usage is {current_cpu['value']}% ({status['state']})",
            "current_status": {
                "state": status['state'],
                "value": current_cpu['value'],
                "trend": "stable"  # To be implemented with historical data
            },
            "key_findings": [
                f"Current CPU load is {current_cpu['value']}%",
                f"System has {current_cpu['metadata']['cores']} cores available",
                "Resource distribution normal across cores"
            ],
            "action_items": self._generate_cpu_actions(status, current_cpu),
            "context": {
                "peak_usage_last_hour": peak_usage,
                "highest_consuming_processes": processes,
                "metrics": cpu_metrics
            }
        }

    def _determine_status(self, metric_type: str, value: float) -> Dict:
        thresholds = self.thresholds.get(metric_type, {'warning': 70, 'critical': 85})
        
        if value >= thresholds['critical']:
            return {
                'state': 'critical',
                'level': 3,
                'requires_action': True
            }
        elif value >= thresholds['warning']:
            return {
                'state': 'warning',
                'level': 2,
                'requires_action': True
            }
        return {
            'state': 'healthy',
            'level': 1,
            'requires_action': False
        }

    async def _get_top_processes(self, limit: int = 5) -> List[Dict]:
        metrics = await self.metrics_collector.get_performance_metrics()
        processes = []
        
        for metric in metrics:
            if metric.get('metadata', {}).get('process_name'):
                processes.append({
                    'name': metric['metadata']['process_name'],
                    'cpu_percent': metric['metadata'].get('cpu_percent', 0),
                    'pid': metric['metadata'].get('pid')
                })
                
        return sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:limit]

    def _generate_cpu_actions(self, status: Dict, metric: Dict) -> List[Dict]:
        actions = []
        
        if status['requires_action']:
            if status['state'] == 'critical':
                actions.append({
                    "priority": "high",
                    "description": "CPU usage critically high - immediate action required",
                    "command": "top -b -n 1",
                    "details": "Check and potentially terminate resource-intensive processes"
                })
            elif status['state'] == 'warning':
                actions.append({
                    "priority": "medium",
                    "description": "CPU usage high - monitor closely",
                    "command": "htop",
                    "details": "Monitor system performance and identify resource-intensive processes"
                })
        else:
            actions.append({
                "priority": "low",
                "description": "System CPU usage normal",
                "command": "top -b -n 1",
                "details": "Routine monitoring recommended"
            })
            
        return actions

    def _get_empty_response(self, message: str) -> Dict:
        return {
            "summary": message,
            "current_status": {
                "state": "unknown",
                "value": None,
                "trend": None
            },
            "key_findings": [],
            "action_items": [],
            "context": {}
        }