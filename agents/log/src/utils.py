from typing import List, Dict
import re
import logging

logger = logging.getLogger(__name__)

def extract_recommendations(analysis: str) -> List[str]:
    """Extrait les recommandations d'une analyse"""
    recommendations = []
    
    sections = analysis.lower().split('\n')
    in_recommendations = False
    current_recommendation = []
    
    for line in sections:
        if any(keyword in line for keyword in ['recommend', 'suggestion', 'action item', 'mitigation']):
            if current_recommendation:
                recommendations.append(' '.join(current_recommendation))
            in_recommendations = True
            current_recommendation = []
            continue
            
        if in_recommendations and not line.strip():
            if current_recommendation:
                recommendations.append(' '.join(current_recommendation))
            current_recommendation = []
            continue
            
        if in_recommendations and line.strip():
            cleaned_line = re.sub(r'^[\d\-\*\•\.\s]+', '', line.strip())
            if cleaned_line:
                current_recommendation.append(cleaned_line)

    if current_recommendation:
        recommendations.append(' '.join(current_recommendation))

    return [
        clean_recommendation(rec)
        for rec in recommendations
        if len(rec.strip()) > 10
    ]

def clean_recommendation(text: str) -> str:
    """Nettoie et formate une recommandation"""
    cleaned = re.sub(r'[^\w\s\-\.,:]', '', text).strip()
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned

def format_log_entry(log: Dict) -> str:
    """Formate une entrée de log pour l'analyse"""
    components = []
    
    if timestamp := log.get('timestamp'):
        components.append(f"[{timestamp}]")
        
    if level := log.get('level', '').upper():
        components.append(f"{level}")
        
    if component := log.get('labels', {}).get('component'):
        components.append(f"({component})")
        
    if message := log.get('message'):
        components.append(str(message))
        
    return ' '.join(components)

def get_default_response() -> Dict:
    """Retourne une réponse par défaut en cas d'erreur"""
    return {
        "analysis": "Analysis could not be completed",
        "patterns_detected": {},
        "trends": {},
        "stats": {},
        "issues": [{
            "description": "Analysis failed to complete",
            "source": "logs",
            "severity": "medium"
        }],
        "metrics": [],
        "sources": ["logs"],
        "risk_level": "low",
        "recommendations": [{
            "description": "Check system logs for errors",
            "source": "logs",
            "priority": "high"
        }]
    }