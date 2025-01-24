from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class FormattingOptions:
    include_raw_data: bool = False
    max_items: int = 10
    sort_by: Optional[str] = None
    time_format: str = "%Y-%m-%d %H:%M:%S"
    include_metadata: bool = True

class ResultFormatter:
    """Formateur standardisé pour les résultats d'analyse"""
    
    def __init__(self, options: Optional[FormattingOptions] = None):
        self.options = options or FormattingOptions()

    def format_analysis_result(self, result: Dict) -> Dict:
        """Formater un résultat d'analyse complet"""
        try:
            formatted = {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "data": self._format_data_section(result),
                "metadata": self._format_metadata(result) if self.options.include_metadata else None
            }

            # Ajouter les sections spécifiques
            if "metrics" in result:
                formatted["metrics"] = self._format_metrics(result["metrics"])
                
            if "anomalies" in result:
                formatted["anomalies"] = self._format_anomalies(result["anomalies"])
                
            if "recommendations" in result:
                formatted["recommendations"] = self._format_recommendations(
                    result["recommendations"]
                )

            # Calcul du risk_level global
            formatted["risk_level"] = self._calculate_global_risk(result)

            return formatted

        except Exception as e:
            logger.error(f"Error formatting analysis result: {e}")
            return self._get_error_response(str(e))

    def _format_data_section(self, result: Dict) -> Dict:
        """Formater la section principale des données"""
        data = {
            "summary": self._create_summary(result),
            "details": {}
        }
        
        # Ajouter les métriques si présentes
        if "metrics" in result:
            data["details"]["metrics"] = self._format_metric_details(
                result["metrics"]
            )
            
        # Ajouter les tendances si présentes
        if "trends" in result:
            data["details"]["trends"] = self._format_trends(result["trends"])
            
        # Ajouter les prédictions si présentes
        if "predictions" in result:
            data["details"]["predictions"] = self._format_predictions(
                result["predictions"]
            )

        return data

    def _format_metrics(self, metrics: List[Dict]) -> List[Dict]:
        """Formater les métriques"""
        formatted_metrics = []
        
        for metric in metrics[:self.options.max_items]:
            formatted_metric = {
                "name": metric["name"],
                "value": self._format_value(metric["value"]),
                "unit": metric.get("unit", ""),
                "timestamp": self._format_timestamp(metric["timestamp"])
            }
            
            # Ajouter les métadonnées si présentes
            if "metadata" in metric and self.options.include_metadata:
                formatted_metric["metadata"] = metric["metadata"]
                
            formatted_metrics.append(formatted_metric)
            
        return formatted_metrics

    def _format_anomalies(self, anomalies: List[Dict]) -> List[Dict]:
        """Formater les anomalies"""
        formatted_anomalies = []
        
        for anomaly in anomalies[:self.options.max_items]:
            formatted_anomaly = {
                "timestamp": self._format_timestamp(anomaly["timestamp"]),
                "metric": anomaly["metric"],
                "value": self._format_value(anomaly["value"]),
                "severity": anomaly["severity"],
                "description": self._generate_anomaly_description(anomaly)
            }
            
            # Ajouter le contexte si présent
            if "context" in anomaly and self.options.include_metadata:
                formatted_anomaly["context"] = anomaly["context"]
                
            formatted_anomalies.append(formatted_anomaly)
            
        return formatted_anomalies

    def _format_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
        """Formater les recommandations"""
        formatted_recommendations = []
        
        for rec in recommendations[:self.options.max_items]:
            formatted_rec = {
                "description": rec["description"],
                "priority": rec["priority"],
                "category": rec.get("category", "general")
            }
            
            # Ajouter les actions si présentes
            if "actions" in rec:
                formatted_rec["actions"] = self._format_actions(rec["actions"])
                
            formatted_recommendations.append(formatted_rec)
            
        return formatted_recommendations

    def _format_timestamp(self, timestamp: Any) -> str:
        """Formater un timestamp selon le format spécifié"""
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif isinstance(timestamp, (int, float)):
                dt = datetime.fromtimestamp(timestamp)
            else:
                dt = timestamp
                
            return dt.strftime(self.options.time_format)
            
        except Exception:
            return str(timestamp)

    def _format_value(self, value: Any) -> Any:
        """Formater une valeur numérique"""
        if isinstance(value, (int, float)):
            return round(value, 2) if isinstance(value, float) else value
        return value

    def _generate_anomaly_description(self, anomaly: Dict) -> str:
        """Générer une description pour une anomalie"""
        metric_name = anomaly["metric"]
        value = self._format_value(anomaly["value"])
        expected = self._format_value(anomaly.get("expected_value", 0))
        
        return (
            f"Anomalous {metric_name} value detected: {value} "
            f"(expected around {expected})"
        )

    def _format_actions(self, actions: List[Dict]) -> List[Dict]:
        """Formater les actions recommandées"""
        formatted_actions = []
        
        for action in actions:
            formatted_action = {
                "type": action["type"],
                "description": action["description"],
                "automated": action.get("automated", False)
            }
            
            if "command" in action:
                formatted_action["command"] = action["command"]
                
            formatted_actions.append(formatted_action)
            
        return formatted_actions

    def _create_summary(self, result: Dict) -> Dict:
        """Créer un résumé des résultats"""
        return {
            "total_metrics": len(result.get("metrics", [])),
            "total_anomalies": len(result.get("anomalies", [])),
            "total_recommendations": len(result.get("recommendations", [])),
            "risk_level": self._calculate_global_risk(result),
            "analysis_duration": result.get("duration", "unknown")
        }

    def _format_metadata(self, result: Dict) -> Dict:
        """Formater les métadonnées"""
        return {
            "timestamp": datetime.now().isoformat(),
            "version": "2.0",
            "source": result.get("source", "unknown"),
            "query": result.get("query", ""),
            "parameters": result.get("parameters", {})
        }

    def _calculate_global_risk(self, result: Dict) -> str:
        """Calculer le niveau de risque global"""
        risk_scores = {
            "critical": 3,
            "high": 2,
            "medium": 1,
            "low": 0
        }
        
        # Récupérer tous les niveaux de risque
        risk_levels = []
        
        if "risk_level" in result:
            risk_levels.append(result["risk_level"])
            
        if "anomalies" in result:
            risk_levels.extend(
                anomaly["severity"] for anomaly in result["anomalies"]
            )
            
        if not risk_levels:
            return "unknown"
            
        # Convertir en scores et prendre le maximum
        max_score = max(risk_scores.get(level, 0) for level in risk_levels)
        
        # Reconvertir en niveau de risque
        for level, score in risk_scores.items():
            if score == max_score:
                return level
                
        return "unknown"

    def _get_error_response(self, error: str) -> Dict:
        """Générer une réponse d'erreur formatée"""
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(error),
            "data": None
        }