from typing import Dict, List
import re
# src/agents/security/threat_analyzer.py
class ThreatAnalyzer:
    def compute_stats(self, issues: List[Dict]) -> Dict:
        """Compute threat statistics"""
        stats = {
            'total_issues': len(issues),
            'by_type': {},
            'by_severity': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0},
            'unique_ips': set(),
            'temporal_distribution': {}
        }

        for issue in issues:
            # Count by type and severity
            issue_type = issue['type']
            severity = issue['severity']
            stats['by_type'][issue_type] = stats['by_type'].get(issue_type, 0) + 1
            stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1

            # Extract unique IPs
            if ip_match := re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', issue['context']):
                stats['unique_ips'].add(ip_match.group(0))

            # Track temporal distribution
            if timestamp := issue.get('timestamp'):
                hour = timestamp.split('T')[1][:2]
                stats['temporal_distribution'][hour] = stats['temporal_distribution'].get(hour, 0) + 1

        stats['unique_ips'] = list(stats['unique_ips'])
        return stats

    def calculate_risk_level(self, issues: List[Dict], stats: Dict) -> str:
        """Calculate overall risk level"""
        risk_score = 0
        severity_scores = {'critical': 10, 'high': 5, 'medium': 2, 'low': 1}

        # Calculate score based on issues
        for severity, count in stats['by_severity'].items():
            risk_score += severity_scores[severity] * count

        # Adjust based on temporal concentration
        temporal_distribution = stats.get('temporal_distribution', {})
        if len(temporal_distribution) > 0:
            max_issues_per_hour = max(temporal_distribution.values())
            if max_issues_per_hour > 10:
                risk_score *= 1.5

        # Determine risk level
        if risk_score > 50:
            return 'critical'
        elif risk_score > 25:
            return 'high'
        elif risk_score > 10:
            return 'medium'
        return 'low'