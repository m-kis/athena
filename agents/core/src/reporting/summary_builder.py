from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass
import logging
from src.models.llm import LLMWrapper
from .insights_generator import Insight

logger = logging.getLogger(__name__)

@dataclass
class AnalysisSummary:
    title: str
    overview: str
    key_findings: List[str]
    risk_assessment: Dict[str, str]
    recommendations: List[Dict]
    metrics_summary: Dict[str, Any]
    time_period: str
    generated_at: datetime
    metadata: Optional[Dict] = None

class SummaryBuilder:
    """Constructeur de résumés pour les analyses de métriques et insights"""
    
    def __init__(self, llm: Optional[LLMWrapper] = None):
        self.llm = llm or LLMWrapper()

    async def build_summary(
        self,
        analysis_results: Dict,
        insights: List[Insight],
        time_window: timedelta,
        include_raw_data: bool = False
    ) -> AnalysisSummary:
        """Construire un résumé complet à partir des résultats d'analyse et insights"""
        try:
            # Générer les composants du résumé
            overview = await self._generate_overview(analysis_results, insights)
            key_findings = self._extract_key_findings(insights)
            risk_assessment = self._assess_risks(analysis_results, insights)
            recommendations = self._compile_recommendations(insights)
            metrics_summary = self._summarize_metrics(analysis_results)

            # Construire le titre
            title = self._generate_title(analysis_results, insights)

            # Créer le résumé
            summary = AnalysisSummary(
                title=title,
                overview=overview,
                key_findings=key_findings,
                risk_assessment=risk_assessment,
                recommendations=recommendations,
                metrics_summary=metrics_summary,
                time_period=self._format_time_period(time_window),
                generated_at=datetime.now(),
                metadata=self._build_metadata(analysis_results, include_raw_data)
            )

            return summary

        except Exception as e:
            logger.error(f"Error building summary: {e}")
            return self._get_error_summary()

    async def _generate_overview(
        self,
        results: Dict,
        insights: List[Insight]
    ) -> str:
        """Générer un aperçu général de l'analyse"""
        try:
            # Préparer le contexte pour le LLM
            context = {
                "total_metrics": len(results.get("metrics", [])),
                "total_anomalies": len(results.get("anomalies", [])),
                "critical_insights": len([i for i in insights if i.importance >= 4]),
                "risk_level": results.get("risk_level", "unknown")
            }

            # Base text pour l'aperçu
            base_overview = (
                f"Analysis detected {context['total_anomalies']} anomalies and "
                f"generated {len(insights)} insights, with {context['critical_insights']} "
                f"critical findings. Overall risk level: {context['risk_level'].upper()}."
            )

            # Enrichir avec LLM si disponible
            if self.llm:
                enhanced_overview = await self.llm.analyze_with_fallback(
                    str(context),
                    f"Enhance this overview: {base_overview}"
                )
                return enhanced_overview

            return base_overview

        except Exception as e:
            logger.error(f"Error generating overview: {e}")
            return "Analysis summary generation failed."

    def _extract_key_findings(self, insights: List[Insight]) -> List[str]:
        """Extraire les conclusions principales des insights"""
        try:
            # Filtrer et trier les insights par importance
            important_insights = sorted(
                [i for i in insights if i.importance >= 3],
                key=lambda x: (-x.importance, -x.confidence)
            )

            # Formatter les findings
            findings = []
            for insight in important_insights:
                finding = self._format_finding(insight)
                if finding:
                    findings.append(finding)

            return findings[:5]  # Limiter aux 5 plus importants

        except Exception as e:
            logger.error(f"Error extracting key findings: {e}")
            return ["Error processing key findings"]

    def _assess_risks(
        self,
        results: Dict,
        insights: List[Insight]
    ) -> Dict[str, str]:
        """Évaluer les risques par catégorie"""
        try:
            risk_assessment = {
                "overall": results.get("risk_level", "unknown"),
                "categories": {}
            }

            # Grouper les insights par catégorie
            category_insights = {}
            for insight in insights:
                category_insights.setdefault(insight.category, []).append(insight)

            # Évaluer chaque catégorie
            for category, cat_insights in category_insights.items():
                risk_level = self._calculate_category_risk(cat_insights)
                risk_assessment["categories"][category] = {
                    "level": risk_level,
                    "details": self._get_risk_details(cat_insights)
                }

            return risk_assessment

        except Exception as e:
            logger.error(f"Error assessing risks: {e}")
            return {"overall": "unknown", "categories": {}}

    def _compile_recommendations(self, insights: List[Insight]) -> List[Dict]:
        """Compiler et prioriser les recommandations"""
        try:
            recommendations = []
            seen_recommendations = set()

            # Extraire les actions de tous les insights
            for insight in insights:
                if not insight.actions:
                    continue

                for action in insight.actions:
                    # Créer une clé unique pour la déduplication
                    action_key = f"{action['type']}:{action['description']}"
                    
                    if action_key not in seen_recommendations:
                        recommendation = {
                            "type": action["type"],
                            "description": action["description"],
                            "priority": self._map_importance_to_priority(insight.importance),
                            "category": insight.category,
                            "confidence": insight.confidence
                        }
                        recommendations.append(recommendation)
                        seen_recommendations.add(action_key)

            # Trier par priorité et confiance
            return sorted(
                recommendations,
                key=lambda x: (-int(x["priority"]), -x["confidence"])
            )

        except Exception as e:
            logger.error(f"Error compiling recommendations: {e}")
            return []

    def _summarize_metrics(self, results: Dict) -> Dict:
        """Créer un résumé des métriques principales"""
        try:
            metrics = results.get("metrics", [])
            summary = {
                "total_metrics": len(metrics),
                "categories": {},
                "statistics": {},
                "anomalies": {}
            }

            # Grouper les métriques par catégorie
            for metric in metrics:
                category = self._categorize_metric(metric["name"])
                if category not in summary["categories"]:
                    summary["categories"][category] = []
                summary["categories"][category].append(metric)

            # Calculer les statistiques par catégorie
            for category, cat_metrics in summary["categories"].items():
                summary["statistics"][category] = self._calculate_metric_stats(cat_metrics)

            # Résumer les anomalies
            if anomalies := results.get("anomalies", []):
                summary["anomalies"] = self._summarize_anomalies(anomalies)

            return summary

        except Exception as e:
            logger.error(f"Error summarizing metrics: {e}")
            return {"error": str(e)}

    def _format_time_period(self, time_window: timedelta) -> str:
        """Formater la période d'analyse"""
        hours = time_window.total_seconds() / 3600
        
        if hours < 1:
            minutes = time_window.total_seconds() / 60
            return f"Last {int(minutes)} minutes"
        elif hours < 24:
            return f"Last {int(hours)} hours"
        else:
            days = hours / 24
            return f"Last {int(days)} days"

    def _format_finding(self, insight: Insight) -> Optional[str]:
        """Formater un insight en finding"""
        try:
            importance_markers = {
                5: "CRITICAL",
                4: "HIGH",
                3: "MEDIUM"
            }
            
            marker = importance_markers.get(insight.importance, "")
            if marker:
                return f"[{marker}] {insight.message}"
            return insight.message

        except Exception:
            return None

    def _calculate_category_risk(self, insights: List[Insight]) -> str:
        """Calculer le niveau de risque pour une catégorie"""
        if not insights:
            return "low"

        # Calculer un score basé sur l'importance et la confiance
        scores = [insight.importance * insight.confidence for insight in insights]
        avg_score = np.mean(scores)

        if avg_score >= 4:
            return "critical"
        elif avg_score >= 3:
            return "high"
        elif avg_score >= 2:
            return "medium"
        return "low"

    def _get_risk_details(self, insights: List[Insight]) -> str:
        """Obtenir les détails de risque pour une catégorie"""
        if not insights:
            return "No specific risks identified"

        # Prendre les insights les plus importants
        critical_insights = [i for i in insights if i.importance >= 4]
        if critical_insights:
            details = [i.message for i in critical_insights]
            return "; ".join(details)

        return "No critical risks identified"

    def _map_importance_to_priority(self, importance: int) -> int:
        """Mapper l'importance à une priorité"""
        return min(max(importance, 1), 5)

    def _categorize_metric(self, metric_name: str) -> str:
        """Catégoriser une métrique"""
        name_lower = metric_name.lower()
        
        if 'cpu' in name_lower:
            return 'cpu'
        elif 'memory' in name_lower or 'mem' in name_lower:
            return 'memory'
        elif 'disk' in name_lower or 'storage' in name_lower:
            return 'disk'
        elif 'network' in name_lower:
            return 'network'
        return 'other'

    def _calculate_metric_stats(self, metrics: List[Dict]) -> Dict:
        """Calculer les statistiques pour un groupe de métriques"""
        values = [m.get("value", 0) for m in metrics]
        return {
            "count": len(values),
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
            "mean": np.mean(values) if values else 0,
            "std": np.std(values) if values else 0
        }

    def _summarize_anomalies(self, anomalies: List[Dict]) -> Dict:
        """Résumer les anomalies détectées"""
        summary = {
            "total": len(anomalies),
            "by_severity": {},
            "by_category": {}
        }

        # Compter par sévérité et catégorie
        for anomaly in anomalies:
            severity = anomaly.get("severity", "unknown")
            category = anomaly.get("category", "unknown")
            
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
            summary["by_category"][category] = summary["by_category"].get(category, 0) + 1

        return summary

    def _build_metadata(
        self,
        results: Dict,
        include_raw_data: bool
    ) -> Dict:
        """Construire les métadonnées du résumé"""
        metadata = {
            "version": "2.0",
            "generated_at": datetime.now().isoformat(),
            "source": results.get("source", "unknown"),
            "analysis_duration": results.get("duration")
        }

        if include_raw_data:
            metadata["raw_data"] = results

        return metadata

    def _get_error_summary(self) -> AnalysisSummary:
        """Créer un résumé d'erreur"""
        return AnalysisSummary(
            title="Error in Analysis Summary",
            overview="Failed to generate analysis summary",
            key_findings=["Error processing analysis results"],
            risk_assessment={"overall": "unknown"},
            recommendations=[],
            metrics_summary={},
            time_period="unknown",
            generated_at=datetime.now(),
            metadata={"error": True}
        )

    def _generate_title(self, results: Dict, insights: List[Insight]) -> str:
        """Générer un titre approprié pour le résumé"""
        try:
            # Déterminer le niveau de risque global
            risk_level = results.get("risk_level", "unknown").upper()
            
            # Compter les problèmes critiques
            critical_count = len([i for i in insights if i.importance >= 4])
            
            if critical_count > 0:
                return f"System Analysis Report - {risk_level} Risk Level ({critical_count} Critical Issues)"
            elif risk_level in ["HIGH", "CRITICAL"]:
                return f"System Analysis Report - {risk_level} Risk Level"
            else:
                return f"System Analysis Report - {risk_level} Risk Level - Normal Operations"
                
        except Exception:
            return "System Analysis Report"