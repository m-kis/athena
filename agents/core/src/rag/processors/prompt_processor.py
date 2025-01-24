from typing import Dict, Optional, List
from datetime import datetime, timedelta
import json
import logging
from src.rag.processors.context_processor import ContextProcessor

logger = logging.getLogger(__name__)

class PromptProcessor:
    def __init__(self):
        self.context_processor = ContextProcessor()
        
    async def enhance_prompt(
        self,
        query: str,
        base_prompt: str,
        time_window: Optional[timedelta] = None,
        max_context_items: int = 5
    ) -> str:
        """
        Enhance the base prompt with relevant context
        """
        try:
            # Get combined context
            context = await self.context_processor.get_combined_context(
                query=query,
                time_window=time_window,
                k=max_context_items
            )
            
            # Format context sections
            context_sections = []
            
            # Format log context
            if context['logs']:
                log_section = self._format_log_context(context['logs'])
                context_sections.append(log_section)
                
            # Format metric context
            if context['metrics']:
                metric_section = self._format_metric_context(context['metrics'])
                context_sections.append(metric_section)
                
            # Add summary section
            if context['summary']:
                summary_section = self._format_summary_context(context['summary'])
                context_sections.append(summary_section)
                
            # Combine everything into enhanced prompt
            context_str = "\n\n".join(context_sections)
            
            enhanced_prompt = f"""Based on the following context:

{context_str}

Original Query: {query}

{base_prompt}

Provide a comprehensive analysis focusing on:
1. Key insights from the logs and metrics
2. Potential issues or anomalies
3. Relevant patterns or trends
4. Specific recommendations

Analysis:"""

            return enhanced_prompt
            
        except Exception as e:
            logger.error(f"Error enhancing prompt: {e}", exc_info=True)
            # Return a simplified prompt if enhancement fails
            return f"{base_prompt}\n\nQuery: {query}\n\nAnalysis:"
            
    def _format_log_context(self, logs: List[Dict]) -> str:
        """Format log entries for prompt context"""
        log_lines = ["Log Context:"]
        
        for log in logs:
            relevance = log.get('relevance_score', 0)
            timestamp = log.get('metadata', {}).get('timestamp', 'unknown_time')
            content = log.get('content', '')
            
            log_lines.append(
                f"- [{timestamp}] (Relevance: {relevance:.2f})\n  {content}"
            )
            
        return "\n".join(log_lines)
        
    def _format_metric_context(self, metrics: List[Dict]) -> str:
        """Format metrics for prompt context"""
        metric_lines = ["Metric Context:"]
        
        for metric in metrics:
            relevance = metric.get('relevance_score', 0)
            metric_type = metric.get('metric_type', 'unknown')
            value = metric.get('value', 'N/A')
            unit = metric.get('unit', '')
            
            metric_lines.append(
                f"- {metric_type}: {value}{unit} (Relevance: {relevance:.2f})"
            )
            
        return "\n".join(metric_lines)
        
    def _format_summary_context(self, summary: Dict) -> str:
        """Format context summary"""
        time_range = summary.get('timestamp_range', {})
        start = time_range.get('start', 'unknown')
        end = time_range.get('end', 'unknown')
        
        return f"""Context Summary:
- Time Range: {start} to {end}
- Total Items: {summary.get('total_items', 0)}
- Logs: {summary.get('log_count', 0)}
- Metrics: {summary.get('metric_count', 0)}
- Average Relevance: {summary.get('avg_relevance', 0):.2f}"""