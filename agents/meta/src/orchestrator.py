# src/agents/meta_agent/orchestrator.py
from typing import Dict, List, Optional, Any
from datetime import timedelta, datetime
import logging
from src.nlu.roberta_processor import RoBERTaProcessor, NLUResult
from src.agents.metrics.metrics_agent import MetricAgent
from src.agents.log_analysis.agent import LogAnalysisAgent
from src.agents.security.agent import SecurityAgent
from src.agents.performance_agent import PerformanceAgent
from src.config.settings import settings

logger = logging.getLogger(__name__)

class MetaOrchestrator:
    def __init__(self):
        self.nlu = RoBERTaProcessor()
        self.agents = {
            'metrics': MetricAgent(),
            'logs': LogAnalysisAgent(),
            'security': SecurityAgent(),
            'performance': PerformanceAgent()
        }
        
        # Mappings avancés pour routage
        self.intent_agent_mapping = {
            'metrics_analysis': ['metrics'],
            'security_analysis': ['security'],
            'log_analysis': ['logs'],
            'performance_analysis': ['performance', 'metrics'],
            'correlation_analysis': ['metrics', 'logs', 'security'],
            'anomaly_detection': ['metrics', 'security']
        }

    async def process_query(
        self,
        query: str,
        time_window: timedelta,
        context: Optional[Dict] = None
    ) -> Dict:
        """Traite une requête utilisateur"""
        try:
            # Analyse NLU
            nlu_result = await self.nlu.process(query)
            logger.info(f"NLU Result: {nlu_result}")

            # Sélection des agents
            selected_agents = self._select_agents(nlu_result)
            logger.info(f"Selected agents: {selected_agents}")

            # Exécution parallèle des agents
            results = await self._execute_agents(
                query=query,
                time_window=time_window,
                agents=selected_agents,
                nlu_result=nlu_result,
                context=context
            )

            # Synthèse des résultats
            synthesis = await self._synthesize_results(
                results=results,
                nlu_result=nlu_result
            )

            return {
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'intent': nlu_result.intent,
                'confidence': nlu_result.confidence,
                'results': synthesis,
                'metadata': {
                    'agents_used': selected_agents,
                    'processing_time': datetime.now().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Error in query processing: {e}", exc_info=True)
            return self._get_error_response(str(e))

    def _select_agents(self, nlu_result: NLUResult) -> List[str]:
        """Sélectionne les agents basés sur l'intention NLU"""
        # Obtenir les agents mappés à l'intention
        agents = self.intent_agent_mapping.get(
            nlu_result.intent,
            ['logs', 'metrics']  # Agents par défaut
        )

        # Ajouter des agents basés sur les entités
        if 'metric' in nlu_result.entities:
            agents.append('metrics')
        
        # Dédupliquer
        return list(set(agents))

    async def _execute_agents(
        self,
        query: str,
        time_window: timedelta,
        agents: List[str],
        nlu_result: NLUResult,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Exécute les agents sélectionnés"""
        results = {}
        
        for agent_name in agents:
            try:
                if agent := self.agents.get(agent_name):
                    results[agent_name] = await agent.analyze(
                        query=query,
                        time_window=time_window,
                        context=context,
                        nlu_result=nlu_result
                    )
            except Exception as e:
                logger.error(f"Error in {agent_name} analysis: {e}")
                results[agent_name] = {
                    'error': str(e),
                    'status': 'error'
                }

        return results

    async def _synthesize_results(
        self,
        results: Dict[str, Any],
        nlu_result: NLUResult
    ) -> Dict:
        """Synthétise les résultats des différents agents"""
        synthesis = {
            'summary': [],
            'metrics': [],
            'issues': [],
            'recommendations': [],
            'risk_level': 'low'
        }

        # Agréger les métriques
        for agent_name, result in results.items():
            if isinstance(result, dict):
                synthesis['metrics'].extend(result.get('metrics', []))
                synthesis['issues'].extend(result.get('issues', []))
                synthesis['recommendations'].extend(
                    result.get('recommendations', [])
                )

        # Déterminer le niveau de risque global
        risk_levels = {
            'critical': 3,
            'high': 2,
            'medium': 1,
            'low': 0
        }

        max_risk = max(
            (risk_levels.get(result.get('risk_level', 'low'), 0) 
             for result in results.values()),
            default=0
        )

        synthesis['risk_level'] = next(
            level for level, score in risk_levels.items() 
            if score == max_risk
        )

        return synthesis

    def _get_error_response(self, error: str) -> Dict:
        """Génère une réponse d'erreur standardisée"""
        return {
            'error': error,
            'timestamp': datetime.now().isoformat(),
            'status': 'error',
            'recommendations': [{
                'description': 'Please try again or contact support if the issue persists',
                'priority': 'high'
            }]
        }