from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass
import logging
from src.models.llm import LLMWrapper

logger = logging.getLogger(__name__)

@dataclass
class Insight:
    category: str  # 'performance', 'security', 'resource', etc.
    importance: int  # 1-5, 5 étant le plus important
    message: str
    evidence: List[Dict]
    confidence: float
    timestamp: datetime
    actions: Optional[List[Dict]] = None
    metadata: Optional[Dict] = None

class InsightsGenerator:
    """Générateur d'insights basé sur l'analyse des métriques et anomalies"""
    
    def __init__(self, llm: Optional[LLMWrapper] = None):
        self.llm = llm or LLMWrapper()
        self.correlation_threshold = 0.7
        self.insight_categories = {
            'performance': self._analyze_performance,
            'resource': self._analyze_resources,
            'security': self._analyze_security,
            'availability': self._analyze_availability,
            'trend': self._analyze_trends
        }

    async def generate_insights(
        self,
        analysis_results: Dict,
        max_insights: int = 5,
        focus_categories: Optional[List[str]] = None
    ) -> List[Insight]:
        """Générer des insights à partir des résultats d'analyse"""
        try:
            insights = []
            categories = focus_categories or list(self.insight_categories.keys())

            # Générer les insights pour chaque catégorie
            for category in categories:
                if analyzer := self.insight_categories.get(category):
                    category_insights = await analyzer(analysis_results)
                    insights.extend(category_insights)

            # Trier par importance et filtrer
            insights.sort(key=lambda x: (-x.importance, -x.confidence))
            filtered_insights = self._filter_redundant_insights(insights)
            
            # Enrichir avec LLM si disponible
            if self.llm:
                enriched_insights = await self._enrich_insights_with_llm(
                    filtered_insights[:max_insights]
                )
                return enriched_insights

            return filtered_insights[:max_insights]

        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return []

    async def _analyze_performance(self, results: Dict) -> List[Insight]:
        """Analyser les aspects performance"""
        insights = []
        
        try:
            # Analyser les métriques de performance
            if metrics := results.get('metrics', []):
                cpu_metrics = [m for m in metrics if 'cpu' in m['name'].lower()]
                memory_metrics = [m for m in metrics if 'memory' in m['name'].lower()]
                
                # Détecter la haute utilisation CPU
                if cpu_metrics:
                    high_cpu = any(m['value'] > 80 for m in cpu_metrics)
                    if high_cpu:
                        insights.append(
                            Insight(
                                category='performance',
                                importance=4,
                                message="High CPU utilization detected",
                                evidence=cpu_metrics,
                                confidence=0.9,
                                timestamp=datetime.now(),
                                actions=[{
                                    'type': 'investigate',
                                    'description': 'Identify CPU-intensive processes'
                                }]
                            )
                        )

                # Détecter les problèmes de mémoire
                if memory_metrics:
                    high_memory = any(m['value'] > 85 for m in memory_metrics)
                    if high_memory:
                        insights.append(
                            Insight(
                                category='performance',
                                importance=5,
                                message="Critical memory usage detected",
                                evidence=memory_metrics,
                                confidence=0.95,
                                timestamp=datetime.now(),
                                actions=[{
                                    'type': 'alert',
                                    'description': 'Investigate memory usage and consider scaling'
                                }]
                            )
                        )

            # Analyser les latences et temps de réponse
            if trends := results.get('trends', {}):
                latency_trends = trends.get('latency', {})
                if latency_trends:
                    insights.extend(
                        self._analyze_latency_trends(latency_trends)
                    )

            return insights

        except Exception as e:
            logger.error(f"Error in performance analysis: {e}")
            return []

    async def _analyze_resources(self, results: Dict) -> List[Insight]:
        """Analyser l'utilisation des ressources"""
        insights = []
        
        try:
            metrics = results.get('metrics', [])
            
            # Regrouper les métriques par type
            resource_metrics = {}
            for metric in metrics:
                resource_type = self._categorize_resource_metric(metric['name'])
                if resource_type:
                    resource_metrics.setdefault(resource_type, []).append(metric)

            # Analyser chaque type de ressource
            for resource_type, type_metrics in resource_metrics.items():
                resource_insights = self._analyze_resource_type(
                    resource_type,
                    type_metrics
                )
                insights.extend(resource_insights)

            # Détecter les corrélations
            if len(resource_metrics) > 1:
                correlation_insights = self._detect_resource_correlations(
                    resource_metrics
                )
                insights.extend(correlation_insights)

            return insights

        except Exception as e:
            logger.error(f"Error in resource analysis: {e}")
            return []

    async def _analyze_security(self, results: Dict) -> List[Insight]:
        """Analyser les aspects sécurité"""
        insights = []
        
        try:
            # Analyser les anomalies de sécurité
            if anomalies := results.get('anomalies', []):
                security_anomalies = [
                    a for a in anomalies 
                    if a.get('category') == 'security'
                ]
                
                if security_anomalies:
                    severity_counts = {
                        'critical': 0,
                        'high': 0,
                        'medium': 0,
                        'low': 0
                    }
                    
                    for anomaly in security_anomalies:
                        severity = anomaly.get('severity', 'low')
                        severity_counts[severity] += 1

                    if severity_counts['critical'] > 0:
                        insights.append(
                            Insight(
                                category='security',
                                importance=5,
                                message=f"Critical security anomalies detected: {severity_counts['critical']}",
                                evidence=security_anomalies,
                                confidence=0.95,
                                timestamp=datetime.now(),
                                actions=[{
                                    'type': 'alert',
                                    'description': 'Immediate security investigation required'
                                }]
                            )
                        )

            # Analyser les tendances de sécurité
            if trends := results.get('trends', {}):
                security_trends = trends.get('security', {})
                if security_trends:
                    trend_insights = self._analyze_security_trends(security_trends)
                    insights.extend(trend_insights)

            return insights

        except Exception as e:
            logger.error(f"Error in security analysis: {e}")
            return []

    async def _analyze_trends(self, results: Dict) -> List[Insight]:
        """Analyser les tendances générales"""
        insights = []
        
        try:
            if trends := results.get('trends', {}):
                # Analyser les tendances par métrique
                for metric_name, trend_data in trends.items():
                    trend_insights = self._analyze_metric_trend(
                        metric_name,
                        trend_data
                    )
                    insights.extend(trend_insights)

                # Détecter les patterns saisonniers
                seasonal_insights = self._detect_seasonality(trends)
                insights.extend(seasonal_insights)

            return insights

        except Exception as e:
            logger.error(f"Error in trend analysis: {e}")
            return []

    async def _analyze_availability(self, results: Dict) -> List[Insight]:
        """Analyser la disponibilité des services"""
        insights = []
        
        try:
            metrics = results.get('metrics', [])
            availability_metrics = [
                m for m in metrics 
                if any(key in m['name'].lower() for key in ['uptime', 'availability', 'health'])
            ]

            if availability_metrics:
                # Calculer la disponibilité moyenne
                availability_values = [m['value'] for m in availability_metrics]
                avg_availability = np.mean(availability_values)

                if avg_availability < 99.9:
                    insights.append(
                        Insight(
                            category='availability',
                            importance=5 if avg_availability < 99 else 3,
                            message=f"Service availability below target: {avg_availability:.2f}%",
                            evidence=availability_metrics,
                            confidence=0.9,
                            timestamp=datetime.now(),
                            actions=[{
                                'type': 'investigate',
                                'description': 'Review service health and incidents'
                            }]
                        )
                    )

            return insights

        except Exception as e:
            logger.error(f"Error in availability analysis: {e}")
            return []

    def _filter_redundant_insights(self, insights: List[Insight]) -> List[Insight]:
        """Filtrer les insights redondants"""
        filtered = []
        seen_messages = set()
        
        for insight in insights:
            # Créer une version normalisée du message pour la comparaison
            normalized_message = ' '.join(insight.message.lower().split())
            
            if normalized_message not in seen_messages:
                seen_messages.add(normalized_message)
                filtered.append(insight)
                
        return filtered

    async def _enrich_insights_with_llm(self, insights: List[Insight]) -> List[Insight]:
        """Enrichir les insights avec l'analyse LLM"""
        enriched_insights = []
        
        for insight in insights:
            try:
                # Préparer le contexte pour le LLM
                context = {
                    'message': insight.message,
                    'category': insight.category,
                    'evidence': insight.evidence,
                    'importance': insight.importance
                }
                
                # Générer une analyse plus détaillée
                analysis = await self.llm.analyze_with_fallback(
                    str(context),
                    "Provide detailed analysis and specific recommendations"
                )
                
                # Mettre à jour l'insight avec l'analyse enrichie
                insight.metadata = {
                    'llm_analysis': analysis,
                    'enriched_at': datetime.now().isoformat()
                }
                
                enriched_insights.append(insight)
                
            except Exception as e:
                logger.error(f"Error enriching insight with LLM: {e}")
                enriched_insights.append(insight)
                
        return enriched_insights

    def _categorize_resource_metric(self, metric_name: str) -> Optional[str]:
        """Catégoriser une métrique de ressource"""
        name_lower = metric_name.lower()
        
        if 'cpu' in name_lower:
            return 'cpu'
        elif 'memory' in name_lower or 'mem' in name_lower:
            return 'memory'
        elif 'disk' in name_lower or 'storage' in name_lower:
            return 'disk'
        elif 'network' in name_lower:
            return 'network'
            
        return None

    def _analyze_resource_type(
        self,
        resource_type: str,
        metrics: List[Dict]
    ) -> List[Insight]:
        """Analyser un type spécifique de ressource"""
        insights = []
        
        # Calculer les statistiques de base
        values = [m['value'] for m in metrics]
        avg_value = np.mean(values)
        max_value = np.max(values)
        
        # Définir les seuils par type de ressource
        thresholds = {
            'cpu': {'high': 80, 'critical': 90},
            'memory': {'high': 85, 'critical': 95},
            'disk': {'high': 85, 'critical': 90},
            'network': {'high': 80, 'critical': 90}
        }
        
        if resource_type in thresholds:
            if max_value >= thresholds[resource_type]['critical']:
                insights.append(
                    Insight(
                        category='resource',
                        importance=5,
                        message=f"Critical {resource_type} usage detected: {max_value:.1f}%",
                        evidence=metrics,
                        confidence=0.95,
                        timestamp=datetime.now(),
                        actions=[{
                            'type': 'alert',
                            'description': f'Investigate high {resource_type} usage'
                        }]
                    )
                )
            elif max_value >= thresholds[resource_type]['high']:
                insights.append(
                    Insight(
                        category='resource',
                        importance=4,
                        message=f"High {resource_type} usage detected: {max_value:.1f}%",
                        evidence=metrics,
                        confidence=0.9,
                        timestamp=datetime.now(),
                        actions=[{
                            'type': 'monitor',
                            'description': f'Monitor {resource_type} usage closely'
                        }]
                    )
                )
                
        return insights