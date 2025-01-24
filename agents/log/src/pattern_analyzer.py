from typing import Dict, List
import re
import json
from collections import defaultdict

class PatternAnalyzer:
    def __init__(self):
        self.ERROR_PATTERNS = {
            'connection': r'(?i)(connection|timeout|refused|unreachable)',
            'database': r'(?i)(database|db|sql|query).*error',
            'memory': r'(?i)(memory|heap|stack|overflow)',
            'disk': r'(?i)(disk|storage|space|volume).*(?:full|error)',
            'api': r'(?i)(api|http|request).*(?:error|failed|timeout)',
            'config': r'(?i)(config|configuration|setting).*(?:invalid|missing|error)'
        }

    def analyze_patterns(self, logs: List[Dict] | List[str]) -> Dict:
        patterns = defaultdict(list)
        for log in logs:
            message = self._normalize_message(log) if isinstance(log, str) else self._normalize_message(log.get('message', ''))
            timestamp = log.get('timestamp') if isinstance(log, dict) else None
            
            for pattern_name, pattern in self.ERROR_PATTERNS.items():
                if matches := re.finditer(pattern, message, re.IGNORECASE):
                    patterns[pattern_name].extend({
                        'message': message,
                        'timestamp': timestamp,
                        'match': match.group(0)
                    } for match in matches)
                    
        return dict(patterns)
    
    def evaluate_risk_level(self, patterns: Dict, stats: Dict) -> str:
        risk_score = self._calculate_risk_score(patterns, stats)
        if risk_score >= 7: return 'critical'
        elif risk_score >= 4: return 'high'
        elif risk_score >= 2: return 'medium'
        return 'low'

    def _calculate_risk_score(self, patterns: Dict, stats: Dict) -> int:
        score = 0
        critical_patterns = ['database', 'memory', 'disk']
        for pattern in critical_patterns:
            if pattern in patterns and patterns[pattern]:
                score += len(patterns[pattern]) * 2

        error_rate = stats.get('error_rate', 0)
        if error_rate > 0.30: score += 3
        elif error_rate > 0.15: score += 2
        elif error_rate > 0.05: score += 1
        return score

    def _normalize_message(self, message: any) -> str:
        if isinstance(message, dict):
            return json.dumps(message)
        return str(message)

    def generate_analysis_prompt(self, patterns: Dict, trends: Dict) -> str:
        sections = ["Analyze these logs focusing on the following aspects:"]
        
        # Add pattern sections
        if patterns:
            sections.append("1. Detected Patterns:")
            for pattern_name, matches in patterns.items():
                sections.append(f"   - {pattern_name.title()} issues: {len(matches)} occurrences")

        # Add trends if present
        if trends:
            sections.append("\n2. Observed Trends:")
            if 'error_frequency' in trends:
                sections.append("   - Error frequency patterns")
            if 'temporal_distribution' in trends:
                sections.append("   - Time-based patterns")

        # Analysis instructions
        sections.extend([
            "\n3. Provide:",
            "- Root cause analysis",
            "- Impact assessment",
            "- Specific recommendations",
            "- Priority of issues"
        ])

        return "\n".join(sections)