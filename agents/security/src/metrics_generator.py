from datetime import datetime
from typing import Dict, List

# src/agents/security/metrics_generator.py
class SecurityMetricsGenerator:
    def generate_metrics(self, stats: Dict) -> List[Dict]:
        """Generate security metrics"""
        metrics = []
        timestamp = datetime.now().isoformat()
        
        metrics.append({
            'name': 'security_issues_total',
            'value': stats['total_issues'],
            'timestamp': timestamp
        })
        
        for severity, count in stats['by_severity'].items():
            metrics.append({
                'name': f'security_issues_{severity}',
                'value': count,
                'timestamp': timestamp
            })
            
        for issue_type, count in stats['by_type'].items():
            metrics.append({
                'name': f'security_issues_{issue_type}',
                'value': count,
                'timestamp': timestamp
            })
        
        return metrics