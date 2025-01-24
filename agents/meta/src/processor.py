from typing import Dict, List, Tuple
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
from dataclasses import dataclass
import logging
from src.config.settings import settings

logger = logging.getLogger(__name__)

@dataclass
class NLUResult:
    intent: str
    confidence: float
    entities: Dict[str, str]
    metadata: Dict[str, any]

class NLUProcessor:
    """Processeur NLU utilisant un petit modèle BERT/RoBERTa"""
    
    def __init__(self):
        self.model_name = "distilbert-base-uncased"  # Petit modèle rapide
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name,
            num_labels=len(self.get_intent_labels())
        )
        self.intent_labels = self.get_intent_labels()
        self.cache = {}

    @staticmethod
    def get_intent_labels() -> List[str]:
        """Liste des intentions possibles"""
        return [
            'host_inventory',      # Inventaire des hosts
            'host_specific',       # Analyse d'un host spécifique
            'performance',         # Analyse de performance
            'security',           # Analyse de sécurité
            'logs',              # Analyse de logs
            'correlation',        # Analyse de corrélation
            'recommendation',     # Demande de recommandations
            'other'              # Autre
        ]

    async def process(self, query: str) -> NLUResult:
        """Traite une requête pour en extraire l'intention et les entités"""
        try:
            # Vérifier le cache
            if query in self.cache:
                return self.cache[query]

            # Tokenization
            inputs = self.tokenizer(
                query,
                padding=True,
                truncation=True,
                return_tensors="pt"
            )

            # Prédiction
            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
                intent_idx = torch.argmax(predictions, dim=-1).item()
                confidence = predictions[0][intent_idx].item()

            # Extraction d'entités
            entities = self._extract_entities(query)

            # Création du résultat
            result = NLUResult(
                intent=self.intent_labels[intent_idx],
                confidence=confidence,
                entities=entities,
                metadata={
                    'query_length': len(query),
                    'all_intents': {
                        label: predictions[0][i].item()
                        for i, label in enumerate(self.intent_labels)
                    }
                }
            )

            # Mise en cache
            self.cache[query] = result
            return result

        except Exception as e:
            logger.error(f"Error in NLU processing: {e}")
            return NLUResult(
                intent='other',
                confidence=0.0,
                entities={},
                metadata={'error': str(e)}
            )

    def _extract_entities(self, query: str) -> Dict[str, str]:
        """Extrait les entités de la requête"""
        entities = {}
        
        # Extraction de host
        # TODO: Implémenter une vraie NER ici
        common_host_patterns = [
            r'host[0-9]+',
            r'server[0-9]+',
            r'machine[0-9]+'
        ]
        
        # Extraction de métriques
        if 'cpu' in query.lower():
            entities['metric'] = 'cpu'
        elif 'memory' in query.lower() or 'ram' in query.lower():
            entities['metric'] = 'memory'
        elif 'disk' in query.lower():
            entities['metric'] = 'disk'
            
        return entities

    async def train(self, examples: List[Tuple[str, str]]):
        """Entraîne ou affine le modèle avec de nouveaux exemples"""
        # TODO: Implémenter l'entraînement incrémental
        pass