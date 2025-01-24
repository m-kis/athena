from typing import Dict, List, Any
import re
from datetime import datetime

class SecurityPatternDetector:
    def __init__(self):
        self.patterns = {
            'auth_failure': r'(?i)(auth.*fail|login.*fail|invalid.*password|access.*denied)',
            'injection': r'(?i)(sql|command|code|script).*injection',
            'suspicious_ip': r'\b(?:\d{1,3}\.){3}\d{1,3}\b.*(suspicious|blocked|blacklisted)',
            'brute_force': r'(?i)(multiple|repeated|brute.*force).*(?:login|attempt|auth)',
            'privilege_escalation': r'(?i)(sudo|root|admin|privilege).*(?:escalation|elevation)',
            'malware': r'(?i)(malware|virus|trojan|ransomware|spyware)',
        }
        
        self.severity_map = {
            'injection': 'critical',
            'privilege_escalation': 'critical',
            'malware': 'critical',
            'brute_force': 'high',
            'auth_failure': 'medium',
            'suspicious_ip': 'medium'
        }
    def detect_patterns(self, context: List[Dict[str, Any]] | List[str]) -> List[Dict[str, Any]]:
        """Detect security patterns in logs"""
        issues = []
        
        for item in context:
            # Handle different input formats
            if isinstance(item, str):
                content = item
                timestamp = datetime.now().isoformat()
                metadata = {}
            elif isinstance(item, dict):
                content = str(item.get('content') if 'content' in item else item.get('message', ''))
                timestamp = item.get('timestamp') or item.get('metadata', {}).get('timestamp')
                metadata = item.get('metadata', {})
            else:
                continue
                
            # Process each pattern
            for pattern_name, pattern in self.patterns.items():
                if matches := re.finditer(pattern, content, re.IGNORECASE):
                    for match in matches:
                        issues.append({
                            'type': pattern_name,
                            'match': match.group(0),
                            'context': content,
                            'timestamp': timestamp,
                            'severity': self.get_severity(pattern_name),
                            'metadata': metadata
                        })
                        
        return issues

    def get_severity(self, issue_type: str) -> str:
        """Get severity level for an issue type"""
        return self.severity_map.get(issue_type, 'low')