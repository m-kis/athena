from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TrendResult:
    direction: str  # 'increasing', 'decreasing', or 'stable'
    slope: float
    confidence: float
    change_percent: float
    seasonality: Optional[str] = None
    forecast: Optional[List[float]] = None

class TrendAnalyzer:
    def __init__(self):
        self.min_points = 5
        self.significance_level = 0.05
        self.change_threshold = 0.1  # 10% change threshold

    async def analyze_trends(
        self,
        data: pd.DataFrame,
        metric_name: str,
        window_size: int = 5
    ) -> TrendResult:
        """Analyser les tendances dans une série temporelle de métriques"""
        try:
            if len(data) < self.min_points:
                return self._get_insufficient_data_result()

            # Calcul de la tendance linéaire
            x = np.arange(len(data))
            y = data['value'].values
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            # Déterminer la direction et la confiance
            direction = self._determine_direction(slope, p_value)
            confidence = abs(r_value)
            
            # Calculer le changement en pourcentage
            change_percent = self._calculate_change_percent(data['value'])
            
            # Détecter la saisonnalité si suffisamment de données
            seasonality = None
            if len(data) >= 24:  # Au moins 24 points pour la saisonnalité
                seasonality = self._detect_seasonality(data)
            
            # Générer une prévision simple si possible
            forecast = None
            if len(data) >= window_size:
                forecast = self._generate_forecast(data, slope, intercept, window_size)
            
            return TrendResult(
                direction=direction,
                slope=slope,
                confidence=confidence,
                change_percent=change_percent,
                seasonality=seasonality,
                forecast=forecast
            )
            
        except Exception as e:
            logger.error(f"Error analyzing trends for {metric_name}: {e}")
            return self._get_error_result()

    def _determine_direction(self, slope: float, p_value: float) -> str:
        """Déterminer la direction de la tendance"""
        if p_value > self.significance_level:
            return 'stable'
        return 'increasing' if slope > 0 else 'decreasing'

    def _calculate_change_percent(self, values: pd.Series) -> float:
        """Calculer le pourcentage de changement"""
        if len(values) < 2:
            return 0.0
            
        first_val = values.iloc[0]
        last_val = values.iloc[-1]
        
        if first_val == 0:
            return float('inf') if last_val > 0 else 0.0
            
        return ((last_val - first_val) / first_val) * 100

    def _detect_seasonality(self, data: pd.DataFrame) -> Optional[str]:
        """Détecter les motifs saisonniers"""
        try:
            # Test pour la saisonnalité quotidienne
            hourly_groups = data.groupby(data.index.hour)['value'].mean()
            f_stat, p_val = stats.f_oneway(*[group for name, group in hourly_groups.items()])
            
            if p_val < self.significance_level:
                return 'daily'
                
            # Test pour la saisonnalité hebdomadaire
            if len(data) >= 168:  # 7 jours * 24 heures
                weekly_groups = data.groupby(data.index.dayofweek)['value'].mean()
                f_stat, p_val = stats.f_oneway(*[group for name, group in weekly_groups.items()])
                
                if p_val < self.significance_level:
                    return 'weekly'
                    
            return None
            
        except Exception as e:
            logger.error(f"Error detecting seasonality: {e}")
            return None

    def _generate_forecast(
        self,
        data: pd.DataFrame,
        slope: float,
        intercept: float,
        window_size: int
    ) -> List[float]:
        """Générer une prévision simple basée sur la tendance"""
        try:
            # Utiliser les derniers points pour la prévision
            last_x = len(data) - 1
            forecast_x = np.arange(last_x + 1, last_x + window_size + 1)
            
            # Calculer les valeurs prévues
            forecast_values = slope * forecast_x + intercept
            
            # Ajouter la composante saisonnière si détectée
            if seasonality := self._detect_seasonality(data):
                if seasonality == 'daily':
                    seasonal_pattern = data.groupby(data.index.hour)['value'].mean()
                    forecast_hours = (data.index[-1].hour + np.arange(1, window_size + 1)) % 24
                    forecast_values += [seasonal_pattern[hour] for hour in forecast_hours]
                    
            return forecast_values.tolist()
            
        except Exception as e:
            logger.error(f"Error generating forecast: {e}")
            return []

    def _get_insufficient_data_result(self) -> TrendResult:
        """Résultat par défaut pour données insuffisantes"""
        return TrendResult(
            direction='stable',
            slope=0.0,
            confidence=0.0,
            change_percent=0.0
        )

    def _get_error_result(self) -> TrendResult:
        """Résultat par défaut en cas d'erreur"""
        return TrendResult(
            direction='error',
            slope=0.0,
            confidence=0.0,
            change_percent=0.0
        )