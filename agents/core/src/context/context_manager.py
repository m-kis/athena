from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import asyncio
import logging
from dataclasses import dataclass
from src.embeddings.loki_client import LokiClient
from src.context.time_window import TimeWindow
from src.rag.cache.memory_cache import MemoryCache
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class ContextConfig:
    max_logs: int = 1000
    max_metrics: int = 500
    cache_ttl: int = 300  # 5 minutes
    include_raw_data: bool = False
    correlation_window: timedelta = timedelta(minutes=30)

class ContextManager:
    """Gestionnaire centralisé du contexte d'analyse"""
    
    def __init__(
        self,
        config: Optional[ContextConfig] = None,
        loki_client: Optional[LokiClient] = None
    ):
        self.config = config or ContextConfig()
        self.loki_client = loki_client or LokiClient()
        self.time_window = TimeWindow()
        self.cache = MemoryCache(
            max_size=1000,
            default_ttl=self.config.cache_ttl
        )
        
    async def get_analysis_context(
        self,
        query: str,
        time_window: timedelta,
        context_types: Optional[List[str]] = None,
        include_correlations: bool = True
    ) -> Dict:
        """
        Récupérer le contexte complet pour une analyse
        
        Args:
            query: Requête d'analyse
            time_window: Fenêtre temporelle
            context_types: Types de contexte à inclure ('logs', 'metrics', etc.)
            include_correlations: Inclure l'analyse des corrélations
            
        Returns:
            Dict contenant le contexte d'analyse
        """
        try:
            # Valider et ajuster la fenêtre temporelle
            start_time, end_time = self.time_window.get_time_range(time_window)
            
            if not self.time_window.validate_range(start_time, end_time):
                logger.error("Invalid time range")
                return self._get_empty_context()
            
            # Vérifier le cache
            cache_key = self._build_cache_key(query, start_time, end_time, context_types)
            if cached_context := await self.cache.get(cache_key):
                logger.info("Returning cached context")
                return cached_context
            
            # Construire le contexte
            context = await self._build_context(
                query,
                start_time,
                end_time,
                context_types
            )
            
            # Ajouter les corrélations si demandées
            if include_correlations:
                correlations = await self._analyze_correlations(context)
                context['correlations'] = correlations
            
            # Mettre en cache
            await self.cache.set(cache_key, context)
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting analysis context: {e}")
            return self._get_empty_context()

    async def _build_context(
        self,
        query: str,
        start_time: datetime,
        end_time: datetime,
        context_types: Optional[List[str]] = None
    ) -> Dict:
        """Construire le contexte d'analyse complet"""
        context = {
            'metadata': {
                'query': query,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'types': context_types
            }
        }
        
        # Déterminer les types de contexte à récupérer
        types_to_fetch = context_types or ['logs', 'metrics', 'events']
        
        # Récupérer les différents types de contexte en parallèle
        tasks = []
        if 'logs' in types_to_fetch:
            tasks.append(self._get_logs_context(query, start_time, end_time))
        if 'metrics' in types_to_fetch:
            tasks.append(self._get_metrics_context(query, start_time, end_time))
        if 'events' in types_to_fetch:
            tasks.append(self._get_events_context(query, start_time, end_time))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Traiter les résultats
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error fetching context: {result}")
                continue
            context.update(result)
            
        return context

    async def _get_logs_context(
        self,
        query: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict:
        """Récupérer le contexte des logs"""
        try:
            logs_response = await self.loki_client.query_logs(
                query=query,
                start_time=start_time,
                end_time=end_time,
                limit=self.config.max_logs
            )
            
            return {
                'logs': logs_response.get('logs', []),
                'log_stats': logs_response.get('stats', {})
            }
            
        except Exception as e:
            logger.error(f"Error getting logs context: {e}")
            return {'logs': [], 'log_stats': {}}

    async def _get_metrics_context(
        self,
        query: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict:
        """Récupérer le contexte des métriques"""
        try:
            # Détecter le type de métrique à partir de la requête
            metric_name = self._detect_metric_type(query)
            
            metrics_response = await self.loki_client.query_logs(
                query=query,
                start_time=start_time,
                end_time=end_time,
                metric_name=metric_name,
                limit=self.config.max_metrics
            )
            
            # Transformer les logs en métriques structurées
            metrics = self._transform_to_metrics(metrics_response.get('logs', []))
            
            return {
                'metrics': metrics,
                'metric_stats': self._calculate_metric_stats(metrics)
            }
            
        except Exception as e:
            logger.error(f"Error getting metrics context: {e}")
            return {'metrics': [], 'metric_stats': {}}

    async def _get_events_context(
        self,
        query: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict:
        """Récupérer le contexte des événements"""
        try:
            # Construire la requête pour les événements
            event_query = self._build_event_query(query)
            
            events_response = await self.loki_client.query_logs(
                query=event_query,
                start_time=start_time,
                end_time=end_time
            )
            
            events = self._parse_events(events_response.get('logs', []))
            
            return {
                'events': events,
                'event_stats': self._analyze_events(events)
            }
            
        except Exception as e:
            logger.error(f"Error getting events context: {e}")
            return {'events': [], 'event_stats': {}}

    async def _analyze_correlations(self, context: Dict) -> Dict:
        """Analyser les corrélations entre les différentes sources de données"""
        correlations = {
            'metric_correlations': {},
            'log_patterns': {},
            'event_correlations': {}
        }
        
        try:
            # Analyser les corrélations entre métriques
            if metrics := context.get('metrics', []):
                correlations['metric_correlations'] = (
                    self._analyze_metric_correlations(metrics)
                )
            
            # Analyser les patterns dans les logs
            if logs := context.get('logs', []):
                correlations['log_patterns'] = (
                    self._analyze_log_patterns(logs)
                )
            
            # Analyser les corrélations avec les événements
            if events := context.get('events', []):
                correlations['event_correlations'] = (
                    self._analyze_event_correlations(events, context)
                )
                
            return correlations
            
        except Exception as e:
            logger.error(f"Error analyzing correlations: {e}")
            return correlations

    def _detect_metric_type(self, query: str) -> Optional[str]:
        """Détecter le type de métrique à partir de la requête"""
        query_lower = query.lower()
        
        if 'cpu' in query_lower:
            return 'cpu_usage'
        elif 'memory' in query_lower or 'ram' in query_lower:
            return 'memory_usage'
        elif 'disk' in query_lower or 'storage' in query_lower:
            return 'disk_usage'
        elif 'network' in query_lower:
            return 'network_usage'
            
        return None

    def _transform_to_metrics(self, logs: List[Dict]) -> List[Dict]:
        """Transformer les logs en métriques structurées"""
        metrics = []
        
        for log in logs:
            try:
                # Extraire la valeur métrique du log
                if isinstance(log.get('message'), dict):
                    value = log['message'].get('value')
                    if isinstance(value, (int, float)):
                        metrics.append({
                            'timestamp': log['timestamp'],
                            'value': value,
                            'name': self._extract_metric_name(log),
                            'labels': log.get('labels', {})
                        })
            except Exception:
                continue
                
        return metrics

    def _calculate_metric_stats(self, metrics: List[Dict]) -> Dict:
        """Calculer les statistiques des métriques"""
        stats = {}
        
        if not metrics:
            return stats
            
        # Grouper par nom de métrique
        metric_groups = {}
        for metric in metrics:
            name = metric['name']
            metric_groups.setdefault(name, []).append(metric['value'])
            
        # Calculer les stats pour chaque groupe
        for name, values in metric_groups.items():
            stats[name] = {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values)
            }
            
        return stats

    def _build_event_query(self, query: str) -> str:
        """Construire une requête pour les événements"""
        # Base query for events
        event_query = '{job="vector"} |~ "(?i)(error|warning|critical|failed|started|stopped)"'
        
        # Add any specific terms from the original query
        query_terms = [term.strip() for term in query.split() if len(term.strip()) > 3]
        if query_terms:
            terms_pattern = "|".join(query_terms)
            event_query += f' |~ "(?i)({terms_pattern})"'
            
        return event_query

    def _parse_events(self, logs: List[Dict]) -> List[Dict]:
        """Parser les logs en événements structurés"""
        events = []
        
        for log in logs:
            try:
                event = {
                    'timestamp': log['timestamp'],
                    'type': self._determine_event_type(log),
                    'message': log.get('message', ''),
                    'severity': self._determine_severity(log),
                    'source': log.get('labels', {}).get('source', 'unknown'),
                    'raw': log if self.config.include_raw_data else None
                }
                events.append(event)
            except Exception:
                continue
                
        return events

    def _determine_event_type(self, log: Dict) -> str:
        """Déterminer le type d'événement"""
        message = str(log.get('message', '')).lower()
        
        if 'error' in message:
            return 'error'
        elif 'warning' in message:
            return 'warning'
        elif 'started' in message:
            return 'startup'
        elif 'stopped' in message:
            return 'shutdown'
        elif 'modified' in message:
            return 'change'
        return 'info'

    def _determine_severity(self, log: Dict) -> str:
        """Déterminer la sévérité d'un événement"""
        if 'level' in log:
            return log['level'].lower()
            
        message = str(log.get('message', '')).lower()
        
        if 'critical' in message or 'fatal' in message:
            return 'critical'
        elif 'error' in message:
            return 'error'
        elif 'warning' in message:
            return 'warning'
        elif 'info' in message:
            return 'info'
        return 'unknown'

    def _analyze_events(self, events: List[Dict]) -> Dict:
        """Analyser les statistiques des événements"""
        stats = {
            'total': len(events),
            'by_type': {},
            'by_severity': {},
            'by_source': {},
            'timeline': {}
        }
        
        for event in events:
            # Compter par type
            event_type = event['type']
            stats['by_type'][event_type] = stats['by_type'].get(event_type, 0) + 1
            
            # Compter par sévérité
            severity = event['severity']
            stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
            
            # Compter par source
            source = event['source']
            stats['by_source'][source] = stats['by_source'].get(source, 0) + 1
            
            # Agréger par heure
            hour = event['timestamp'][:13]  # YYYY-MM-DDThh
            stats['timeline'][hour] = stats['timeline'].get(hour, 0) + 1
            
        return stats

    def _extract_metric_name(self, log: Dict) -> str:
        """Extraire le nom de la métrique d'un log"""
        # Essayer d'extraire depuis les labels
        if 'labels' in log and 'metric_name' in log['labels']:
            return log['labels']['metric_name']
            
        # Essayer d'extraire depuis le message
        if isinstance(log.get('message'), dict):
            return log['message'].get('name', 'unknown')
            
        return 'unknown'

    def _build_cache_key(
        self,
        query: str,
        start_time: datetime,
        end_time: datetime,
        context_types: Optional[List[str]]
    ) -> str:
        """Construire une clé de cache"""
        components = [
            query,
            start_time.isoformat(),
            end_time.isoformat(),
            ','.join(sorted(context_types)) if context_types else 'all'
        ]
        return ':'.join(components)

    def _analyze_metric_correlations(self, metrics: List[Dict]) -> Dict:
        """Analyser les corrélations entre les métriques"""
        correlations = {}
        
        try:
            # Grouper les métriques par nom
            metric_groups = {}
            for metric in metrics:
                name = metric['name']
                if name not in metric_groups:
                    metric_groups[name] = []
                metric_groups[name].append(metric)

            # Analyser les corrélations entre chaque paire de métriques
            metric_names = list(metric_groups.keys())
            for i in range(len(metric_names)):
                for j in range(i + 1, len(metric_names)):
                    name1, name2 = metric_names[i], metric_names[j]
                    correlation = self._calculate_correlation(
                        metric_groups[name1],
                        metric_groups[name2]
                    )
                    if correlation['coefficient'] > 0.7 or correlation['coefficient'] < -0.7:
                        key = f"{name1}_vs_{name2}"
                        correlations[key] = correlation

            return correlations

        except Exception as e:
            logger.error(f"Error analyzing metric correlations: {e}")
            return {}

    def _analyze_log_patterns(self, logs: List[Dict]) -> Dict:
        """Analyser les patterns dans les logs"""
        patterns = {
            'error_patterns': {},
            'temporal_patterns': {},
            'component_patterns': {}
        }
        
        try:
            # Analyser les patterns d'erreur
            error_logs = [log for log in logs if 'error' in str(log.get('message', '')).lower()]
            for log in error_logs:
                error_type = self._categorize_error(log)
                patterns['error_patterns'][error_type] = patterns['error_patterns'].get(error_type, 0) + 1

            # Analyser les patterns temporels
            hour_counts = {}
            for log in logs:
                hour = datetime.fromisoformat(log['timestamp']).hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            patterns['temporal_patterns'] = hour_counts

            # Analyser les patterns par composant
            for log in logs:
                component = log.get('labels', {}).get('component', 'unknown')
                if component not in patterns['component_patterns']:
                    patterns['component_patterns'][component] = {
                        'count': 0,
                        'error_count': 0,
                        'warning_count': 0
                    }
                
                patterns['component_patterns'][component]['count'] += 1
                message = str(log.get('message', '')).lower()
                if 'error' in message:
                    patterns['component_patterns'][component]['error_count'] += 1
                elif 'warning' in message:
                    patterns['component_patterns'][component]['warning_count'] += 1

            return patterns

        except Exception as e:
            logger.error(f"Error analyzing log patterns: {e}")
            return {}

    def _analyze_event_correlations(self, events: List[Dict], context: Dict) -> Dict:
        """Analyser les corrélations entre événements et autres données"""
        correlations = {
            'event_metric_correlations': [],
            'event_sequences': [],
            'event_clusters': {}
        }
        
        try:
            # Analyser les corrélations avec les métriques
            if metrics := context.get('metrics', []):
                event_times = [datetime.fromisoformat(e['timestamp']) for e in events]
                for metric in metrics:
                    metric_time = datetime.fromisoformat(metric['timestamp'])
                    # Chercher les événements proches temporellement
                    for event_time, event in zip(event_times, events):
                        if abs((metric_time - event_time).total_seconds()) <= self.config.correlation_window.total_seconds():
                            correlations['event_metric_correlations'].append({
                                'event': event['type'],
                                'metric': metric['name'],
                                'time_diff': abs((metric_time - event_time).total_seconds()),
                                'metric_value': metric['value']
                            })

            # Analyser les séquences d'événements
            event_sequences = self._find_event_sequences(events)
            correlations['event_sequences'] = event_sequences

            # Regrouper les événements similaires
            correlations['event_clusters'] = self._cluster_similar_events(events)

            return correlations

        except Exception as e:
            logger.error(f"Error analyzing event correlations: {e}")
            return {}

    def _calculate_correlation(
        self,
        metrics1: List[Dict],
        metrics2: List[Dict]
    ) -> Dict:
        """Calculer la corrélation entre deux séries de métriques"""
        try:
            # Aligner les timestamps
            values1, values2 = [], []
            timestamps1 = {m['timestamp']: m['value'] for m in metrics1}
            timestamps2 = {m['timestamp']: m['value'] for m in metrics2}
            
            common_timestamps = sorted(set(timestamps1.keys()) & set(timestamps2.keys()))
            
            for ts in common_timestamps:
                values1.append(timestamps1[ts])
                values2.append(timestamps2[ts])

            if len(values1) < 2:
                return {'coefficient': 0, 'significance': 0}

            # Calculer la corrélation
            correlation = np.corrcoef(values1, values2)[0, 1]
            
            return {
                'coefficient': correlation,
                'sample_size': len(values1),
                'time_range': {
                    'start': common_timestamps[0],
                    'end': common_timestamps[-1]
                }
            }

        except Exception:
            return {'coefficient': 0, 'significance': 0}

    def _categorize_error(self, log: Dict) -> str:
        """Catégoriser un type d'erreur"""
        message = str(log.get('message', '')).lower()
        
        if 'timeout' in message:
            return 'timeout'
        elif 'connection' in message:
            return 'connection'
        elif 'permission' in message:
            return 'permission'
        elif 'memory' in message:
            return 'memory'
        elif 'disk' in message:
            return 'disk'
        return 'other'

    def _find_event_sequences(self, events: List[Dict]) -> List[Dict]:
        """Trouver des séquences d'événements répétitives"""
        sequences = []
        
        try:
            # Trier les événements par timestamp
            sorted_events = sorted(events, key=lambda x: x['timestamp'])
            
            # Chercher des séquences de 2-3 événements qui se répètent
            for i in range(len(sorted_events) - 2):
                sequence = [
                    sorted_events[i]['type'],
                    sorted_events[i + 1]['type'],
                    sorted_events[i + 2]['type']
                ]
                
                # Vérifier si cette séquence apparaît ailleurs
                occurrence_count = 0
                for j in range(len(sorted_events) - 2):
                    if (j != i and
                        sorted_events[j]['type'] == sequence[0] and
                        sorted_events[j + 1]['type'] == sequence[1] and
                        sorted_events[j + 2]['type'] == sequence[2]):
                        occurrence_count += 1

                if occurrence_count > 0:
                    sequences.append({
                        'sequence': sequence,
                        'occurrences': occurrence_count + 1,
                        'first_seen': sorted_events[i]['timestamp']
                    })

            return sequences

        except Exception as e:
            logger.error(f"Error finding event sequences: {e}")
            return []

    def _cluster_similar_events(self, events: List[Dict]) -> Dict:
        """Regrouper les événements similaires"""
        clusters = {}
        
        try:
            for event in events:
                # Créer une clé de cluster basée sur type et source
                cluster_key = f"{event['type']}_{event['source']}"
                
                if cluster_key not in clusters:
                    clusters[cluster_key] = {
                        'count': 0,
                        'first_seen': event['timestamp'],
                        'last_seen': event['timestamp'],
                        'severity_distribution': {},
                        'sample': event
                    }
                
                cluster = clusters[cluster_key]
                cluster['count'] += 1
                cluster['last_seen'] = max(cluster['last_seen'], event['timestamp'])
                
                # Mettre à jour la distribution des sévérités
                severity = event['severity']
                cluster['severity_distribution'][severity] = (
                    cluster['severity_distribution'].get(severity, 0) + 1
                )

            return clusters

        except Exception as e:
            logger.error(f"Error clustering events: {e}")
            return {}

    def _get_empty_context(self) -> Dict:
        """Retourner un contexte vide"""
        return {
            'logs': [],
            'metrics': [],
            'events': [],
            'error': 'Failed to retrieve context',
            'timestamp': datetime.now().isoformat()
        }