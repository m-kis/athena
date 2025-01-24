import psutil
import time
from typing import Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MetricsCollector:
    def __init__(self):
        self._last_cpu_times = psutil.cpu_times()
        self._last_collect_time = time.time()

    async def get_performance_metrics(self) -> List[Dict]:
        try:
            metrics = []
            
            # CPU Metrics
            cpu_metrics = self._collect_cpu_metrics()
            metrics.extend(cpu_metrics)
            
            # Memory Metrics
            memory_metrics = self._collect_memory_metrics()
            metrics.extend(memory_metrics)
            
            # Disk Metrics
            disk_metrics = self._collect_disk_metrics()
            metrics.extend(disk_metrics)
            
            # Process Metrics
            process_metrics = self._collect_process_metrics()
            metrics.extend(process_metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return []

    def _collect_cpu_metrics(self) -> List[Dict]:
        metrics = []
        timestamp = datetime.now().isoformat()

        # Overall CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        metrics.append({
            'name': 'cpu_usage',
            'value': cpu_percent,
            'unit': '%',
            'timestamp': timestamp,
            'metadata': {
                'cores': psutil.cpu_count(),
                'physical_cores': psutil.cpu_count(logical=False)
            }
        })

        # Per-core CPU usage
        per_cpu = psutil.cpu_percent(interval=1, percpu=True)
        for i, usage in enumerate(per_cpu):
            metrics.append({
                'name': f'cpu_core_{i}_usage',
                'value': usage,
                'unit': '%',
                'timestamp': timestamp,
                'metadata': {
                    'core_id': i
                }
            })

        # CPU frequency
        freq = psutil.cpu_freq(percpu=False)
        if freq:
            metrics.append({
                'name': 'cpu_frequency',
                'value': freq.current,
                'unit': 'MHz',
                'timestamp': timestamp,
                'metadata': {
                    'min': freq.min,
                    'max': freq.max
                }
            })

        return metrics

    def _collect_memory_metrics(self) -> List[Dict]:
        timestamp = datetime.now().isoformat()
        memory = psutil.virtual_memory()
        
        return [{
            'name': 'memory_usage',
            'value': memory.percent,
            'unit': '%',
            'timestamp': timestamp,
            'metadata': {
                'total_bytes': memory.total,
                'available_bytes': memory.available,
                'used_bytes': memory.used,
                'free_bytes': memory.free,
                'cached_bytes': getattr(memory, 'cached', 0),
                'shared_bytes': getattr(memory, 'shared', 0)
            }
        }]

    def _collect_disk_metrics(self) -> List[Dict]:
        metrics = []
        timestamp = datetime.now().isoformat()

        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                metrics.append({
                    'name': 'disk_usage',
                    'value': usage.percent,
                    'unit': '%',
                    'timestamp': timestamp,
                    'metadata': {
                        'mountpoint': partition.mountpoint,
                        'filesystem': partition.fstype,
                        'total_bytes': usage.total,
                        'used_bytes': usage.used,
                        'free_bytes': usage.free
                    }
                })
            except Exception:
                continue

        return metrics

    def _collect_process_metrics(self, top_n: int = 5) -> List[Dict]:
        metrics = []
        timestamp = datetime.now().isoformat()

        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.as_dict(attrs=['pid', 'name', 'cpu_percent', 'memory_percent'])
                processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by CPU usage
        top_cpu_processes = sorted(processes, 
                                 key=lambda x: x['cpu_percent'] or 0, 
                                 reverse=True)[:top_n]

        for proc in top_cpu_processes:
            metrics.append({
                'name': f'process_{proc["name"]}',
                'value': proc['cpu_percent'] or 0,
                'unit': '%',
                'timestamp': timestamp,
                'metadata': {
                    'pid': proc['pid'],
                    'process_name': proc['name'],
                    'cpu_percent': proc['cpu_percent'] or 0,
                    'memory_percent': proc['memory_percent'] or 0
                }
            })

        return metrics

metrics_collector = MetricsCollector()
