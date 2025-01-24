# src/nlu/roberta_processor.py
from transformers import RobertaTokenizer, RobertaForSequenceClassification
import torch
from typing import Dict, List
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class NLUResult:
    intent: str
    confidence: float
    entities: Dict[str, str]
    metadata: Dict[str, any]

class RoBERTaProcessor:
    """Processeur NLU utilisant RoBERTa"""
    
    def __init__(self):
        self.model_name = "roberta-base"
        self.tokenizer = RobertaTokenizer.from_pretrained(self.model_name)
        self.model = RobertaForSequenceClassification.from_pretrained(
            self.model_name,
            num_labels=len(self.get_intent_labels())
        )
        self.intent_labels = self.get_intent_labels()
        self.cache = {}

    @staticmethod
    def get_intent_labels() -> List[str]:
        """Liste des intentions possibles"""
        return [
            'metrics_analysis',
            'security_analysis', 
            'log_analysis',
            'performance_analysis',
            'correlation_analysis',
            'anomaly_detection',
            'other'
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
        
        # Extraction de métriques
        if 'cpu' in query.lower():
            entities['metric'] = 'cpu'
        elif 'memory' in query.lower():
            entities['metric'] = 'memory'
        elif 'disk' in query.lower():
            entities['metric'] = 'disk'
        elif 'network' in query.lower():
            entities['metric'] = 'network'
            
        # Extraction de période
        if 'last hour' in query.lower():
            entities['time_window'] = '1h'
        elif 'today' in query.lower():
            entities['time_window'] = '24h'
        elif 'week' in query.lower():
            entities['time_window'] = '7d'
            
        return entities