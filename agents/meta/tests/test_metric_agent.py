import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.agents.metrics.metrics_agent import MetricAgent
from src.agents.metrics.feature_eng import MetricFeatureProcessor
from src.agents.metrics.predictor import MetricPredictor

@pytest.fixture
def sample_metric_data():
    """Generate sample metric data for testing"""
    timestamps = pd.date_range(
        start='2024-01-01',
        end='2024-01-02',
        freq='5T'
    )
    
    data = []
    for ts in timestamps:
        # CPU metric
        data.append({
            'timestamp': ts,
            'value': 50 + np.random.normal(0, 10),
            'metric': 'cpu_usage',
            'unit': '%'
        })
        
        # Memory metric
        data.append({
            'timestamp': ts,
            'value': 75 + np.random.normal(0, 5),
            'metric': 'memory_usage',
            'unit': '%'
        })
    
    return pd.DataFrame(data)

@pytest.fixture
async def metric_agent():
    """Create metric agent instance"""
    return MetricAgent()

@pytest.mark.asyncio
async def test_metric_analysis(metric_agent, sample_metric_data):
    """Test full metric analysis pipeline"""
    # Convert DataFrame to list of dicts for context
    context = []
    for _, row in sample_metric_data.iterrows():
        context.append({
            'content': {
                'timestamp': row['timestamp'].isoformat(),
                'value': row['value'],
                'name': row['metric'],
                'unit': row['unit']
            },
            'type': 'metric'
        })
    
    # Run analysis
    result = await metric_agent._analyze_impl(
        query="Analyze system metrics",
        context=context,
        time_window=timedelta(hours=24)
    )
    
    # Verify result structure
    assert 'analysis' in result
    assert 'predictions' in result
    assert 'anomalies' in result
    assert 'trends' in result
    assert 'stats' in result
    assert 'risk_level' in result
    assert 'recommendations' in result
    
    # Verify predictions
    assert len(result['predictions']) > 0
    for metric in ['cpu_usage', 'memory_usage']:
        assert metric in result['predictions']
        assert 'value' in result['predictions'][metric]
        
    # Verify trends
    assert len(result['trends']) > 0
    for metric, trend in result['trends'].items():
        assert 'direction' in trend
        assert 'confidence' in trend
        
    # Verify stats
    assert len(result['stats']) > 0
    for metric, stats in result['stats'].items():
        assert 'mean' in stats
        assert 'std' in stats
        
def test_feature_processor(sample_metric_data):
    """Test feature engineering"""
    processor = MetricFeatureProcessor()
    
    # Process features
    processed_data = processor.process_context(
        sample_metric_data.to_dict('records')
    )
    
    # Verify basic structure
    assert isinstance(processed_data, pd.DataFrame)
    assert 'timestamp' in processed_data.columns
    assert 'value' in processed_data.columns
    assert 'metric' in processed_data.columns
    
    # Verify derived features
    assert 'hour' in processed_data.columns
    assert 'day_of_week' in processed_data.columns
    assert 'is_weekend' in processed_data.columns
    assert 'is_business_hour' in processed_data.columns
    
    # Verify rolling features
    assert 'rolling_mean_5m' in processed_data.columns
    assert 'rolling_std_5m' in processed_data.columns
    
@pytest.mark.asyncio
async def test_predictor(sample_metric_data):
    """Test metric prediction"""
    predictor = MetricPredictor()
    
    # Generate predictions
    predictions = await predictor.predict(sample_metric_data)
    
    # Verify predictions
    assert isinstance(predictions, dict)
    for metric in ['cpu_usage', 'memory_usage']:
        assert metric in predictions
        assert 'timestamp' in predictions[metric]
        assert 'value' in predictions[metric]
        assert 'confidence_interval' in predictions[metric]
        
    # Test anomaly detection
    anomalies = predictor.detect_anomalies(sample_metric_data, predictions)
    assert isinstance(anomalies, list)
    
    # Add some artificial anomalies
    anomaly_data = sample_metric_data.copy()
    anomaly_data.loc[0, 'value'] = 999  # Extreme value
    
    anomalies = predictor.detect_anomalies(anomaly_data, predictions)
    assert len(anomalies) > 0
    
    # Verify anomaly structure
    if anomalies:
        anomaly = anomalies[0]
        assert 'metric' in anomaly
        assert 'timestamp' in anomaly
        assert 'value' in anomaly
        assert 'expected_value' in anomaly
        assert 'deviation' in anomaly
        assert 'severity' in anomaly

@pytest.mark.asyncio
async def test_metric_model_training(sample_metric_data):
    """Test model training process"""
    from src.agents.metrics.trainer import MetricModelTrainer
    
    trainer = MetricModelTrainer()
    
    # Train models
    results = await trainer.train_models(sample_metric_data)
    
    # Verify training results
    assert isinstance(results, dict)
    for metric in ['cpu_usage', 'memory_usage']:
        assert metric in results
        assert results[metric]['status'] == 'success'
        assert 'samples' in results[metric]
        assert 'metrics' in results[metric]
        assert 'seasonality' in results[metric]
        
    # Test model validation
    for metric, result in results.items():
        if result['status'] == 'success':
            validation_metrics = trainer.validate_model(
                trainer.model,
                sample_metric_data[sample_metric_data['metric'] == metric]
            )
            assert 'mae' in validation_metrics
            assert 'rmse' in validation_metrics
            assert 'r2' in validation_metrics

def test_custom_seasonality():
    """Test handling of custom seasonality patterns"""
    # Create data with strong daily pattern
    timestamps = pd.date_range(
        start='2024-01-01',
        end='2024-01-07',
        freq='1H'
    )
    
    data = []
    for ts in timestamps:
        # Add daily pattern
        hour_factor = np.sin(ts.hour * 2 * np.pi / 24)
        value = 50 + 20 * hour_factor + np.random.normal(0, 2)
        
        data.append({
            'timestamp': ts,
            'value': value,
            'metric': 'test_metric',
            'unit': '%'
        })
    
    test_data = pd.DataFrame(data)
    processor = MetricFeatureProcessor()
    processed_data = processor.process_context(test_data.to_dict('records'))
    
    # Calculate trends
    trends = processor.calculate_trends(processed_data)
    
    assert 'test_metric' in trends
    assert 'direction' in trends['test_metric']
    assert 'confidence' in trends['test_metric']
    
    # Verify stats calculation
    stats = processor.calculate_stats(processed_data)
    assert 'test_metric' in stats
    assert 'mean' in stats['test_metric']
    assert 'std' in stats['test_metric']
    assert 'rate_of_change' in stats['test_metric']