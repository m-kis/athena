from datetime import timedelta, datetime
from typing import Dict, List, Optional
import logging
import json
from src.agents.base_agent import BaseAgent
from .cache import LogAnalysisCache
from .pattern_analyzer import PatternAnalyzer
from .trend_analyzer import TrendAnalyzer
from .utils import extract_recommendations, get_default_response, format_log_entry

logger = logging.getLogger(__name__)

class LogAnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.cache = LogAnalysisCache()
        self.pattern_analyzer = PatternAnalyzer()
        self.trend_analyzer = TrendAnalyzer()

    async def _analyze_impl(
        self,
        query: str,
        context: List[Dict],
        time_window: timedelta,
        nlu_context: Optional[Dict] = None
    ) -> Dict:
        try:
            if not context:
                logger.warning("No logs found in context")
                return {
                    "analysis": "No logs found for analysis",
                    "issues": [],
                    "risk_level": "low"
                }

            sample_context = context[:10] if len(context) > 10 else context
            context_hash = hash(json.dumps([str(item) for item in sample_context]))
            cache_key = f"{query}:{time_window}:{context_hash}"

            if cached_result := await self.cache.get(cache_key):
                logger.debug("Returning cached analysis")
                return cached_result

            patterns = self.pattern_analyzer.analyze_patterns(context)
            trends = self.trend_analyzer.analyze_trends(context)
            stats = self.trend_analyzer.calculate_stats(context)

            analysis_prompt = self._generate_analysis_prompt(
                query, patterns, trends, nlu_context
            )

            analysis = await self.llm.analyze_with_fallback(
                json.dumps({
                    "context": sample_context,
                    "patterns": patterns,
                    "trends": trends,
                    "stats": stats
                }),
                analysis_prompt
            )

            results = self._prepare_results(
                analysis=analysis,
                patterns=patterns,
                trends=trends,
                stats=stats,
                nlu_context=nlu_context
            )

            await self.cache.set(cache_key, results)
            return results

        except Exception as e:
            logger.error(f"Error in log analysis: {e}", exc_info=True)
            return get_default_response()

    def _generate_analysis_prompt(
        self,
        query: str,
        patterns: Dict,
        trends: Dict,
        nlu_context: Optional[Dict] = None
    ) -> str:
        prompt = self.pattern_analyzer.generate_analysis_prompt(patterns, trends)

        if nlu_context:
            if hosts := nlu_context.get('entities', {}).get('matched_hosts'):
                prompt += f"\n\nFocus analysis on these hosts: {', '.join(hosts)}"
            if metric := nlu_context.get('entities', {}).get('metric'):
                prompt += f"\nPay special attention to {metric} related issues"

        return prompt

    def _prepare_results(
        self,
        analysis: str,
        patterns: Dict,
        trends: Dict,
        stats: Dict,
        nlu_context: Optional[Dict] = None
    ) -> Dict:
        recommendations = extract_recommendations(analysis)
        risk_level = self.pattern_analyzer.evaluate_risk_level(patterns, stats)

        issues = []
        for name, pattern_list in patterns.items():
            for pattern in pattern_list:
                if isinstance(pattern, dict):
                    issues.append({
                        "description": pattern.get("message", "Unknown issue"),
                        "source": name,
                        "severity": "high" if name in ["database", "memory", "disk"] else "medium",
                        "timestamp": pattern.get("timestamp"),
                        "pattern": pattern.get("match")
                    })

        if nlu_context and issues:
            if hosts := nlu_context.get('entities', {}).get('matched_hosts'):
                issues = [
                    issue for issue in issues
                    if any(host in str(issue.get('description', '')).lower() 
                          for host in hosts)
                ]

        return {
            "analysis": analysis,
            "patterns_detected": patterns,
            "trends": trends,
            "stats": stats,
            "issues": issues,
            "metrics": self._extract_metrics(trends, stats),
            "recommendations": [
                {
                    "description": rec,
                    "source": "log_analysis",
                    "priority": "high" if risk_level in ["critical", "high"] else "normal"
                }
                for rec in recommendations
            ],
            "risk_level": risk_level,
            "sources": ["log_analysis"]
        }

    def _extract_metrics(self, trends: Dict, stats: Dict) -> List[Dict]:
        """Extract metrics from trends and statistics"""
        metrics = []
        timestamp = datetime.now().isoformat()

        # Add error rate metric
        metrics.append({
            'name': 'error_rate',
            'value': stats.get('error_rate', 0) * 100,
            'unit': '%',
            'timestamp': timestamp
        })

        # Add severity metrics
        severity_dist = stats.get('severity_distribution', {})
        for severity, count in severity_dist.items():
            metrics.append({
                'name': f'{severity}_count',
                'value': count,
                'unit': 'count',
                'timestamp': timestamp
            })

        # Add trend metrics if available
        for trend_type, trend_data in trends.items():
            if isinstance(trend_data, dict):
                metrics.append({
                    'name': f'trend_{trend_type}',
                    'value': trend_data,
                    'timestamp': timestamp
                })

        return metrics