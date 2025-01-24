# src/agents/security/agent.py
from datetime import timedelta
from typing import Dict, List, Optional
from src.agents.base_agent import BaseAgent
from .pattern_detector import SecurityPatternDetector
from .threat_analyzer import ThreatAnalyzer
from .metrics_generator import SecurityMetricsGenerator
from .prompt_generator import SecurityPromptGenerator
import logging
import json

logger = logging.getLogger(__name__)

class SecurityAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.pattern_detector = SecurityPatternDetector()
        self.threat_analyzer = ThreatAnalyzer()
        self.metrics_generator = SecurityMetricsGenerator()
        self.prompt_generator = SecurityPromptGenerator()

    async def _analyze_impl(
        self,
        query: str,
        context: List[Dict],
        time_window: timedelta,
        nlu_context: Optional[Dict] = None
    ) -> Dict:
        """Implement security analysis"""
        try:
            # Detect security patterns
            security_issues = self.pattern_detector.detect_patterns(context)
            
            # Analyze threats
            threat_stats = self.threat_analyzer.compute_stats(security_issues)
            risk_level = self.threat_analyzer.calculate_risk_level(security_issues, threat_stats)
            
            # Generate metrics
            metrics = self.metrics_generator.generate_metrics(threat_stats)
            
            # Get LLM analysis using prompt
            prompt = self.prompt_generator.generate_prompt(security_issues)
            analysis = await self.llm.analyze_with_fallback(
                json.dumps({
                    'security_issues': security_issues,
                    'threat_stats': threat_stats,
                    'time_window': str(time_window),
                    'query': query
                }),
                base_prompt=prompt
            )
            
            # Extract recommendations
            recommendations = self.prompt_generator.extract_recommendations(analysis)

            return {
                'security_analysis': analysis,
                'risk_level': risk_level,
                'threat_stats': threat_stats,
                'detected_issues': security_issues,
                'recommendations': recommendations,
                'metrics': metrics
            }

        except Exception as e:
            logger.error(f"Error in security analysis: {str(e)}", exc_info=True)
            return {
                'security_analysis': f"Analysis failed: {str(e)}",
                'risk_level': 'error',
                'threat_stats': {},
                'detected_issues': [],
                'recommendations': [],
                'metrics': []
            }