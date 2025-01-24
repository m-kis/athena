from dataclasses import dataclass
from typing import List, Dict, Optional
import asyncio
from langchain_ollama import OllamaEmbeddings
import numpy as np
from src.config.settings import settings
import logging

logger = logging.getLogger(__name__)

@dataclass
class QueryIntent:
    category: str  # Ex: 'resource_analysis', 'security', 'performance', etc.
    confidence: float
    entities: Dict[str, str]  # Ex: {'resource_type': 'cpu', 'time_period': '1h'}
    context: Dict[str, any]  # Métadonnées additionnelles

class QueryUnderstandingEngine:
    def __init__(self):
        self.embeddings = OllamaEmbeddings(
            base_url=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}",
            model=settings.MODEL_NAME
        )
        
        # Définir des exemples d'intentions avec leurs embeddings
        self.intent_examples = {
            'resource_analysis': [
                "Quels processus utilisent le plus de CPU ?",
                "Montre-moi l'utilisation de la mémoire",
                "Quelles applications consomment les ressources ?",
                "Le système est lent, qu'est-ce qui consomme trop ?",
                "Analyse la consommation des ressources",
                "Quel process prend tout le CPU ?",
                "Y a-t-il des processus qui fuient en mémoire ?",
            ],
            'security_analysis': [
                "Y a-t-il eu des tentatives d'intrusion ?",
                "Montre-moi les logs de sécurité",
                "Détecte les activités suspectes",
                "Y a-t-il des connexions anormales ?",
                "Vérifie les accès non autorisés",
                "Analyse les logs d'authentification",
                "Cherche des comportements suspects",
            ],
            'performance_analysis': [
                "Comment sont les performances du système ?",
                "Y a-t-il des problèmes de latence ?",
                "Analyse les temps de réponse",
                "Le système répond-il normalement ?",
                "Vérifie les performances des APIs",
                "Comment est la vitesse du système ?",
                "Y a-t-il des goulots d'étranglement ?",
            ],
            'log_analysis': [
                "Que disent les logs ?",
                "Y a-t-il des erreurs dans les logs ?",
                "Montre-moi les logs récents",
                "Analyse les messages d'erreur",
                "Qu'est-ce qui se passe dans les logs ?",
                "Y a-t-il des warnings importants ?",
                "Cherche les erreurs critiques",
            ]
        }
        self._cache = {}
        self._intent_embeddings = {}
        
    async def initialize(self):
        """Pré-calcule les embeddings des exemples"""
        try:
            logger.info("Initializing query understanding engine...")
            for intent, examples in self.intent_examples.items():
                embeddings = []
                for example in examples:
                    if example not in self._cache:
                        embedding = self.embeddings.embed_query(example)
                        self._cache[example] = embedding
                    embeddings.append(self._cache[example])
                self._intent_embeddings[intent] = np.mean(embeddings, axis=0)
            logger.info("Query understanding engine initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing query understanding engine: {e}")
            raise

    def _extract_entities(self, query: str) -> Dict[str, str]:
        """Extrait les entités pertinentes de la requête"""
        entities = {}
        
        # Analyse des ressources spécifiques mentionnées
        if any(word in query.lower() for word in ['cpu', 'processeur', 'charge']):
            entities['resource_type'] = 'cpu'
        elif any(word in query.lower() for word in ['ram', 'mémoire', 'memory']):
            entities['resource_type'] = 'memory'
        elif any(word in query.lower() for word in ['disque', 'disk', 'stockage', 'espace']):
            entities['resource_type'] = 'disk'
        elif any(word in query.lower() for word in ['réseau', 'network', 'connexion', 'bande passante']):
            entities['resource_type'] = 'network'
            
        # Détection de la criticité
        if any(word in query.lower() for word in ['urgent', 'critique', 'important', 'grave']):
            entities['priority'] = 'high'
        elif any(word in query.lower() for word in ['attention', 'surveillance', 'vérifier']):
            entities['priority'] = 'medium'
            
        # Détection de la période
        if 'dernière heure' in query.lower():
            entities['time_period'] = '1h'
        elif 'aujourd\'hui' in query.lower():
            entities['time_period'] = '24h'
        elif 'semaine' in query.lower():
            entities['time_period'] = '7d'
            
        return entities

    async def understand_query(self, query: str) -> QueryIntent:
        """Analyse la requête pour déterminer l'intention et extraire les entités"""
        try:
            # Si pas encore initialisé
            if not self._intent_embeddings:
                await self.initialize()
            
            # Obtenir l'embedding de la requête
            query_embedding = self.embeddings.embed_query(query)
            
            # Calculer la similarité avec chaque intention
            similarities = {}
            for intent, intent_embedding in self._intent_embeddings.items():
                similarity = np.dot(query_embedding, intent_embedding)
                similarities[intent] = similarity
            
            # Trouver l'intention la plus probable
            best_intent = max(similarities.items(), key=lambda x: x[1])
            
            # Extraire les entités
            entities = self._extract_entities(query)
            
            # Construire le contexte
            context = {
                'similar_queries': [
                    ex for ex in self.intent_examples[best_intent[0]]
                    if similarities.get(ex, 0) > 0.7
                ],
                'other_intents': [
                    intent for intent, sim in similarities.items()
                    if sim > 0.5 and intent != best_intent[0]
                ],
                'query_type': 'question' if '?' in query else 'command',
                'analysis_scope': 'specific' if entities else 'general'
            }
            
            intent = QueryIntent(
                category=best_intent[0],
                confidence=float(best_intent[1]),
                entities=entities,
                context=context
            )
            
            logger.debug(f"Query understanding results: {intent}")
            return intent
            
        except Exception as e:
            logger.error(f"Error understanding query: {e}")
            # Retourner une intention par défaut en cas d'erreur
            return QueryIntent(
                category='unknown',
                confidence=0.0,
                entities={},
                context={'error': str(e)}
            )

    async def get_suggested_queries(self, intent: str) -> List[str]:
        """Retourne des exemples de requêtes pour une intention donnée"""
        return self.intent_examples.get(intent, [])